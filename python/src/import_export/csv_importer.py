"""
Import CSV - Importation des transactions depuis les courtiers
Supporte: Degiro, Boursorama, Trade Republic, Interactive Brokers, Generic
"""

import csv
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import io


class BrokerType(Enum):
    DEGIRO = "degiro"
    BOURSORAMA = "boursorama"
    TRADE_REPUBLIC = "trade_republic"
    INTERACTIVE_BROKERS = "interactive_brokers"
    FORTUNEO = "fortuneo"
    BOURSE_DIRECT = "bourse_direct"
    GENERIC = "generic"
    UNKNOWN = "unknown"


@dataclass
class ImportedTransaction:
    """Transaction importée depuis un CSV."""
    date: datetime
    ticker: str
    name: str
    transaction_type: str  # 'buy' or 'sell'
    quantity: float
    price: float
    currency: str
    fees: float
    total: float
    broker: str
    raw_data: Dict  # Données brutes pour debug


@dataclass
class ImportResult:
    """Résultat d'un import."""
    success: bool
    broker_detected: BrokerType
    transactions: List[ImportedTransaction]
    errors: List[str]
    warnings: List[str]
    stats: Dict


class CSVImporter:
    """Importateur CSV multi-courtiers."""

    # Patterns de détection des courtiers
    BROKER_SIGNATURES = {
        BrokerType.DEGIRO: ['Datum', 'Produkt', 'ISIN', 'Börse', 'Anzahl'],
        BrokerType.BOURSORAMA: ['Date opération', 'Libellé', 'Montant'],
        BrokerType.TRADE_REPUBLIC: ['Date', 'Type', 'ISIN', 'Shares', 'Amount'],
        BrokerType.INTERACTIVE_BROKERS: ['TradeDate', 'Symbol', 'Quantity', 'TradePrice'],
        BrokerType.FORTUNEO: ['Date', 'Libellé opération', 'Débit', 'Crédit'],
        BrokerType.BOURSE_DIRECT: ['Date', 'Opération', 'Valeur', 'Quantité'],
    }

    # Mapping des types d'opération par courtier
    BUY_KEYWORDS = ['achat', 'buy', 'kauf', 'acquisto', 'compra', 'bought', 'acquisition']
    SELL_KEYWORDS = ['vente', 'sell', 'verkauf', 'vendita', 'venta', 'sold', 'cession']

    def __init__(self):
        self.errors = []
        self.warnings = []

    def detect_broker(self, content: str, headers: List[str]) -> BrokerType:
        """Détecte le courtier basé sur les en-têtes et le contenu."""
        headers_lower = [h.lower().strip() for h in headers]
        content_lower = content.lower()

        # Vérifier les signatures
        for broker, signatures in self.BROKER_SIGNATURES.items():
            matches = sum(1 for sig in signatures if sig.lower() in headers_lower or sig.lower() in content_lower)
            if matches >= 2:
                return broker

        # Détection par contenu spécifique
        if 'degiro' in content_lower:
            return BrokerType.DEGIRO
        if 'boursorama' in content_lower or 'brs' in content_lower:
            return BrokerType.BOURSORAMA
        if 'trade republic' in content_lower:
            return BrokerType.TRADE_REPUBLIC

        return BrokerType.GENERIC

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse une date dans différents formats."""
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%Y/%m/%d', '%m/%d/%Y', '%d %b %Y', '%d %B %Y',
            '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S',
        ]

        date_str = date_str.strip()
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        self.warnings.append(f"Format de date non reconnu: {date_str}")
        return None

    def parse_number(self, value: str) -> float:
        """Parse un nombre (gère les formats européens et US)."""
        if not value or value.strip() == '':
            return 0.0

        value = value.strip()
        # Enlever les symboles de devise
        value = re.sub(r'[€$£¥CHF]', '', value)
        value = value.strip()

        # Détecter le format (européen vs US)
        if ',' in value and '.' in value:
            # Format avec les deux séparateurs
            if value.rfind(',') > value.rfind('.'):
                # Format européen: 1.234,56
                value = value.replace('.', '').replace(',', '.')
            else:
                # Format US: 1,234.56
                value = value.replace(',', '')
        elif ',' in value:
            # Peut être européen (1234,56) ou US (1,234)
            parts = value.split(',')
            if len(parts) == 2 and len(parts[1]) == 2:
                # Probablement européen
                value = value.replace(',', '.')
            else:
                # Probablement séparateur de milliers
                value = value.replace(',', '')

        try:
            return float(value)
        except ValueError:
            self.warnings.append(f"Nombre non parsable: {value}")
            return 0.0

    def detect_transaction_type(self, text: str) -> str:
        """Détecte si c'est un achat ou une vente."""
        text_lower = text.lower()

        for keyword in self.BUY_KEYWORDS:
            if keyword in text_lower:
                return 'buy'

        for keyword in self.SELL_KEYWORDS:
            if keyword in text_lower:
                return 'sell'

        return 'buy'  # Par défaut

    def import_degiro(self, rows: List[Dict]) -> List[ImportedTransaction]:
        """Import spécifique Degiro."""
        transactions = []

        for row in rows:
            try:
                # Colonnes Degiro: Date, Heure, Produit, ISIN, Place, Nombre, Cours, Valeur locale, Valeur, Taux de change, Frais de transaction, Total
                date = self.parse_date(row.get('Datum', row.get('Date', '')))
                if not date:
                    continue

                product = row.get('Produkt', row.get('Produit', row.get('Product', '')))
                isin = row.get('ISIN', '')
                quantity = abs(self.parse_number(row.get('Anzahl', row.get('Nombre', row.get('Number', '0')))))
                price = self.parse_number(row.get('Kurs', row.get('Cours', row.get('Price', '0'))))
                total = self.parse_number(row.get('Gesamt', row.get('Total', row.get('Value', '0'))))
                fees = abs(self.parse_number(row.get('Transaktionskosten', row.get('Frais', row.get('Transaction costs', '0')))))

                # Détecter achat/vente par le signe du total
                tx_type = 'sell' if total > 0 else 'buy'

                if quantity > 0 and (price > 0 or total != 0):
                    # Chercher le ticker depuis l'ISIN ou le nom
                    ticker = self._isin_to_ticker(isin) or self._name_to_ticker(product)

                    transactions.append(ImportedTransaction(
                        date=date,
                        ticker=ticker or isin,
                        name=product,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price if price > 0 else abs(total) / quantity,
                        currency=row.get('Währung', row.get('Devise', 'EUR')),
                        fees=fees,
                        total=abs(total),
                        broker='Degiro',
                        raw_data=dict(row)
                    ))
            except Exception as e:
                self.errors.append(f"Erreur ligne Degiro: {e}")

        return transactions

    def import_boursorama(self, rows: List[Dict]) -> List[ImportedTransaction]:
        """Import spécifique Boursorama."""
        transactions = []

        for row in rows:
            try:
                date = self.parse_date(row.get('Date opération', row.get('Date', '')))
                if not date:
                    continue

                libelle = row.get('Libellé', row.get('Libellé opération', ''))

                # Détecter si c'est une transaction d'achat/vente
                if not any(kw in libelle.lower() for kw in self.BUY_KEYWORDS + self.SELL_KEYWORDS):
                    continue

                tx_type = self.detect_transaction_type(libelle)

                # Parser le libellé pour extraire les infos
                # Format typique: "ACHAT 10 ACTION_NAME" ou "VENTE 5 ACTION_NAME"
                quantity = self._extract_quantity_from_text(libelle)
                name = self._extract_name_from_text(libelle)

                montant = abs(self.parse_number(row.get('Montant', row.get('Débit', row.get('Crédit', '0')))))

                if quantity > 0 and montant > 0:
                    price = montant / quantity
                    ticker = self._name_to_ticker(name)

                    transactions.append(ImportedTransaction(
                        date=date,
                        ticker=ticker or name[:10],
                        name=name,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                        currency='EUR',
                        fees=0,
                        total=montant,
                        broker='Boursorama',
                        raw_data=dict(row)
                    ))
            except Exception as e:
                self.errors.append(f"Erreur ligne Boursorama: {e}")

        return transactions

    def import_trade_republic(self, rows: List[Dict]) -> List[ImportedTransaction]:
        """Import spécifique Trade Republic."""
        transactions = []

        for row in rows:
            try:
                date = self.parse_date(row.get('Date', ''))
                if not date:
                    continue

                tx_type_raw = row.get('Type', '')
                if 'buy' in tx_type_raw.lower() or 'kauf' in tx_type_raw.lower():
                    tx_type = 'buy'
                elif 'sell' in tx_type_raw.lower() or 'verkauf' in tx_type_raw.lower():
                    tx_type = 'sell'
                else:
                    continue

                isin = row.get('ISIN', '')
                name = row.get('Name', row.get('Asset', ''))
                quantity = abs(self.parse_number(row.get('Shares', row.get('Quantity', '0'))))
                amount = abs(self.parse_number(row.get('Amount', row.get('Total', '0'))))

                if quantity > 0 and amount > 0:
                    price = amount / quantity
                    ticker = self._isin_to_ticker(isin) or self._name_to_ticker(name)

                    transactions.append(ImportedTransaction(
                        date=date,
                        ticker=ticker or isin,
                        name=name,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                        currency='EUR',
                        fees=1.0,  # Trade Republic = 1€ par ordre
                        total=amount,
                        broker='Trade Republic',
                        raw_data=dict(row)
                    ))
            except Exception as e:
                self.errors.append(f"Erreur ligne Trade Republic: {e}")

        return transactions

    def import_generic(self, rows: List[Dict]) -> List[ImportedTransaction]:
        """Import générique - essaie de détecter les colonnes."""
        transactions = []

        # Mapping des noms de colonnes possibles
        date_cols = ['date', 'datum', 'trade date', 'transaction date', 'date opération']
        ticker_cols = ['ticker', 'symbol', 'code', 'isin', 'valeur']
        name_cols = ['name', 'nom', 'produit', 'product', 'libellé', 'description']
        type_cols = ['type', 'opération', 'operation', 'action', 'side']
        qty_cols = ['quantity', 'quantité', 'qty', 'nombre', 'shares', 'anzahl']
        price_cols = ['price', 'prix', 'cours', 'kurs', 'trade price']
        total_cols = ['total', 'montant', 'amount', 'value', 'valeur']
        fees_cols = ['fees', 'frais', 'commission', 'kosten']

        def find_col(row: Dict, candidates: List[str]) -> Optional[str]:
            for key in row.keys():
                if key.lower().strip() in candidates:
                    return key
            return None

        for row in rows:
            try:
                # Trouver les colonnes
                date_col = find_col(row, date_cols)
                if not date_col:
                    continue

                date = self.parse_date(row.get(date_col, ''))
                if not date:
                    continue

                ticker = row.get(find_col(row, ticker_cols) or '', '')
                name = row.get(find_col(row, name_cols) or '', ticker)

                type_col = find_col(row, type_cols)
                tx_type = self.detect_transaction_type(row.get(type_col, 'buy')) if type_col else 'buy'

                qty_col = find_col(row, qty_cols)
                quantity = abs(self.parse_number(row.get(qty_col, '0'))) if qty_col else 0

                price_col = find_col(row, price_cols)
                price = self.parse_number(row.get(price_col, '0')) if price_col else 0

                total_col = find_col(row, total_cols)
                total = abs(self.parse_number(row.get(total_col, '0'))) if total_col else 0

                fees_col = find_col(row, fees_cols)
                fees = abs(self.parse_number(row.get(fees_col, '0'))) if fees_col else 0

                # Calculer les valeurs manquantes
                if quantity > 0 and price == 0 and total > 0:
                    price = total / quantity
                if quantity > 0 and total == 0 and price > 0:
                    total = quantity * price

                if quantity > 0 and (price > 0 or total > 0):
                    transactions.append(ImportedTransaction(
                        date=date,
                        ticker=ticker or name[:10],
                        name=name,
                        transaction_type=tx_type,
                        quantity=quantity,
                        price=price,
                        currency='EUR',
                        fees=fees,
                        total=total,
                        broker='Import',
                        raw_data=dict(row)
                    ))
            except Exception as e:
                self.errors.append(f"Erreur ligne générique: {e}")

        return transactions

    def _isin_to_ticker(self, isin: str) -> Optional[str]:
        """Convertit un ISIN en ticker (mapping basique)."""
        # Mapping des ISINs courants
        isin_map = {
            'US0378331005': 'AAPL',
            'US5949181045': 'MSFT',
            'US02079K3059': 'GOOGL',
            'US0231351067': 'AMZN',
            'US67066G1040': 'NVDA',
            'US30303M1027': 'META',
            'US88160R1014': 'TSLA',
            'FR0000121014': 'MC.PA',
            'FR0000120578': 'SAN.PA',
            'FR0000120321': 'OR.PA',
            'FR0000125338': 'CAP.PA',
            'FR0000131104': 'BNP.PA',
            'FR0000120073': 'AI.PA',
            'FR0000120271': 'TTE.PA',
            'DE0007164600': 'SAP.DE',
            'DE0007236101': 'SIE.DE',
            'DE0008404005': 'ALV.DE',
            'NL0010273215': 'ASML.AS',
        }
        return isin_map.get(isin.upper().strip())

    def _name_to_ticker(self, name: str) -> Optional[str]:
        """Essaie de deviner le ticker depuis le nom."""
        name_lower = name.lower().strip()

        name_map = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'alphabet': 'GOOGL',
            'google': 'GOOGL',
            'amazon': 'AMZN',
            'nvidia': 'NVDA',
            'meta': 'META',
            'facebook': 'META',
            'tesla': 'TSLA',
            'lvmh': 'MC.PA',
            'sanofi': 'SAN.PA',
            "l'oreal": 'OR.PA',
            'loreal': 'OR.PA',
            'total': 'TTE.PA',
            'totalenergies': 'TTE.PA',
            'bnp': 'BNP.PA',
            'air liquide': 'AI.PA',
            'capgemini': 'CAP.PA',
            'sap': 'SAP.DE',
            'siemens': 'SIE.DE',
            'allianz': 'ALV.DE',
            'asml': 'ASML.AS',
        }

        for key, ticker in name_map.items():
            if key in name_lower:
                return ticker

        return None

    def _extract_quantity_from_text(self, text: str) -> float:
        """Extrait la quantité d'un texte."""
        # Pattern: "ACHAT 10 ..." ou "... 10 ACTIONS"
        patterns = [
            r'(?:achat|vente|buy|sell)\s+(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s+(?:action|share|titre)',
            r'x\s*(\d+(?:[.,]\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                return self.parse_number(match.group(1))

        return 0

    def _extract_name_from_text(self, text: str) -> str:
        """Extrait le nom de l'action d'un texte."""
        # Enlever les mots-clés de transaction
        text = re.sub(r'\b(achat|vente|buy|sell|acquisition|cession)\b', '', text, flags=re.IGNORECASE)
        # Enlever les nombres
        text = re.sub(r'\b\d+(?:[.,]\d+)?\b', '', text)
        # Nettoyer
        text = ' '.join(text.split())
        return text.strip()

    def import_csv(self, content: str, broker_hint: BrokerType = None) -> ImportResult:
        """
        Importe un fichier CSV.

        Args:
            content: Contenu du fichier CSV
            broker_hint: Type de courtier (optionnel, sera auto-détecté sinon)
        """
        self.errors = []
        self.warnings = []
        transactions = []

        try:
            # Détecter le délimiteur
            sample = content[:2000]
            if '\t' in sample:
                delimiter = '\t'
            elif ';' in sample:
                delimiter = ';'
            else:
                delimiter = ','

            # Parser le CSV
            reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
            rows = list(reader)

            if not rows:
                return ImportResult(
                    success=False,
                    broker_detected=BrokerType.UNKNOWN,
                    transactions=[],
                    errors=["Fichier CSV vide"],
                    warnings=[],
                    stats={}
                )

            headers = list(rows[0].keys()) if rows else []

            # Détecter le courtier
            broker = broker_hint or self.detect_broker(content, headers)

            # Importer selon le courtier
            if broker == BrokerType.DEGIRO:
                transactions = self.import_degiro(rows)
            elif broker == BrokerType.BOURSORAMA:
                transactions = self.import_boursorama(rows)
            elif broker == BrokerType.TRADE_REPUBLIC:
                transactions = self.import_trade_republic(rows)
            else:
                transactions = self.import_generic(rows)

            # Statistiques
            stats = {
                'total_rows': len(rows),
                'transactions_imported': len(transactions),
                'buys': len([t for t in transactions if t.transaction_type == 'buy']),
                'sells': len([t for t in transactions if t.transaction_type == 'sell']),
                'total_invested': sum(t.total for t in transactions if t.transaction_type == 'buy'),
                'total_sold': sum(t.total for t in transactions if t.transaction_type == 'sell'),
                'unique_tickers': len(set(t.ticker for t in transactions)),
                'date_range': f"{min(t.date for t in transactions).strftime('%Y-%m-%d')} - {max(t.date for t in transactions).strftime('%Y-%m-%d')}" if transactions else "N/A"
            }

            return ImportResult(
                success=len(transactions) > 0,
                broker_detected=broker,
                transactions=transactions,
                errors=self.errors,
                warnings=self.warnings,
                stats=stats
            )

        except Exception as e:
            return ImportResult(
                success=False,
                broker_detected=BrokerType.UNKNOWN,
                transactions=[],
                errors=[f"Erreur parsing CSV: {str(e)}"],
                warnings=self.warnings,
                stats={}
            )


def get_csv_importer() -> CSVImporter:
    """Factory function."""
    return CSVImporter()


if __name__ == "__main__":
    # Test
    importer = CSVImporter()

    # Exemple CSV Degiro
    test_csv = """Datum,Produkt,ISIN,Börse,Anzahl,Kurs,Währung,Gesamt
2024-01-15,Apple Inc,US0378331005,NASDAQ,10,185.50,USD,-1855.00
2024-02-20,Microsoft Corp,US5949181045,NASDAQ,5,410.00,USD,-2050.00
2024-03-10,Apple Inc,US0378331005,NASDAQ,-5,195.00,USD,975.00"""

    result = importer.import_csv(test_csv)

    print(f"Broker détecté: {result.broker_detected.value}")
    print(f"Transactions importées: {result.stats.get('transactions_imported', 0)}")

    for tx in result.transactions:
        print(f"  {tx.date.strftime('%Y-%m-%d')} | {tx.transaction_type.upper()} | {tx.quantity}x {tx.ticker} @ {tx.price:.2f} = {tx.total:.2f}")
