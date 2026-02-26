"""
Gestionnaire de Portefeuilles - Inspiré de Moning/Finary
Permet de gérer plusieurs portefeuilles, positions et transactions
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session

try:
    from src.database.models import (
        Base, Portfolio, Position, Transaction, DividendReceived,
        init_db, get_session
    )
except ImportError:
    from database.models import (
        Base, Portfolio, Position, Transaction, DividendReceived,
        init_db, get_session
    )

import yfinance as yf
import pandas as pd


@dataclass
class PortfolioSummary:
    """Résumé d'un portefeuille."""
    id: int
    name: str
    portfolio_type: str
    broker: Optional[str]
    total_invested: float
    current_value: float
    total_gain: float
    total_gain_pct: float
    total_dividends: float
    positions_count: int
    currency: str


@dataclass
class PositionDetail:
    """Détails d'une position."""
    id: int
    ticker: str
    name: str
    quantity: float
    average_cost: float
    total_cost: float
    current_price: float
    current_value: float
    gain: float
    gain_pct: float
    weight: float  # Poids dans le portefeuille
    sector: Optional[str]
    country: Optional[str]
    dividends_received: float
    last_transaction: Optional[datetime]


class PortfolioManager:
    """Gestionnaire principal des portefeuilles."""

    def __init__(self, db_path: str = None):
        """Initialise le gestionnaire avec une base de données."""
        if db_path is None:
            # Chemin par défaut
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            db_path = os.path.join(base_dir, "data", "portfolios.db")

        # Créer le dossier data si nécessaire
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # Cache pour les prix
        self._price_cache: Dict[str, Tuple[float, datetime]] = {}
        self._cache_duration = timedelta(minutes=15)

    def _get_session(self) -> Session:
        """Crée une nouvelle session."""
        return self.Session()

    # ==================== GESTION DES PORTEFEUILLES ====================

    def create_portfolio(
        self,
        name: str,
        portfolio_type: str,
        broker: str = None,
        description: str = None,
        currency: str = "EUR",
        opened_date: datetime = None,
        target_value: float = None,
        monthly_contribution: float = None
    ) -> Portfolio:
        """Crée un nouveau portefeuille."""
        session = self._get_session()
        try:
            portfolio = Portfolio(
                name=name,
                portfolio_type=portfolio_type,
                broker=broker,
                description=description,
                currency=currency,
                opened_date=opened_date or datetime.now(),
                target_value=target_value,
                monthly_contribution=monthly_contribution
            )
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)
            return portfolio
        finally:
            session.close()

    def get_portfolio(self, portfolio_id: int) -> Optional[Portfolio]:
        """Récupère un portefeuille par ID."""
        session = self._get_session()
        try:
            return session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        finally:
            session.close()

    def get_all_portfolios(self, active_only: bool = True) -> List[Portfolio]:
        """Récupère tous les portefeuilles."""
        session = self._get_session()
        try:
            query = session.query(Portfolio)
            if active_only:
                query = query.filter(Portfolio.is_active == True)
            return query.order_by(Portfolio.name).all()
        finally:
            session.close()

    def update_portfolio(self, portfolio_id: int, **kwargs) -> Optional[Portfolio]:
        """Met à jour un portefeuille."""
        session = self._get_session()
        try:
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if portfolio:
                for key, value in kwargs.items():
                    if hasattr(portfolio, key):
                        setattr(portfolio, key, value)
                portfolio.updated_at = datetime.now()
                session.commit()
                session.refresh(portfolio)
            return portfolio
        finally:
            session.close()

    def delete_portfolio(self, portfolio_id: int, hard_delete: bool = False) -> bool:
        """Supprime un portefeuille (soft delete par défaut)."""
        session = self._get_session()
        try:
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if portfolio:
                if hard_delete:
                    session.delete(portfolio)
                else:
                    portfolio.is_active = False
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== GESTION DES POSITIONS ====================

    def add_position(
        self,
        portfolio_id: int,
        ticker: str,
        quantity: float,
        price: float,
        transaction_date: datetime = None,
        fees: float = 0,
        notes: str = None,
        asset_type: str = "stock"
    ) -> Tuple[Position, Transaction]:
        """Ajoute une position (crée ou met à jour) avec une transaction d'achat."""
        session = self._get_session()
        try:
            # Vérifier que le portefeuille existe
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} non trouvé")

            transaction_date = transaction_date or datetime.now()
            total_amount = quantity * price + fees

            # Chercher une position existante
            position = session.query(Position).filter(
                and_(Position.portfolio_id == portfolio_id, Position.ticker == ticker)
            ).first()

            if position:
                # Mettre à jour la position existante (moyenne pondérée)
                old_total = position.quantity * (position.average_cost or 0)
                new_total = old_total + (quantity * price)
                position.quantity += quantity
                position.average_cost = new_total / position.quantity if position.quantity > 0 else 0
                position.total_cost = position.quantity * position.average_cost
                position.last_transaction_date = transaction_date
            else:
                # Créer une nouvelle position
                # Récupérer les infos de l'action
                stock_info = self._get_stock_info(ticker)

                position = Position(
                    portfolio_id=portfolio_id,
                    ticker=ticker,
                    name=stock_info.get('name', ticker),
                    asset_type=asset_type,
                    quantity=quantity,
                    average_cost=price,
                    total_cost=quantity * price,
                    currency=stock_info.get('currency', portfolio.currency),
                    sector=stock_info.get('sector'),
                    country=stock_info.get('country'),
                    first_buy_date=transaction_date,
                    last_transaction_date=transaction_date,
                    notes=notes
                )
                session.add(position)
                session.flush()  # Pour obtenir l'ID

            # Créer la transaction
            transaction = Transaction(
                portfolio_id=portfolio_id,
                position_id=position.id,
                transaction_type="buy",
                ticker=ticker,
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                fees=fees,
                currency=portfolio.currency,
                transaction_date=transaction_date,
                notes=notes
            )
            session.add(transaction)

            session.commit()
            session.refresh(position)
            session.refresh(transaction)

            return position, transaction
        finally:
            session.close()

    def sell_position(
        self,
        portfolio_id: int,
        ticker: str,
        quantity: float,
        price: float,
        transaction_date: datetime = None,
        fees: float = 0,
        notes: str = None
    ) -> Tuple[Optional[Position], Transaction]:
        """Vend une partie ou toute une position."""
        session = self._get_session()
        try:
            position = session.query(Position).filter(
                and_(Position.portfolio_id == portfolio_id, Position.ticker == ticker)
            ).first()

            if not position:
                raise ValueError(f"Position {ticker} non trouvée dans le portefeuille")

            if quantity > position.quantity:
                raise ValueError(f"Quantité à vendre ({quantity}) supérieure à la position ({position.quantity})")

            transaction_date = transaction_date or datetime.now()
            total_amount = quantity * price - fees

            # Mettre à jour la position
            position.quantity -= quantity
            if position.quantity > 0:
                # Garder le même PRU
                position.total_cost = position.quantity * position.average_cost
            else:
                # Position soldée
                position.total_cost = 0
                position.average_cost = 0

            position.last_transaction_date = transaction_date

            # Créer la transaction
            transaction = Transaction(
                portfolio_id=portfolio_id,
                position_id=position.id,
                transaction_type="sell",
                ticker=ticker,
                quantity=quantity,
                price=price,
                total_amount=total_amount,
                fees=fees,
                transaction_date=transaction_date,
                notes=notes
            )
            session.add(transaction)

            session.commit()

            # Retourner None si position soldée
            if position.quantity <= 0:
                return None, transaction

            session.refresh(position)
            session.refresh(transaction)
            return position, transaction
        finally:
            session.close()

    def get_positions(self, portfolio_id: int, include_sold: bool = False) -> List[Position]:
        """Récupère toutes les positions d'un portefeuille."""
        session = self._get_session()
        try:
            query = session.query(Position).filter(Position.portfolio_id == portfolio_id)
            if not include_sold:
                query = query.filter(Position.quantity > 0)
            return query.order_by(Position.ticker).all()
        finally:
            session.close()

    def get_position(self, portfolio_id: int, ticker: str) -> Optional[Position]:
        """Récupère une position spécifique."""
        session = self._get_session()
        try:
            return session.query(Position).filter(
                and_(Position.portfolio_id == portfolio_id, Position.ticker == ticker)
            ).first()
        finally:
            session.close()

    # ==================== DIVIDENDES ====================

    def add_dividend(
        self,
        position_id: int,
        gross_amount: float,
        payment_date: datetime,
        tax_withheld: float = 0,
        amount_per_share: float = None,
        shares_held: float = None,
        ex_date: datetime = None,
        dividend_type: str = "regular",
        is_drip: bool = False,
        notes: str = None
    ) -> DividendReceived:
        """Enregistre un dividende reçu."""
        session = self._get_session()
        try:
            position = session.query(Position).filter(Position.id == position_id).first()
            if not position:
                raise ValueError(f"Position {position_id} non trouvée")

            dividend = DividendReceived(
                position_id=position_id,
                ticker=position.ticker,
                ex_date=ex_date,
                payment_date=payment_date,
                amount_per_share=amount_per_share,
                shares_held=shares_held or position.quantity,
                gross_amount=gross_amount,
                tax_withheld=tax_withheld,
                net_amount=gross_amount - tax_withheld,
                currency=position.currency,
                dividend_type=dividend_type,
                is_drip=is_drip,
                notes=notes
            )
            session.add(dividend)
            session.commit()
            session.refresh(dividend)
            return dividend
        finally:
            session.close()

    def get_dividends(
        self,
        portfolio_id: int = None,
        position_id: int = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[DividendReceived]:
        """Récupère les dividendes."""
        session = self._get_session()
        try:
            query = session.query(DividendReceived)

            if position_id:
                query = query.filter(DividendReceived.position_id == position_id)
            elif portfolio_id:
                # Joindre avec positions pour filtrer par portefeuille
                query = query.join(Position).filter(Position.portfolio_id == portfolio_id)

            if start_date:
                query = query.filter(DividendReceived.payment_date >= start_date)
            if end_date:
                query = query.filter(DividendReceived.payment_date <= end_date)

            return query.order_by(DividendReceived.payment_date.desc()).all()
        finally:
            session.close()

    # ==================== TRANSACTIONS ====================

    def get_transactions(
        self,
        portfolio_id: int = None,
        ticker: str = None,
        transaction_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[Transaction]:
        """Récupère les transactions."""
        session = self._get_session()
        try:
            query = session.query(Transaction)

            if portfolio_id:
                query = query.filter(Transaction.portfolio_id == portfolio_id)
            if ticker:
                query = query.filter(Transaction.ticker == ticker)
            if transaction_type:
                query = query.filter(Transaction.transaction_type == transaction_type)
            if start_date:
                query = query.filter(Transaction.transaction_date >= start_date)
            if end_date:
                query = query.filter(Transaction.transaction_date <= end_date)

            return query.order_by(Transaction.transaction_date.desc()).limit(limit).all()
        finally:
            session.close()

    # ==================== CALCULS ET ANALYTICS ====================

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Récupère le prix actuel d'une action (avec cache)."""
        now = datetime.now()

        # Vérifier le cache
        if ticker in self._price_cache:
            price, timestamp = self._price_cache[ticker]
            if now - timestamp < self._cache_duration:
                return price

        # Récupérer le prix via yfinance
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                self._price_cache[ticker] = (price, now)
                return price
        except Exception as e:
            print(f"Erreur récupération prix {ticker}: {e}")

        return None

    def _get_stock_info(self, ticker: str) -> Dict:
        """Récupère les infos d'une action."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'name': info.get('longName') or info.get('shortName') or ticker,
                'currency': info.get('currency', 'EUR'),
                'sector': info.get('sector'),
                'country': info.get('country'),
                'industry': info.get('industry')
            }
        except:
            return {'name': ticker, 'currency': 'EUR'}

    def get_portfolio_summary(self, portfolio_id: int) -> Optional[PortfolioSummary]:
        """Calcule le résumé d'un portefeuille."""
        session = self._get_session()
        try:
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                return None

            positions = session.query(Position).filter(
                and_(Position.portfolio_id == portfolio_id, Position.quantity > 0)
            ).all()

            total_invested = 0
            current_value = 0
            total_dividends = 0

            for pos in positions:
                total_invested += pos.total_cost or 0
                price = self.get_current_price(pos.ticker)
                if price:
                    current_value += pos.quantity * price

                # Calculer les dividendes
                dividends = session.query(func.sum(DividendReceived.net_amount)).filter(
                    DividendReceived.position_id == pos.id
                ).scalar() or 0
                total_dividends += dividends

            total_gain = current_value - total_invested + total_dividends
            total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0

            return PortfolioSummary(
                id=portfolio.id,
                name=portfolio.name,
                portfolio_type=portfolio.portfolio_type,
                broker=portfolio.broker,
                total_invested=total_invested,
                current_value=current_value,
                total_gain=total_gain,
                total_gain_pct=total_gain_pct,
                total_dividends=total_dividends,
                positions_count=len(positions),
                currency=portfolio.currency
            )
        finally:
            session.close()

    def get_position_details(self, portfolio_id: int) -> List[PositionDetail]:
        """Calcule les détails de toutes les positions d'un portefeuille."""
        session = self._get_session()
        try:
            positions = session.query(Position).filter(
                and_(Position.portfolio_id == portfolio_id, Position.quantity > 0)
            ).all()

            # Calculer la valeur totale du portefeuille
            total_value = 0
            position_values = {}

            for pos in positions:
                price = self.get_current_price(pos.ticker) or pos.average_cost or 0
                value = pos.quantity * price
                position_values[pos.id] = (price, value)
                total_value += value

            details = []
            for pos in positions:
                price, value = position_values.get(pos.id, (0, 0))

                # Dividendes reçus
                dividends = session.query(func.sum(DividendReceived.net_amount)).filter(
                    DividendReceived.position_id == pos.id
                ).scalar() or 0

                gain = value - (pos.total_cost or 0)
                gain_pct = (gain / pos.total_cost * 100) if pos.total_cost and pos.total_cost > 0 else 0
                weight = (value / total_value * 100) if total_value > 0 else 0

                details.append(PositionDetail(
                    id=pos.id,
                    ticker=pos.ticker,
                    name=pos.name or pos.ticker,
                    quantity=pos.quantity,
                    average_cost=pos.average_cost or 0,
                    total_cost=pos.total_cost or 0,
                    current_price=price,
                    current_value=value,
                    gain=gain,
                    gain_pct=gain_pct,
                    weight=weight,
                    sector=pos.sector,
                    country=pos.country,
                    dividends_received=dividends,
                    last_transaction=pos.last_transaction_date
                ))

            # Trier par valeur décroissante
            details.sort(key=lambda x: x.current_value, reverse=True)
            return details
        finally:
            session.close()

    def get_allocation_by_sector(self, portfolio_id: int) -> Dict[str, float]:
        """Calcule la répartition sectorielle."""
        details = self.get_position_details(portfolio_id)
        sectors = {}
        for pos in details:
            sector = pos.sector or "Non classé"
            sectors[sector] = sectors.get(sector, 0) + pos.current_value
        return sectors

    def get_allocation_by_country(self, portfolio_id: int) -> Dict[str, float]:
        """Calcule la répartition géographique."""
        details = self.get_position_details(portfolio_id)
        countries = {}
        for pos in details:
            country = pos.country or "Non classé"
            countries[country] = countries.get(country, 0) + pos.current_value
        return countries

    def get_all_portfolios_summary(self) -> Dict:
        """Calcule le résumé global de tous les portefeuilles."""
        portfolios = self.get_all_portfolios()
        summaries = []
        total_invested = 0
        total_value = 0
        total_gain = 0
        total_dividends = 0

        for portfolio in portfolios:
            summary = self.get_portfolio_summary(portfolio.id)
            if summary:
                summaries.append(summary)
                total_invested += summary.total_invested
                total_value += summary.current_value
                total_gain += summary.total_gain
                total_dividends += summary.total_dividends

        return {
            'portfolios': summaries,
            'total_invested': total_invested,
            'total_value': total_value,
            'total_gain': total_gain,
            'total_gain_pct': (total_gain / total_invested * 100) if total_invested > 0 else 0,
            'total_dividends': total_dividends,
            'portfolios_count': len(summaries)
        }

    def get_dividend_calendar(
        self,
        portfolio_id: int = None,
        year: int = None
    ) -> Dict[str, List[DividendReceived]]:
        """Retourne un calendrier des dividendes par mois."""
        if year is None:
            year = datetime.now().year

        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31)

        dividends = self.get_dividends(
            portfolio_id=portfolio_id,
            start_date=start_date,
            end_date=end_date
        )

        calendar = {str(i).zfill(2): [] for i in range(1, 13)}
        for div in dividends:
            month = str(div.payment_date.month).zfill(2)
            calendar[month].append(div)

        return calendar

    def get_performance_history(
        self,
        portfolio_id: int,
        period_days: int = 365
    ) -> pd.DataFrame:
        """Calcule l'historique de performance."""
        session = self._get_session()
        try:
            # Récupérer toutes les transactions
            transactions = session.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id
            ).order_by(Transaction.transaction_date).all()

            if not transactions:
                return pd.DataFrame()

            # Créer une timeline jour par jour
            start_date = transactions[0].transaction_date
            end_date = datetime.now()

            # Simplifier : prendre des snapshots mensuels
            dates = pd.date_range(start=start_date, end=end_date, freq='M')

            data = []
            for date in dates:
                # Calculer l'investissement total à cette date
                invested = sum(
                    t.total_amount if t.transaction_type == 'buy' else -t.total_amount
                    for t in transactions
                    if t.transaction_date <= date
                )
                data.append({
                    'date': date,
                    'invested': invested
                })

            return pd.DataFrame(data)
        finally:
            session.close()

    # ==================== IMPORT/EXPORT ====================

    def export_portfolio_to_json(self, portfolio_id: int) -> str:
        """Exporte un portefeuille en JSON."""
        session = self._get_session()
        try:
            portfolio = session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                return "{}"

            positions = session.query(Position).filter(
                Position.portfolio_id == portfolio_id
            ).all()

            transactions = session.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id
            ).all()

            data = {
                'portfolio': {
                    'name': portfolio.name,
                    'type': portfolio.portfolio_type,
                    'broker': portfolio.broker,
                    'currency': portfolio.currency,
                    'opened_date': portfolio.opened_date.isoformat() if portfolio.opened_date else None
                },
                'positions': [
                    {
                        'ticker': p.ticker,
                        'name': p.name,
                        'quantity': p.quantity,
                        'average_cost': p.average_cost,
                        'sector': p.sector,
                        'country': p.country
                    }
                    for p in positions
                ],
                'transactions': [
                    {
                        'type': t.transaction_type,
                        'ticker': t.ticker,
                        'quantity': t.quantity,
                        'price': t.price,
                        'fees': t.fees,
                        'date': t.transaction_date.isoformat()
                    }
                    for t in transactions
                ]
            }

            return json.dumps(data, indent=2, ensure_ascii=False)
        finally:
            session.close()

    def import_portfolio_from_json(self, json_data: str) -> Portfolio:
        """Importe un portefeuille depuis JSON."""
        data = json.loads(json_data)

        # Créer le portefeuille
        portfolio = self.create_portfolio(
            name=data['portfolio']['name'],
            portfolio_type=data['portfolio']['type'],
            broker=data['portfolio'].get('broker'),
            currency=data['portfolio'].get('currency', 'EUR')
        )

        # Importer les transactions (recréera les positions)
        for t in data.get('transactions', []):
            if t['type'] == 'buy':
                self.add_position(
                    portfolio_id=portfolio.id,
                    ticker=t['ticker'],
                    quantity=t['quantity'],
                    price=t['price'],
                    fees=t.get('fees', 0),
                    transaction_date=datetime.fromisoformat(t['date'])
                )
            elif t['type'] == 'sell':
                self.sell_position(
                    portfolio_id=portfolio.id,
                    ticker=t['ticker'],
                    quantity=t['quantity'],
                    price=t['price'],
                    fees=t.get('fees', 0),
                    transaction_date=datetime.fromisoformat(t['date'])
                )

        return portfolio


