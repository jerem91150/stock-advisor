"""
Modèles SQLAlchemy pour Stock Advisor
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum, create_engine, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from enum import Enum as PyEnum

Base = declarative_base()


class MarketType(PyEnum):
    """Type de marché."""
    PEA = "pea"
    CTO = "cto"
    BOTH = "both"


class Sector(PyEnum):
    """Secteurs d'activité."""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    INDUSTRIALS = "industrials"
    ENERGY = "energy"
    MATERIALS = "materials"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION_SERVICES = "communication_services"
    DEFENSE = "defense"
    OTHER = "other"


class Stock(Base):
    """Modèle pour une action."""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    isin = Column(String(12), unique=True, nullable=True)

    # Marché et éligibilité
    exchange = Column(String(50))  # NYSE, NASDAQ, EURONEXT, etc.
    currency = Column(String(10), default="USD")
    country = Column(String(50))
    pea_eligible = Column(Boolean, default=False)

    # Classification
    sector = Column(String(100))
    industry = Column(String(100))

    # Données de base
    market_cap = Column(Float)  # En millions
    employees = Column(Integer)
    website = Column(String(255))
    description = Column(Text)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    price_history = relationship("PriceHistory", back_populates="stock", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamentals", back_populates="stock", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="stock", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_stock_sector', 'sector'),
        Index('idx_stock_country', 'country'),
    )

    def __repr__(self):
        return f"<Stock(ticker='{self.ticker}', name='{self.name}')>"


class PriceHistory(Base):
    """Historique des prix."""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, nullable=False)

    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_close = Column(Float)
    volume = Column(Float)

    # Indicateurs techniques pré-calculés
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)

    stock = relationship("Stock", back_populates="price_history")

    __table_args__ = (
        Index('idx_price_stock_date', 'stock_id', 'date'),
    )


class Fundamentals(Base):
    """Données fondamentales."""
    __tablename__ = "fundamentals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    # Valorisation
    pe_ratio = Column(Float)  # Price/Earnings
    forward_pe = Column(Float)
    peg_ratio = Column(Float)  # Price/Earnings to Growth
    pb_ratio = Column(Float)  # Price/Book
    ps_ratio = Column(Float)  # Price/Sales
    ev_ebitda = Column(Float)  # Enterprise Value / EBITDA

    # Rentabilité
    roe = Column(Float)  # Return on Equity
    roa = Column(Float)  # Return on Assets
    roic = Column(Float)  # Return on Invested Capital
    profit_margin = Column(Float)
    operating_margin = Column(Float)
    gross_margin = Column(Float)

    # Croissance
    revenue_growth = Column(Float)  # YoY
    earnings_growth = Column(Float)  # YoY

    # Santé financière
    current_ratio = Column(Float)
    quick_ratio = Column(Float)
    debt_to_equity = Column(Float)
    debt_to_ebitda = Column(Float)
    interest_coverage = Column(Float)

    # Dividendes
    dividend_yield = Column(Float)
    dividend_payout_ratio = Column(Float)

    # Autres
    beta = Column(Float)
    eps = Column(Float)
    revenue = Column(Float)  # En millions
    ebitda = Column(Float)  # En millions
    free_cash_flow = Column(Float)  # En millions

    stock = relationship("Stock", back_populates="fundamentals")

    __table_args__ = (
        Index('idx_fundamentals_stock_date', 'stock_id', 'date'),
    )


class Score(Base):
    """Scores calculés pour une action."""
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)

    # Scores par catégorie (0-100)
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    smart_money_score = Column(Float)

    # Score global (0-100)
    global_score = Column(Float)

    # Pondérations utilisées
    technical_weight = Column(Float, default=0.25)
    fundamental_weight = Column(Float, default=0.25)
    sentiment_weight = Column(Float, default=0.25)
    smart_money_weight = Column(Float, default=0.25)

    # Signaux détaillés (JSON stocké comme texte)
    technical_signals = Column(Text)  # JSON
    fundamental_signals = Column(Text)  # JSON
    sentiment_signals = Column(Text)  # JSON
    smart_money_signals = Column(Text)  # JSON

    stock = relationship("Stock", back_populates="scores")

    __table_args__ = (
        Index('idx_score_stock_date', 'stock_id', 'date'),
        Index('idx_score_global', 'global_score'),
    )


