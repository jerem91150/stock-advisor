"""
Gestionnaire multi-devises pour Stock Advisor.
Conversion temps réel, impact change, affichage multi-devises.
"""
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yfinance as yf


# Devises supportées
SUPPORTED_CURRENCIES = {
    'EUR': {'name': 'Euro', 'symbol': '€', 'flag': '🇪🇺'},
    'USD': {'name': 'US Dollar', 'symbol': '$', 'flag': '🇺🇸'},
    'GBP': {'name': 'British Pound', 'symbol': '£', 'flag': '🇬🇧'},
    'CHF': {'name': 'Swiss Franc', 'symbol': 'CHF', 'flag': '🇨🇭'},
    'JPY': {'name': 'Japanese Yen', 'symbol': '¥', 'flag': '🇯🇵'},
    'CAD': {'name': 'Canadian Dollar', 'symbol': 'C$', 'flag': '🇨🇦'},
    'AUD': {'name': 'Australian Dollar', 'symbol': 'A$', 'flag': '🇦🇺'},
    'CNY': {'name': 'Chinese Yuan', 'symbol': '¥', 'flag': '🇨🇳'},
    'HKD': {'name': 'Hong Kong Dollar', 'symbol': 'HK$', 'flag': '🇭🇰'},
    'SEK': {'name': 'Swedish Krona', 'symbol': 'kr', 'flag': '🇸🇪'},
    'NOK': {'name': 'Norwegian Krone', 'symbol': 'kr', 'flag': '🇳🇴'},
    'DKK': {'name': 'Danish Krone', 'symbol': 'kr', 'flag': '🇩🇰'},
}


@dataclass
class Currency:
    """Représente une devise."""
    code: str
    name: str
    symbol: str
    flag: str = ""


@dataclass
class ExchangeRate:
    """Taux de change entre deux devises."""
    from_currency: str
    to_currency: str
    rate: float
    timestamp: datetime
    change_24h: float = 0  # Variation 24h en %