# ==================== FONCTIONS UTILITAIRES ====================

def get_portfolio_manager(db_path: str = None) -> PortfolioManager:
    """Factory function pour créer un PortfolioManager."""
    return PortfolioManager(db_path)


if __name__ == "__main__":
    # Test du gestionnaire
    print("=== Test du Gestionnaire de Portefeuilles ===\n")

    manager = PortfolioManager()

    # Créer un portefeuille de test
    print("Création d'un portefeuille PEA...")
    pea = manager.create_portfolio(
        name="Mon PEA",
        portfolio_type="PEA",
        broker="Boursorama",
        description="Portefeuille PEA principal",
        monthly_contribution=200
    )
    print(f"  Créé: {pea.name} (ID: {pea.id})")

    # Ajouter des positions
    print("\nAjout de positions...")
    pos1, tx1 = manager.add_position(
        portfolio_id=pea.id,
        ticker="MC.PA",
        quantity=2,
        price=850.0,
        fees=1.0
    )
    print(f"  Acheté: {pos1.ticker} - {pos1.quantity}x @ {pos1.average_cost}€")

    pos2, tx2 = manager.add_position(
        portfolio_id=pea.id,
        ticker="OR.PA",
        quantity=5,
        price=390.0,
        fees=1.0
    )
    print(f"  Acheté: {pos2.ticker} - {pos2.quantity}x @ {pos2.average_cost}€")

    # Résumé du portefeuille
    print("\nRésumé du portefeuille:")
    summary = manager.get_portfolio_summary(pea.id)
    if summary:
        print(f"  Investi: {summary.total_invested:.2f}€")
        print(f"  Valeur actuelle: {summary.current_value:.2f}€")
        print(f"  Gain: {summary.total_gain:+.2f}€ ({summary.total_gain_pct:+.1f}%)")
        print(f"  Positions: {summary.positions_count}")

    # Détails des positions
    print("\nDétails des positions:")
    details = manager.get_position_details(pea.id)
    for d in details:
        print(f"  {d.ticker}: {d.quantity}x @ {d.average_cost:.2f}€ = {d.current_value:.2f}€ ({d.gain_pct:+.1f}%) - {d.weight:.1f}%")

    print("\n=== Test terminé ===")