class Watchlist(Base):
    """Liste de surveillance utilisateur."""
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    """Élément d'une watchlist."""
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    target_price = Column(Float)
    alert_enabled = Column(Boolean, default=False)

    watchlist = relationship("Watchlist", back_populates="items")
    stock = relationship("Stock")


class Filter(Base):
    """Filtres personnalisés sauvegardés."""
    __tablename__ = "filters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # Configuration du filtre (JSON)
    config = Column(Text, nullable=False)  # JSON

    # Type de filtre
    filter_type = Column(String(50))  # sectoral, ethical, fundamental, custom

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class GuruPosition(Base):
    """Positions des grands investisseurs (13F)."""
    __tablename__ = "guru_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    guru_name = Column(String(100), nullable=False, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    # Position
    shares = Column(Float)
    value = Column(Float)  # En millions USD
    portfolio_percentage = Column(Float)

    # Changement depuis dernier 13F
    change_type = Column(String(20))  # new, increased, decreased, sold, unchanged
    change_percentage = Column(Float)

    # Dates
    report_date = Column(DateTime, nullable=False)
    filing_date = Column(DateTime)

    stock = relationship("Stock")

    __table_args__ = (
        Index('idx_guru_stock', 'guru_name', 'stock_id'),
        Index('idx_guru_date', 'report_date'),
    )


class NewsArticle(Base):
    """Articles de news pour analyse sentiment."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)

    title = Column(String(500), nullable=False)
    url = Column(String(1000))
    source = Column(String(100))
    published_at = Column(DateTime)

    # Contenu
    summary = Column(Text)
    full_text = Column(Text)

    # Analyse sentiment
    sentiment_score = Column(Float)  # -1 à +1
    sentiment_label = Column(String(20))  # positive, negative, neutral
    sentiment_analyzed_at = Column(DateTime)

    # Métadonnées
    scraped_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock")

    __table_args__ = (
        Index('idx_news_stock', 'stock_id'),
        Index('idx_news_date', 'published_at'),
    )


class SocialMention(Base):
    """Mentions sur réseaux sociaux."""
    __tablename__ = "social_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)

    platform = Column(String(50), nullable=False)  # reddit, stocktwits, twitter
    post_id = Column(String(100))

    title = Column(String(500))
    content = Column(Text)
    url = Column(String(1000))

    author = Column(String(100))
    upvotes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)

    published_at = Column(DateTime)

    # Analyse sentiment
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))

    scraped_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock")

    __table_args__ = (
        Index('idx_social_stock', 'stock_id'),
        Index('idx_social_platform', 'platform'),
    )


class PortfolioType(PyEnum):
    """Type de portefeuille."""
    PEA = "pea"
    CTO = "cto"
    ASSURANCE_VIE = "assurance_vie"
    PER = "per"
    CRYPTO = "crypto"
    AUTRE = "autre"


class TransactionType(PyEnum):
    """Type de transaction."""
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    SPLIT = "split"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"


class Portfolio(Base):
    """Portefeuille d'investissement."""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    portfolio_type = Column(String(50), nullable=False)  # PEA, CTO, AV, etc.
    broker = Column(String(100))  # Courtier (Boursorama, Degiro, etc.)
    description = Column(Text)

    # Devise de référence
    currency = Column(String(10), default="EUR")

    # Dates
    opened_date = Column(DateTime)  # Date d'ouverture du compte
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Objectifs
    target_value = Column(Float)  # Objectif de valorisation
    monthly_contribution = Column(Float)  # Versement mensuel prévu

    # Est actif ?
    is_active = Column(Boolean, default=True)

    # Relations
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Portfolio(name='{self.name}', type='{self.portfolio_type}')>"