class CurrencyManager:
    """Gestionnaire de devises et conversions."""

    def __init__(self, base_currency: str = 'EUR', db_path: str = "data/currency.db"):
        """
        Initialise le gestionnaire.

        Args:
            base_currency: Devise de base pour l'affichage
            db_path: Chemin vers la base de données cache
        """
        self.base_currency = base_currency.upper()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, ExchangeRate] = {}
        self._cache_duration = timedelta(minutes=15)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                timestamp TEXT NOT NULL,
                change_24h REAL DEFAULT 0,
                UNIQUE(from_currency, to_currency)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rate_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                date TEXT NOT NULL
            )
        ''')

        conn.commit()
        conn.close()

    def set_base_currency(self, currency: str):
        """Change la devise de base."""
        currency = currency.upper()
        if currency in SUPPORTED_CURRENCIES:
            self.base_currency = currency

    def get_exchange_rate(self, from_currency: str, to_currency: str,
                           force_refresh: bool = False) -> Optional[ExchangeRate]:
        """
        Récupère le taux de change entre deux devises.

        Args:
            from_currency: Devise source
            to_currency: Devise cible
            force_refresh: Force la mise à jour depuis l'API

        Returns:
            ExchangeRate ou None si erreur
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return ExchangeRate(from_currency, to_currency, 1.0, datetime.now())

        cache_key = f"{from_currency}{to_currency}"

        # Vérifier le cache mémoire
        if not force_refresh and cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached.timestamp < self._cache_duration:
                return cached

        # Vérifier le cache DB
        if not force_refresh:
            db_rate = self._get_from_db(from_currency, to_currency)
            if db_rate and datetime.now() - db_rate.timestamp < self._cache_duration:
                self._cache[cache_key] = db_rate
                return db_rate

        # Récupérer depuis Yahoo Finance
        try:
            ticker = f"{from_currency}{to_currency}=X"
            data = yf.Ticker(ticker)
            hist = data.history(period='2d')

            if hist.empty:
                return self._get_from_db(from_currency, to_currency)

            current_rate = hist['Close'].iloc[-1]
            prev_rate = hist['Close'].iloc[0] if len(hist) > 1 else current_rate
            change_24h = ((current_rate - prev_rate) / prev_rate) * 100 if prev_rate else 0

            rate = ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=current_rate,
                timestamp=datetime.now(),
                change_24h=change_24h
            )

            # Sauvegarder en cache
            self._cache[cache_key] = rate
            self._save_to_db(rate)

            return rate

        except Exception as e:
            print(f"Erreur récupération taux {from_currency}/{to_currency}: {e}")
            return self._get_from_db(from_currency, to_currency)

    def _get_from_db(self, from_currency: str, to_currency: str) -> Optional[ExchangeRate]:
        """Récupère un taux depuis la base de données."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT rate, timestamp, change_24h FROM exchange_rates
            WHERE from_currency = ? AND to_currency = ?
        ''', (from_currency, to_currency))

        row = cursor.fetchone()
        conn.close()

        if row:
            return ExchangeRate(
                from_currency=from_currency,
                to_currency=to_currency,
                rate=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                change_24h=row[2] or 0
            )

        return None

    def _save_to_db(self, rate: ExchangeRate):
        """Sauvegarde un taux en base de données."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, timestamp, change_24h)
            VALUES (?, ?, ?, ?, ?)
        ''', (rate.from_currency, rate.to_currency, rate.rate,
              rate.timestamp.isoformat(), rate.change_24h))

        # Historique
        cursor.execute('''
            INSERT INTO rate_history (from_currency, to_currency, rate, date)
            VALUES (?, ?, ?, ?)
        ''', (rate.from_currency, rate.to_currency, rate.rate,
              datetime.now().strftime('%Y-%m-%d')))

        conn.commit()
        conn.close()

    def convert(self, amount: float, from_currency: str, to_currency: str = None) -> float:
        """
        Convertit un montant d'une devise à une autre.

        Args:
            amount: Montant à convertir
            from_currency: Devise source
            to_currency: Devise cible (défaut: devise de base)

        Returns:
            Montant converti
        """
        to_currency = to_currency or self.base_currency

        rate = self.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            return amount

        return amount * rate.rate

    def convert_portfolio(self, positions: List[Dict], to_currency: str = None) -> Dict:
        """
        Convertit toutes les positions d'un portefeuille.

        Args:
            positions: Liste de positions avec 'value' et 'currency'
            to_currency: Devise cible

        Returns:
            Dict avec total converti et détail par position
        """
        to_currency = to_currency or self.base_currency
        total = 0
        converted_positions = []

        for pos in positions:
            original_value = pos.get('value', 0)
            original_currency = pos.get('currency', 'EUR')

            converted_value = self.convert(original_value, original_currency, to_currency)
            total += converted_value

            converted_positions.append({
                **pos,
                'original_value': original_value,
                'original_currency': original_currency,
                'converted_value': converted_value,
                'converted_currency': to_currency
            })

        return {
            'total': total,
            'currency': to_currency,
            'positions': converted_positions
        }

    def get_all_rates(self, base: str = None) -> Dict[str, ExchangeRate]:
        """Récupère tous les taux de change par rapport à une devise base."""
        base = base or self.base_currency
        rates = {}

        for currency in SUPPORTED_CURRENCIES:
            if currency != base:
                rate = self.get_exchange_rate(base, currency)
                if rate:
                    rates[currency] = rate

        return rates

    def calculate_fx_impact(self, original_value: float, original_currency: str,
                             purchase_rate: float, to_currency: str = None) -> Dict:
        """
        Calcule l'impact du change sur une position.

        Args:
            original_value: Valeur dans la devise originale
            original_currency: Devise de la position
            purchase_rate: Taux de change à l'achat
            to_currency: Devise de conversion

        Returns:
            Dict avec valeur actuelle, impact change, etc.
        """
        to_currency = to_currency or self.base_currency

        current_rate = self.get_exchange_rate(original_currency, to_currency)
        if current_rate is None:
            return {}

        current_value = original_value * current_rate.rate
        value_at_purchase_rate = original_value * purchase_rate

        fx_impact = current_value - value_at_purchase_rate
        fx_impact_pct = (fx_impact / value_at_purchase_rate) * 100 if value_at_purchase_rate else 0

        return {
            'current_value': current_value,
            'value_at_purchase_rate': value_at_purchase_rate,
            'fx_impact': fx_impact,
            'fx_impact_pct': fx_impact_pct,
            'current_rate': current_rate.rate,
            'purchase_rate': purchase_rate,
            'rate_change_pct': ((current_rate.rate - purchase_rate) / purchase_rate) * 100 if purchase_rate else 0
        }

    def format_currency(self, amount: float, currency: str = None,
                         show_symbol: bool = True, decimals: int = 2) -> str:
        """Formate un montant avec le symbole de devise."""
        currency = currency or self.base_currency
        info = SUPPORTED_CURRENCIES.get(currency, {})
        symbol = info.get('symbol', currency) if show_symbol else ''

        formatted = f"{amount:,.{decimals}f}".replace(",", " ")

        if currency in ['EUR', 'CHF']:
            return f"{formatted} {symbol}".strip()
        else:
            return f"{symbol}{formatted}".strip()

    def get_rate_history(self, from_currency: str, to_currency: str,
                          days: int = 30) -> List[Dict]:
        """Récupère l'historique des taux."""
        try:
            ticker = f"{from_currency}{to_currency}=X"
            data = yf.download(ticker, period=f'{days}d', progress=False)

            if data.empty:
                return []

            history = []
            for date, row in data.iterrows():
                history.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'rate': row['Close'],
                    'high': row['High'],
                    'low': row['Low']
                })

            return history

        except Exception:
            return []

    def get_currency_info(self, code: str) -> Optional[Currency]:
        """Récupère les informations d'une devise."""
        code = code.upper()
        if code in SUPPORTED_CURRENCIES:
            info = SUPPORTED_CURRENCIES[code]
            return Currency(
                code=code,
                name=info['name'],
                symbol=info['symbol'],
                flag=info.get('flag', '')
            )
        return None