class Position(Base):
    """Position dans un portefeuille."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)

    # Identification de l'actif
    ticker = Column(String(20), nullable=False)
    name = Column(String(255))
    asset_type = Column(String(50), default="stock")  # stock, etf, bond, crypto, fond

    # Position actuelle
    quantity = Column(Float, nullable=False, default=0)
    average_cost = Column(Float)  # Prix de revient unitaire
    total_cost = Column(Float)  # Coût total d'acquisition

    # Devise de l'actif
    currency = Column(String(10), default="EUR")

    # Métadonnées
    sector = Column(String(100))
    country = Column(String(50))

    # Notes
    notes = Column(Text)

    # Dates
    first_buy_date = Column(DateTime)
    last_transaction_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    portfolio = relationship("Portfolio", back_populates="positions")
    transactions = relationship("Transaction", back_populates="position", cascade="all, delete-orphan")
    dividends = relationship("DividendReceived", back_populates="position", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_position_portfolio_ticker', 'portfolio_id', 'ticker'),
    )

    def __repr__(self):
        return f"<Position(ticker='{self.ticker}', qty={self.quantity})>"


class Transaction(Base):
    """Transaction d'achat/vente."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True)

    # Type et détails
    transaction_type = Column(String(20), nullable=False)  # buy, sell, dividend, split
    ticker = Column(String(20), nullable=False)

    # Montants
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # Prix unitaire
    total_amount = Column(Float)  # Montant total
    fees = Column(Float, default=0)  # Frais de courtage

    # Devise
    currency = Column(String(10), default="EUR")
    exchange_rate = Column(Float, default=1.0)  # Taux de change si devise étrangère

    # Date de la transaction
    transaction_date = Column(DateTime, nullable=False)
    settlement_date = Column(DateTime)  # Date de règlement

    # Notes
    notes = Column(Text)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    portfolio = relationship("Portfolio", back_populates="transactions")
    position = relationship("Position", back_populates="transactions")

    __table_args__ = (
        Index('idx_transaction_portfolio', 'portfolio_id'),
        Index('idx_transaction_date', 'transaction_date'),
        Index('idx_transaction_ticker', 'ticker'),
    )

    def __repr__(self):
        return f"<Transaction({self.transaction_type} {self.quantity}x {self.ticker})>"


class DividendReceived(Base):
    """Dividendes reçus."""
    __tablename__ = "dividends_received"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)

    # Détails
    ticker = Column(String(20), nullable=False)
    ex_date = Column(DateTime)  # Date ex-dividende
    payment_date = Column(DateTime, nullable=False)  # Date de paiement

    # Montants
    amount_per_share = Column(Float)  # Dividende par action
    shares_held = Column(Float)  # Nombre d'actions détenues
    gross_amount = Column(Float, nullable=False)  # Montant brut
    tax_withheld = Column(Float, default=0)  # Retenue à la source
    net_amount = Column(Float)  # Montant net

    # Devise
    currency = Column(String(10), default="EUR")

    # Type de dividende
    dividend_type = Column(String(50))  # regular, special, return_of_capital

    # Réinvestissement automatique ?
    is_drip = Column(Boolean, default=False)

    # Notes
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    position = relationship("Position", back_populates="dividends")

    __table_args__ = (
        Index('idx_dividend_position', 'position_id'),
        Index('idx_dividend_date', 'payment_date'),
    )


class Catalyst(Base):
    """Catalyseurs et événements."""
    __tablename__ = "catalysts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    event_type = Column(String(50), nullable=False)  # earnings, dividend, split, merger, fda, etc.
    title = Column(String(255))
    description = Column(Text)

    event_date = Column(DateTime, nullable=False)
    is_confirmed = Column(Boolean, default=True)

    # Impact estimé
    expected_impact = Column(String(20))  # positive, negative, neutral, unknown

    created_at = Column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock")

    __table_args__ = (
        Index('idx_catalyst_stock', 'stock_id'),
        Index('idx_catalyst_date', 'event_date'),
    )


# Référentiels d'indices
class IndexConstituent(Base):
    """Composition des indices."""
    __tablename__ = "index_constituents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_name = Column(String(50), nullable=False)  # CAC40, SBF120, SP500, NASDAQ100
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)

    weight = Column(Float)  # Poids dans l'indice
    added_date = Column(DateTime)

    stock = relationship("Stock")

    __table_args__ = (
        Index('idx_constituent_index', 'index_name'),
    )


def init_db(db_url: str = "sqlite:///data/stock_advisor.db"):
    """Initialise la base de données."""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Crée une session."""
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    # Test de création de la base
    engine = init_db()
    print("Base de données créée avec succès!")