def get_supported_currencies() -> List[Currency]:
    """Retourne la liste des devises supportées."""
    return [
        Currency(code, info['name'], info['symbol'], info.get('flag', ''))
        for code, info in SUPPORTED_CURRENCIES.items()
    ]


# Test
if __name__ == "__main__":
    print("=== Test Currency Manager ===\n")

    manager = CurrencyManager(base_currency='EUR')

    # Test conversion simple
    print("EUR -> USD:")
    rate = manager.get_exchange_rate('EUR', 'USD')
    if rate:
        print(f"  Taux: {rate.rate:.4f}")
        print(f"  Variation 24h: {rate.change_24h:+.2f}%")

    amount_eur = 1000
    amount_usd = manager.convert(amount_eur, 'EUR', 'USD')
    print(f"  {manager.format_currency(amount_eur, 'EUR')} = {manager.format_currency(amount_usd, 'USD')}")

    # Test impact change
    print("\n=== Impact Change ===")
    impact = manager.calculate_fx_impact(
        original_value=1000,
        original_currency='USD',
        purchase_rate=0.92,  # EUR/USD à l'achat
        to_currency='EUR'
    )
    if impact:
        print(f"Valeur actuelle: {manager.format_currency(impact['current_value'], 'EUR')}")
        print(f"Valeur au taux d'achat: {manager.format_currency(impact['value_at_purchase_rate'], 'EUR')}")
        print(f"Impact change: {impact['fx_impact']:+.2f}€ ({impact['fx_impact_pct']:+.2f}%)")

    # Liste devises
    print("\n=== Devises supportées ===")
    for curr in get_supported_currencies()[:5]:
        print(f"  {curr.flag} {curr.code}: {curr.name} ({curr.symbol})")

    print("\n✅ Test terminé")
