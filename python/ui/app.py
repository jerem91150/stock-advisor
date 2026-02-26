"""
Interface Streamlit - Stock Advisor v4.0
Dashboard complet avec 593 actions, Multi-portefeuilles, IA et fonctionnalités avancées
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.yahoo_finance import YahooFinanceScraper
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.fundamental import FundamentalAnalyzer
from src.filters.base import (
    FilterManager, StockFilterData, SectorFilter, EthicalFilter,
    FundamentalFilter, GeographicFilter
)
from src.hardware.detector import HardwareDetector
from src.portfolio.manager import PortfolioManager, PortfolioSummary, PositionDetail
from src.portfolio.dividend_tracker import DividendTracker, get_dividend_tracker
from src.analysis.moning_scores import MoningStyleScorer, get_moning_scorer
from src.analysis.projections import ProjectionEngine, RiskProfile, get_projection_engine
from src.analysis.etf_analyzer import ETFAnalyzer, get_etf_analyzer, ETF_UNIVERSE
from src.analysis.ai_advisor import AIPortfolioAdvisor, get_ai_advisor
from src.data.stock_universe import (
    get_all_stocks, get_stocks_by_region, get_pea_eligible, get_stock_count,
    SP500_TOP100, NASDAQ100, CAC40, DAX40, FTSE100, NIKKEI_TOP50, HANGSENG
)

# Import des pages étendues (v4.0)
try:
    from pages_extended import get_extended_pages, EXTENDED_PAGES
    HAS_EXTENDED_PAGES = True
except ImportError:
    HAS_EXTENDED_PAGES = False
    EXTENDED_PAGES = {}

# Configuration de la page
st.set_page_config(
    page_title="Stock Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé - Design moderne SaaS
st.markdown("""
<style>
    /* ========== Variables et Reset ========== */
    :root {
        --primary: #6366f1;
        --primary-dark: #4f46e5;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --bg-dark: #0f172a;
        --bg-card: #1e293b;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --border: #334155;
    }

    /* ========== Global Styles ========== */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }

    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }

    /* ========== Sidebar ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 1px solid #334155;
    }

    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label {
        color: #e2e8f0 !important;
        font-weight: 500;
    }

    /* ========== Headers ========== */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }

    h1 {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem !important;
    }

    /* ========== Metric Cards ========== */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e293b, #334155);
        border: 1px solid #475569;
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
    }

    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.875rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    [data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.875rem !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricDelta"] > div {
        font-weight: 600 !important;
    }

    /* ========== Buttons ========== */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
        box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.4);
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        transform: translateY(-1px);
        box-shadow: 0 6px 10px -1px rgba(99, 102, 241, 0.5);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* ========== DataFrames ========== */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
    }

    .stDataFrame [data-testid="stDataFrameContainer"] {
        background: #1e293b;
    }

    /* ========== Selectbox & Inputs ========== */
    .stSelectbox > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: #1e293b !important;
        border: 1px solid #475569 !important;
        border-radius: 10px !important;
        color: #f8fafc !important;
    }

    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
    }

    /* ========== Tabs ========== */
    .stTabs [data-baseweb="tab-list"] {
        background: #1e293b;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white !important;
    }

    /* ========== Expander ========== */
    .streamlit-expanderHeader {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
    }

    .streamlit-expanderContent {
        background: #1e293b !important;
        border: 1px solid #334155 !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }

    /* ========== Custom Cards ========== */
    .score-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        margin: 12px 0;
        border: 1px solid #475569;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }

    .score-high {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        border: none;
        color: white;
    }

    .score-medium {
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
        border: none;
        color: white;
    }

    .score-low {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        border: none;
        color: white;
    }

    .metric-card {
        background: linear-gradient(145deg, #1e293b, #334155);
        padding: 20px;
        border-radius: 16px;
        margin: 8px 0;
        border: 1px solid #475569;
    }

    .pea-badge {
        background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .cto-badge {
        background: linear-gradient(135deg, #475569 0%, #64748b 100%);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .opportunity-card {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
        padding: 28px;
        border-radius: 20px;
        color: white;
        margin: 16px 0;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.4);
        transition: transform 0.3s, box-shadow 0.3s;
    }

    .opportunity-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.5);
    }

    .stock-row {
        padding: 16px;
        border-bottom: 1px solid #334155;
        transition: background 0.2s;
    }

    .stock-row:hover {
        background: rgba(99, 102, 241, 0.1);
    }

    /* ========== Progress bars ========== */
    .stProgress > div > div {
        background: linear-gradient(90deg, #6366f1, #8b5cf6, #a855f7);
        border-radius: 10px;
    }

    /* ========== Dividers ========== */
    hr {
        border-color: #334155 !important;
    }

    /* ========== Scrollbar ========== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #1e293b;
    }

    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #64748b;
    }

    /* ========== Charts ========== */
    .js-plotly-plot {
        border-radius: 16px;
        overflow: hidden;
    }

    /* ========== Info/Warning/Error boxes ========== */
    .stAlert {
        border-radius: 12px;
        border: none;
    }

    /* ========== Markdown text ========== */
    .stMarkdown {
        color: #e2e8f0;
    }

    p, span, label {
        color: #e2e8f0 !important;
    }

    /* ========== Number styling in metrics ========== */
    .big-number {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# UNIVERS D'ACTIONS (593 actions de 17 indices mondiaux)
# ============================================================================
STOCKS_US = get_stocks_by_region('USA')  # ~150 actions
STOCKS_EU = get_stocks_by_region('EUROPE')  # ~200 actions
STOCKS_ASIA = get_stocks_by_region('ASIE')  # ~100 actions
STOCKS_PEA = get_pea_eligible()  # ~185 actions éligibles PEA

ALL_STOCKS = get_all_stocks()  # 593 actions uniques

# Statistiques de l'univers
STOCK_UNIVERSE_STATS = get_stock_count()

# ============================================================================
# INITIALISATION DES SERVICES
# ============================================================================
@st.cache_resource
def init_services():
    """Initialise les services (singleton)."""
    return {
        "scraper": YahooFinanceScraper(),
        "technical_analyzer": TechnicalAnalyzer(),
        "fundamental_analyzer": FundamentalAnalyzer(),
        "filter_manager": FilterManager(),
        "hardware_detector": HardwareDetector(),
        "portfolio_manager": PortfolioManager(),
        "dividend_tracker": DividendTracker(),
        "moning_scorer": MoningStyleScorer(),
        "projection_engine": ProjectionEngine(),
        "etf_analyzer": ETFAnalyzer(),
        "ai_advisor": AIPortfolioAdvisor()
    }

services = init_services()

# ============================================================================
# GESTION DU PORTEFEUILLE (Session State)
# ============================================================================
def init_portfolio():
    """Initialise le portefeuille dans la session."""
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = {
            'positions': {},  # {ticker: {'shares': n, 'avg_cost': x, 'date': d}}
            'cash': 10000.0,
            'transactions': []
        }
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = []

init_portfolio()

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================
def get_score_color(score: float) -> str:
    """Retourne la couleur selon le score."""
    if score >= 70:
        return "score-high"
    elif score >= 40:
        return "score-medium"
    else:
        return "score-low"

def get_score_emoji(score: float) -> str:
    """Retourne l'emoji selon le score."""
    if score >= 70:
        return "🟢"
    elif score >= 55:
        return "🟡"
    elif score >= 40:
        return "🟠"
    else:
        return "🔴"

def is_pea_eligible(ticker: str) -> bool:
    """Vérifie si une action est éligible PEA."""
    return ticker in STOCKS_PEA or any(x in ticker.upper() for x in ['.PA', '.DE', '.AS', '.MC', '.MI', '.BR'])

# ============================================================================
# PARTICIPATIONS DE L'ETAT FRANCAIS (APE - Agence des Participations de l'Etat)
# Source: https://www.economie.gouv.fr/agence-participations-etat
# ============================================================================
FRENCH_STATE_HOLDINGS = {
    # Entreprise: (ticker, % participation, type)
    "EDF.PA": {"pct": 100.0, "type": "Controle total", "nom": "EDF"},
    "ENGI.PA": {"pct": 23.6, "type": "Actionnaire de reference", "nom": "Engie"},
    "ORA.PA": {"pct": 13.4, "type": "Actionnaire significatif", "nom": "Orange"},
    "TTE.PA": {"pct": 0.0, "type": "Action specifique (golden share)", "nom": "TotalEnergies"},
    "RNO.PA": {"pct": 15.0, "type": "Actionnaire de reference", "nom": "Renault"},
    "AIR.PA": {"pct": 11.1, "type": "Actionnaire significatif", "nom": "Airbus"},
    "SAF.PA": {"pct": 11.2, "type": "Actionnaire significatif", "nom": "Safran"},
    "HO.PA": {"pct": 25.7, "type": "Actionnaire de reference", "nom": "Thales"},
    "AOM.PA": {"pct": 29.3, "type": "Actionnaire de reference", "nom": "Aeroports de Paris"},
    "AF.PA": {"pct": 28.6, "type": "Actionnaire de reference", "nom": "Air France-KLM"},
    "DG.PA": {"pct": 7.6, "type": "Actionnaire significatif", "nom": "Vinci (via Bpifrance)"},
    "STM.PA": {"pct": 13.8, "type": "Actionnaire significatif (via Bpifrance)", "nom": "STMicroelectronics"},
    "SU.PA": {"pct": 3.4, "type": "Participation indirecte (Bpifrance)", "nom": "Schneider Electric"},
    "FDJ.PA": {"pct": 20.5, "type": "Actionnaire de reference", "nom": "La Francaise des Jeux"},
    "LR.PA": {"pct": 22.4, "type": "Actionnaire de reference", "nom": "Legrand (via Bpifrance)"},
    "DSY.PA": {"pct": 0.0, "type": "Participation indirecte (Bpifrance)", "nom": "Dassault Systemes"},
    "AM.PA": {"pct": 0.0, "type": "Participation indirecte (Bpifrance)", "nom": "Dassault Aviation"},
    "CNP.PA": {"pct": 62.1, "type": "Controle (via La Banque Postale/CDC)", "nom": "CNP Assurances"},
}


def get_french_state_info(ticker: str) -> dict | None:
    """Retourne les infos de participation de l'Etat francais, ou None."""
    return FRENCH_STATE_HOLDINGS.get(ticker.upper())

def create_gauge_chart(score: float, title: str) -> go.Figure:
    """Crée un graphique gauge pour le score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 40], 'color': "#dc3545"},
                {'range': [40, 70], 'color': "#ffc107"},
                {'range': [70, 100], 'color': "#28a745"}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig

def create_price_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """Crée un graphique de prix avec indicateurs."""
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='Prix'
    ))

    # Moyennes mobiles
    if len(df) >= 20:
        df['MA20'] = df['Close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA20'],
            mode='lines', name='MA20',
            line=dict(color='orange', width=1)
        ))

    if len(df) >= 50:
        df['MA50'] = df['Close'].rolling(window=50).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA50'],
            mode='lines', name='MA50',
            line=dict(color='blue', width=1)
        ))

    fig.update_layout(
        title=f'{ticker} - Historique des prix',
        yaxis_title='Prix',
        xaxis_rangeslider_visible=False,
        height=400
    )

    return fig

# ============================================================================
# CALCUL DU SCORE COMPLET
# ============================================================================
@st.cache_data(ttl=3600)  # Cache 1 heure
def calculate_full_score(ticker: str) -> dict:
    """
    Calcule le score complet d'une action (4 composantes).
    Retourne un dict avec tous les détails.
    """
    try:
        import yfinance as yf
        import numpy as np

        # Récupérer les données
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty or len(hist) < 50:
            return None

        info = stock.info

        result = {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'price': info.get('currentPrice') or info.get('regularMarketPrice', 0),
            'currency': info.get('currency', 'USD'),
            'sector': info.get('sector', 'N/A'),
            'pea_eligible': is_pea_eligible(ticker),
            'french_state': get_french_state_info(ticker),
            'scores': {},
            'details': {}
        }

        # Seuils P/E par secteur
        sector_pe = {
            'Energy': {'very_low': 5, 'low': 8, 'fair': 12, 'high': 18, 'very_high': 25},
            'Technology': {'very_low': 12, 'low': 18, 'fair': 28, 'high': 40, 'very_high': 55},
            'Financial Services': {'very_low': 6, 'low': 9, 'fair': 14, 'high': 20, 'very_high': 28},
            'Healthcare': {'very_low': 12, 'low': 18, 'fair': 28, 'high': 40, 'very_high': 55},
            'Consumer Cyclical': {'very_low': 8, 'low': 13, 'fair': 20, 'high': 28, 'very_high': 38},
            'Consumer Defensive': {'very_low': 12, 'low': 16, 'fair': 22, 'high': 28, 'very_high': 36},
            'Industrials': {'very_low': 10, 'low': 14, 'fair': 20, 'high': 28, 'very_high': 38},
            'Utilities': {'very_low': 10, 'low': 14, 'fair': 18, 'high': 24, 'very_high': 32},
            'Real Estate': {'very_low': 12, 'low': 18, 'fair': 28, 'high': 40, 'very_high': 55},
            'Basic Materials': {'very_low': 6, 'low': 9, 'fair': 14, 'high': 20, 'very_high': 28},
            'Communication Services': {'very_low': 12, 'low': 16, 'fair': 24, 'high': 32, 'very_high': 45},
        }
        default_pe = {'very_low': 8, 'low': 13, 'fair': 20, 'high': 30, 'very_high': 42}
        sector = info.get('sector', 'N/A')
        pe_thresh = sector_pe.get(sector, default_pe)

        # 1. SCORE TECHNIQUE (30%)
        current_price = float(hist['Close'].iloc[-1])
        ma50 = float(hist['Close'].tail(50).mean())
        ma200 = float(hist['Close'].mean()) if len(hist) >= 200 else ma50

        tech_score = 50
        tech_details = []

        # Prix vs MA50 (bonus réduit de +15 à +10)
        if current_price > ma50 * 1.02:
            tech_score += 10
            tech_details.append("Prix > MA50 (+10)")
        elif current_price > ma50:
            tech_score += 5
            tech_details.append("Prix ~ MA50 (+5)")
        elif current_price < ma50 * 0.95:
            tech_score -= 15
            tech_details.append("Prix << MA50 (-15)")
        elif current_price < ma50 * 0.98:
            tech_score -= 10
            tech_details.append("Prix < MA50 (-10)")

        # MA50 vs MA200
        if ma50 > ma200 * 1.05:
            tech_score += 15
            tech_details.append("Golden Cross fort (+15)")
        elif ma50 > ma200:
            tech_score += 5
            tech_details.append("MA50 > MA200 (+5)")
        elif ma50 < ma200 * 0.95:
            tech_score -= 15
            tech_details.append("Death Cross (-15)")
        elif ma50 < ma200:
            tech_score -= 5
            tech_details.append("MA50 < MA200 (-5)")

        # RSI 14 jours
        if len(hist) >= 14:
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, np.inf)
            rsi_val = float((100 - (100 / (1 + rs))).iloc[-1])

            if rsi_val > 80:
                tech_score -= 15
                tech_details.append(f"RSI={rsi_val:.0f} surachat fort (-15)")
            elif rsi_val > 70:
                tech_score -= 10
                tech_details.append(f"RSI={rsi_val:.0f} surachat (-10)")
            elif rsi_val > 65:
                tech_score -= 5
                tech_details.append(f"RSI={rsi_val:.0f} surachat leger (-5)")
            elif rsi_val < 25:
                tech_score += 15
                tech_details.append(f"RSI={rsi_val:.0f} survente forte (+15)")
            elif rsi_val < 30:
                tech_score += 10
                tech_details.append(f"RSI={rsi_val:.0f} survente (+10)")
            elif rsi_val < 40:
                tech_score += 5
                tech_details.append(f"RSI={rsi_val:.0f} zone basse (+5)")

        # Distance au 52w high
        high_52w = float(hist['High'].max())
        if high_52w > 0:
            pct_from_high = current_price / high_52w
            if pct_from_high > 0.95:
                tech_score -= 10
                tech_details.append(f"Proche 52w high {pct_from_high*100:.0f}% (-10)")
            elif pct_from_high > 0.90:
                tech_score -= 5
                tech_details.append(f"Proche 52w high {pct_from_high*100:.0f}% (-5)")
            elif pct_from_high < 0.65:
                tech_score -= 5
                tech_details.append(f"Loin du 52w high {pct_from_high*100:.0f}% (-5)")

        # Distance au MA200 (trop etire au-dessus)
        if len(hist) >= 200 and ma200 > 0:
            pct_above_ma200 = current_price / ma200
            if pct_above_ma200 > 1.30:
                tech_score -= 10
                tech_details.append(f"Trop etire +{(pct_above_ma200-1)*100:.0f}% vs MA200 (-10)")
            elif pct_above_ma200 > 1.20:
                tech_score -= 5
                tech_details.append(f"Etire +{(pct_above_ma200-1)*100:.0f}% vs MA200 (-5)")

        # Pente MA50 (tendance moyen terme)
        if len(hist) >= 60:
            ma50_now = float(hist['Close'].tail(50).mean())
            ma50_prev = float(hist['Close'].iloc[-60:-10].tail(50).mean())
            if ma50_prev > 0:
                ma50_slope = (ma50_now / ma50_prev - 1) * 100
                if ma50_slope < -2:
                    tech_score -= 8
                    tech_details.append(f"MA50 en baisse {ma50_slope:.1f}% (-8)")
                elif ma50_slope < 0:
                    tech_score -= 3
                    tech_details.append(f"MA50 s'aplatit {ma50_slope:.1f}% (-3)")

        # Momentum 1 mois (avec gradient)
        if len(hist) >= 21:
            price_1m = float(hist['Close'].iloc[-21])
            mom_1m = (current_price / price_1m - 1) * 100
            if mom_1m > 10:
                tech_score += 10
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+10)")
            elif mom_1m > 5:
                tech_score += 5
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+5)")
            elif mom_1m > 2:
                tech_score += 2
                tech_details.append(f"Momentum 1M: +{mom_1m:.1f}% (+2)")
            elif mom_1m < -10:
                tech_score -= 15
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-15)")
            elif mom_1m < -5:
                tech_score -= 10
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-10)")
            elif mom_1m < -2:
                tech_score -= 5
                tech_details.append(f"Momentum 1M: {mom_1m:.1f}% (-5)")

        tech_score = max(0, min(100, tech_score))
        result['scores']['technical'] = tech_score
        result['details']['technical'] = tech_details

        # 2. SCORE FONDAMENTAL (30%)
        fund_score = 50
        fund_details = []

        # P/E ajuste par secteur avec gradient
        pe = info.get('trailingPE')
        if pe and pe > 0:
            if pe < pe_thresh['very_low']:
                fund_score += 15
                fund_details.append(f"P/E={pe:.1f} tres bas vs secteur (+15)")
            elif pe < pe_thresh['low']:
                fund_score += 10
                fund_details.append(f"P/E={pe:.1f} bas vs secteur (+10)")
            elif pe < pe_thresh['fair']:
                fund_score += 5
                fund_details.append(f"P/E={pe:.1f} correct vs secteur (+5)")
            elif pe < pe_thresh['high']:
                fund_details.append(f"P/E={pe:.1f} dans la norme secteur")
            elif pe < pe_thresh['very_high']:
                fund_score -= 10
                fund_details.append(f"P/E={pe:.1f} eleve vs secteur (-10)")
            else:
                fund_score -= 15
                fund_details.append(f"P/E={pe:.1f} tres eleve vs secteur (-15)")
        elif pe and pe < 0:
            fund_score -= 10
            fund_details.append("P/E negatif (non rentable) (-10)")

        # PEG ratio
        peg = info.get('pegRatio')
        if peg and peg > 0:
            if peg < 0.5:
                fund_score += 12
                fund_details.append(f"PEG={peg:.2f} tres attractif (+12)")
            elif peg < 1.0:
                fund_score += 8
                fund_details.append(f"PEG={peg:.2f} attractif (+8)")
            elif peg < 1.5:
                fund_score += 3
                fund_details.append(f"PEG={peg:.2f} correct (+3)")
            elif peg > 3.0:
                fund_score -= 10
                fund_details.append(f"PEG={peg:.2f} tres eleve (-10)")
            elif peg > 2.0:
                fund_score -= 5
                fund_details.append(f"PEG={peg:.2f} eleve (-5)")

        # Marge beneficiaire
        margin = info.get('profitMargins')
        if margin is not None:
            margin_pct = margin * 100
            if margin_pct > 25:
                fund_score += 10
                fund_details.append(f"Marge={margin_pct:.1f}% excellente (+10)")
            elif margin_pct > 15:
                fund_score += 5
                fund_details.append(f"Marge={margin_pct:.1f}% bonne (+5)")
            elif margin_pct > 5:
                fund_details.append(f"Marge={margin_pct:.1f}% correcte")
            elif margin_pct > 0:
                fund_score -= 5
                fund_details.append(f"Marge={margin_pct:.1f}% faible (-5)")
            else:
                fund_score -= 10
                fund_details.append(f"Marge={margin_pct:.1f}% negative (-10)")

        # ROE avec gradient
        roe = info.get('returnOnEquity')
        if roe is not None:
            roe_pct = roe * 100
            if roe_pct > 25:
                fund_score += 12
                fund_details.append(f"ROE={roe_pct:.1f}% excellent (+12)")
            elif roe_pct > 15:
                fund_score += 8
                fund_details.append(f"ROE={roe_pct:.1f}% bon (+8)")
            elif roe_pct > 10:
                fund_score += 3
                fund_details.append(f"ROE={roe_pct:.1f}% correct (+3)")
            elif roe_pct > 0:
                fund_score -= 3
                fund_details.append(f"ROE={roe_pct:.1f}% faible (-3)")
            else:
                fund_score -= 12
                fund_details.append(f"ROE={roe_pct:.1f}% negatif (-12)")

        # Dette/Equity avec gradient
        debt = info.get('debtToEquity')
        if debt is not None:
            if debt < 30:
                fund_score += 8
                fund_details.append(f"Debt/Eq={debt:.0f}% faible (+8)")
            elif debt < 80:
                fund_score += 3
                fund_details.append(f"Debt/Eq={debt:.0f}% modere (+3)")
            elif debt > 200:
                fund_score -= 12
                fund_details.append(f"Debt/Eq={debt:.0f}% tres eleve (-12)")
            elif debt > 150:
                fund_score -= 8
                fund_details.append(f"Debt/Eq={debt:.0f}% eleve (-8)")

        fund_score = max(0, min(100, fund_score))
        result['scores']['fundamental'] = fund_score
        result['details']['fundamental'] = fund_details

        # 3. SCORE SENTIMENT (20%) - Momentum court & moyen terme
        sent_score = 50
        sent_details = []

        # Momentum 5 jours (gradient)
        if len(hist) >= 5:
            price_5d = float(hist['Close'].iloc[-5])
            mom_5d = (current_price / price_5d - 1) * 100
            if mom_5d > 5:
                sent_score += 15
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% fort (+15)")
            elif mom_5d > 2:
                sent_score += 10
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% (+10)")
            elif mom_5d > 0:
                sent_score += 3
                sent_details.append(f"Momentum 5j: +{mom_5d:.1f}% (+3)")
            elif mom_5d > -2:
                sent_score -= 3
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% (-3)")
            elif mom_5d > -5:
                sent_score -= 10
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% (-10)")
            else:
                sent_score -= 18
                sent_details.append(f"Momentum 5j: {mom_5d:.1f}% fort (-18)")

        # Momentum 3 mois (perspective moyen terme)
        if len(hist) >= 63:
            price_3m = float(hist['Close'].iloc[-63])
            mom_3m = (current_price / price_3m - 1) * 100
            if mom_3m > 15:
                sent_score += 10
                sent_details.append(f"Momentum 3M: +{mom_3m:.1f}% (+10)")
            elif mom_3m > 5:
                sent_score += 5
                sent_details.append(f"Momentum 3M: +{mom_3m:.1f}% (+5)")
            elif mom_3m < -15:
                sent_score -= 12
                sent_details.append(f"Momentum 3M: {mom_3m:.1f}% (-12)")
            elif mom_3m < -5:
                sent_score -= 6
                sent_details.append(f"Momentum 3M: {mom_3m:.1f}% (-6)")

        # Volume analysis (bonus ET malus)
        avg_vol = float(hist['Volume'].mean())
        recent_vol = float(hist['Volume'].tail(5).mean())
        if avg_vol > 0:
            vol_ratio = recent_vol / avg_vol
            if vol_ratio > 2.0:
                sent_score += 8
                sent_details.append(f"Volume tres eleve x{vol_ratio:.1f} (+8)")
            elif vol_ratio > 1.5:
                sent_score += 5
                sent_details.append(f"Volume eleve x{vol_ratio:.1f} (+5)")
            elif vol_ratio < 0.5:
                sent_score -= 8
                sent_details.append(f"Volume tres faible x{vol_ratio:.1f} (-8)")
            elif vol_ratio < 0.7:
                sent_score -= 4
                sent_details.append(f"Volume faible x{vol_ratio:.1f} (-4)")

        sent_score = max(0, min(100, sent_score))
        result['scores']['sentiment'] = sent_score
        result['details']['sentiment'] = sent_details

        # 4. SCORE SMART MONEY (20%) - Proxy institutionnel + coherence
        smart_score = 40  # Base plus basse si pas de donnees
        smart_details = []

        inst_hold = info.get('heldPercentInstitutions')
        if inst_hold is not None:
            smart_score = 45  # On a des donnees, base un peu plus haute
            if inst_hold > 0.80:
                smart_score += 10
                smart_details.append(f"Instit: {inst_hold*100:.0f}% tres eleve (+10)")
            elif inst_hold > 0.60:
                smart_score += 8
                smart_details.append(f"Instit: {inst_hold*100:.0f}% eleve (+8)")
            elif inst_hold > 0.40:
                smart_score += 5
                smart_details.append(f"Instit: {inst_hold*100:.0f}% modere (+5)")
            elif inst_hold < 0.20:
                smart_score -= 5
                smart_details.append(f"Instit: {inst_hold*100:.0f}% faible (-5)")
        else:
            smart_details.append("Pas de donnees institutionnelles (base 40)")

        insider_hold = info.get('heldPercentInsiders')
        if insider_hold and insider_hold > 0.10:
            smart_score += 8
            smart_details.append(f"Insiders: {insider_hold*100:.1f}% significatif (+8)")
        elif insider_hold and insider_hold > 0.05:
            smart_score += 5
            smart_details.append(f"Insiders: {insider_hold*100:.1f}% (+5)")

        # Coherence prix vs earnings (forward PE vs trailing PE)
        forward_pe = info.get('forwardPE')
        trailing_pe = info.get('trailingPE')
        if forward_pe and trailing_pe and forward_pe > 0 and trailing_pe > 0:
            pe_ratio = forward_pe / trailing_pe
            if pe_ratio < 0.8:
                smart_score += 8
                smart_details.append("Forward PE < Trailing PE, croissance attendue (+8)")
            elif pe_ratio > 1.3:
                smart_score -= 8
                smart_details.append("Forward PE > Trailing PE, ralentissement attendu (-8)")

        smart_score = max(0, min(100, smart_score))
        result['scores']['smart_money'] = smart_score
        result['details']['smart_money'] = smart_details

        # SCORE GLOBAL (pondere)
        global_score = (
            result['scores']['technical'] * 0.30 +
            result['scores']['fundamental'] * 0.30 +
            result['scores']['sentiment'] * 0.20 +
            result['scores']['smart_money'] * 0.20
        )
        result['scores']['global'] = global_score

        # Recommandation (seuils releves)
        if global_score >= 78:
            result['recommendation'] = "ACHAT FORT"
            result['rec_color'] = "green"
        elif global_score >= 62:
            result['recommendation'] = "ACHAT"
            result['rec_color'] = "lightgreen"
        elif global_score >= 42:
            result['recommendation'] = "CONSERVER"
            result['rec_color'] = "orange"
        elif global_score >= 30:
            result['recommendation'] = "VENDRE"
            result['rec_color'] = "salmon"
        else:
            result['recommendation'] = "VENTE FORTE"
            result['rec_color'] = "red"

        return result

    except Exception as e:
        return None

# ============================================================================
# PAGE: DASHBOARD
# ============================================================================
def page_dashboard():
    """Page principale - Dashboard."""
    st.title("📈 Stock Advisor - Dashboard")

    # Mode de compte
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        account_mode = st.radio("Mode", ["CTO (Mondial)", "PEA (Europe)"], horizontal=True)

    pea_mode = "PEA" in account_mode

    # Résumé du portefeuille global
    st.subheader("💼 Mes Portefeuilles")

    pm = services["portfolio_manager"]
    global_summary = pm.get_all_portfolios_summary()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Portefeuilles", f"{global_summary['portfolios_count']}")
    with col2:
        st.metric("Valeur Totale", f"{global_summary['total_value']:,.2f} €")
    with col3:
        st.metric("Total Investi", f"{global_summary['total_invested']:,.2f} €")
    with col4:
        if global_summary['total_invested'] > 0:
            st.metric("Performance", f"{global_summary['total_gain_pct']:+.1f}%",
                     delta=f"{global_summary['total_gain']:+,.0f}€")
        else:
            st.metric("Performance", "N/A")

    # Mini cartes des portefeuilles
    portfolios = pm.get_all_portfolios()
    if portfolios:
        cols = st.columns(min(len(portfolios), 4))
        for i, portfolio in enumerate(portfolios[:4]):
            summary = pm.get_portfolio_summary(portfolio.id)
            if summary:
                with cols[i]:
                    color = "#28a745" if summary.total_gain >= 0 else "#dc3545"
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px;
                                border-left: 4px solid {color};">
                        <strong>{summary.name}</strong><br>
                        <span style="font-size: 1.2em;">{summary.current_value:,.0f}€</span><br>
                        <small style="color: {color};">{summary.total_gain_pct:+.1f}%</small>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("Aucun portefeuille créé. Allez dans 'Mes Portefeuilles' pour commencer.")

    st.divider()

    # Recherche rapide
    st.subheader("🔍 Rechercher une Action")

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Symbole (ex: AAPL, MC.PA)", key="search_ticker").upper()
    with col2:
        st.write("")
        st.write("")
        if st.button("🔍 Analyser", type="primary"):
            if ticker:
                st.session_state.analyze_ticker = ticker

    # Actions populaires
    st.subheader("⚡ Actions Populaires")

    popular = ["AAPL", "NVDA", "MSFT", "TSLA", "MC.PA", "ASML.AS", "SAP.DE", "7203.T"]  # + Toyota
    cols = st.columns(len(popular))
    for i, stock in enumerate(popular):
        with cols[i]:
            if st.button(stock, key=f"pop_{stock}"):
                st.session_state.analyze_ticker = stock

    # Afficher analyse si demandée
    if 'analyze_ticker' in st.session_state and st.session_state.analyze_ticker:
        analyze_stock_detailed(st.session_state.analyze_ticker)

# ============================================================================
# PAGE: TOP OPPORTUNITÉS
# ============================================================================
def page_opportunities():
    """Page Top Opportunités - Classement des meilleures actions."""
    st.title("🏆 Top Opportunités")

    # Afficher les stats de l'univers
    st.caption(f"Univers: {len(ALL_STOCKS)} actions | PEA: {len(STOCKS_PEA)} | USA: {len(STOCKS_US)} | Europe: {len(STOCKS_EU)} | Asie: {len(STOCKS_ASIA)}")

    # Filtres
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        market = st.selectbox("Marché", [
            "🌍 Tous (593)",
            "🇺🇸 USA (150)",
            "🇪🇺 Europe (200)",
            "🇫🇷 France (86)",
            "🇩🇪 Allemagne (40)",
            "🇬🇧 UK (40)",
            "🇯🇵 Japon (50)",
            "🇨🇳 Chine (50)",
            "🇨🇭 Suisse (20)",
            "🇨🇦 Canada (25)",
            "🇦🇺 Australie (25)",
        ])
    with col2:
        min_score = st.slider("Score minimum", 0, 100, 55)
    with col3:
        max_stocks = st.slider("Analyser (max)", 10, 100, 30)
    with col4:
        pea_only = st.checkbox("PEA uniquement", value=False)

    # Sélectionner les actions selon le marché
    market_key = market.split()[1] if len(market.split()) > 1 else "Tous"
    market_map = {
        "Tous": ALL_STOCKS,
        "USA": STOCKS_US,
        "Europe": STOCKS_EU,
        "France": get_stocks_by_region('FRANCE'),
        "Allemagne": get_stocks_by_region('ALLEMAGNE'),
        "UK": get_stocks_by_region('UK'),
        "Japon": get_stocks_by_region('JAPON'),
        "Chine": get_stocks_by_region('CHINE'),
        "Suisse": get_stocks_by_region('SUISSE'),
        "Canada": get_stocks_by_region('CANADA'),
        "Australie": get_stocks_by_region('AUSTRALIE'),
    }
    stocks_to_analyze = market_map.get(market_key, ALL_STOCKS)

    if pea_only:
        stocks_to_analyze = [s for s in stocks_to_analyze if is_pea_eligible(s)]

    # Limiter le nombre pour la performance
    stocks_to_analyze = stocks_to_analyze[:max_stocks]

    # Analyser toutes les actions
    st.write(f"Analyse de {len(stocks_to_analyze)} actions...")

    progress_bar = st.progress(0)
    results = []

    for i, ticker in enumerate(stocks_to_analyze):
        progress_bar.progress((i + 1) / len(stocks_to_analyze))

        score_data = calculate_full_score(ticker)
        if score_data and score_data['scores']['global'] >= min_score:
            results.append(score_data)

    progress_bar.empty()

    # Trier par score global
    results.sort(key=lambda x: x['scores']['global'], reverse=True)

    # Afficher les résultats
    st.subheader(f"📊 {len(results)} opportunités trouvées")

    if results:
        # Top 3 mis en avant
        st.write("### 🥇 Top 3")
        cols = st.columns(3)
        for i, res in enumerate(results[:3]):
            with cols[i]:
                medal = ["🥇", "🥈", "🥉"][i]
                pea_badge = "🇪🇺 PEA" if res['pea_eligible'] else "🌍 CTO"
                state_info = res.get('french_state')
                state_badge = f"🏛 Etat {state_info['pct']:.0f}%" if state_info and state_info['pct'] > 0 else ("🏛 Golden Share" if state_info else "")

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            padding: 20px; border-radius: 15px; color: white; text-align: center;">
                    <h3>{medal} {res['ticker']}</h3>
                    <p>{res['name'][:25]}...</p>
                    <h2>{res['scores']['global']:.0f}/100</h2>
                    <p>{res['recommendation']}</p>
                    <small>{pea_badge}{' | ' + state_badge if state_badge else ''} | {res['price']:.2f} {res['currency']}</small>
                </div>
                """, unsafe_allow_html=True)

                if st.button(f"Voir détails", key=f"top_{res['ticker']}"):
                    st.session_state.analyze_ticker = res['ticker']

        st.divider()

        # Tableau complet
        st.write("### 📋 Classement complet")

        df = pd.DataFrame([{
            'Rank': i+1,
            'Ticker': r['ticker'],
            'Nom': r['name'][:20],
            'Score': f"{r['scores']['global']:.0f}",
            'Tech': f"{r['scores']['technical']:.0f}",
            'Fond': f"{r['scores']['fundamental']:.0f}",
            'Sent': f"{r['scores']['sentiment']:.0f}",
            'Smart': f"{r['scores']['smart_money']:.0f}",
            'Prix': f"{r['price']:.2f}",
            'PEA': "✅" if r['pea_eligible'] else "❌",
            'Etat FR': f"🏛 {r['french_state']['pct']:.0f}%" if r.get('french_state') and r['french_state']['pct'] > 0 else ("🏛" if r.get('french_state') else ""),
            'Reco': r['recommendation']
        } for i, r in enumerate(results)])

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export CSV
        if st.button("📥 Exporter CSV"):
            csv = df.to_csv(index=False)
            st.download_button(
                label="Télécharger",
                data=csv,
                file_name=f"top_opportunities_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.warning("Aucune opportunité trouvée avec ces critères.")

# ============================================================================
# PAGE: PORTEFEUILLE (Multi-comptes style Moning/Finary)
# ============================================================================
def page_portfolio():
    """Page Portefeuille - Gestion multi-comptes style Moning/Finary."""
    st.title("💼 Mes Portefeuilles")

    pm = services["portfolio_manager"]

    # Sous-navigation
    tab_overview, tab_manage, tab_add_position, tab_dividends, tab_transactions = st.tabs([
        "📊 Vue Globale", "⚙️ Gérer", "➕ Ajouter Position", "💰 Dividendes", "📜 Transactions"
    ])

    # ==================== TAB: VUE GLOBALE ====================
    with tab_overview:
        portfolios = pm.get_all_portfolios()

        if not portfolios:
            st.info("Aucun portefeuille créé. Allez dans l'onglet 'Gérer' pour créer votre premier portefeuille.")
        else:
            # Résumé global
            global_summary = pm.get_all_portfolios_summary()

            st.subheader("🌍 Vue d'Ensemble")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Valeur Totale", f"{global_summary['total_value']:,.2f} €")
            with col2:
                st.metric("Total Investi", f"{global_summary['total_invested']:,.2f} €")
            with col3:
                gain_color = "normal" if global_summary['total_gain'] >= 0 else "inverse"
                st.metric("Plus/Moins Value",
                         f"{global_summary['total_gain']:+,.2f} €",
                         delta=f"{global_summary['total_gain_pct']:+.1f}%")
            with col4:
                st.metric("Dividendes Reçus", f"{global_summary['total_dividends']:,.2f} €")

            st.divider()

            # Cartes des portefeuilles
            st.subheader("📁 Mes Comptes")

            cols = st.columns(min(len(portfolios), 3))
            for i, portfolio in enumerate(portfolios):
                summary = pm.get_portfolio_summary(portfolio.id)
                if not summary:
                    continue

                with cols[i % 3]:
                    # Couleur selon le type
                    colors = {
                        'PEA': ('#007bff', '#0056b3'),
                        'CTO': ('#28a745', '#1e7e34'),
                        'ASSURANCE_VIE': ('#6f42c1', '#59359a'),
                        'PER': ('#fd7e14', '#e06b10'),
                        'CRYPTO': ('#ffc107', '#d39e00'),
                    }
                    color = colors.get(summary.portfolio_type.upper(), ('#6c757d', '#545b62'))

                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, {color[0]} 0%, {color[1]} 100%);
                                padding: 20px; border-radius: 15px; color: white; margin-bottom: 15px;">
                        <h3 style="margin: 0 0 10px 0;">{summary.name}</h3>
                        <p style="margin: 0; opacity: 0.8;">{summary.portfolio_type} | {summary.broker or 'N/A'}</p>
                        <hr style="border-color: rgba(255,255,255,0.3); margin: 10px 0;">
                        <h2 style="margin: 0;">{summary.current_value:,.2f} €</h2>
                        <p style="margin: 5px 0; font-size: 1.1em;">
                            {'+' if summary.total_gain >= 0 else ''}{summary.total_gain:,.2f} €
                            ({'+' if summary.total_gain_pct >= 0 else ''}{summary.total_gain_pct:.1f}%)
                        </p>
                        <small>{summary.positions_count} positions</small>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()

            # Sélection d'un portefeuille pour détails
            st.subheader("🔍 Détails d'un Portefeuille")

            portfolio_names = {p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios}
            selected_id = st.selectbox(
                "Sélectionner un portefeuille",
                options=list(portfolio_names.keys()),
                format_func=lambda x: portfolio_names[x]
            )

            if selected_id:
                display_portfolio_details(pm, selected_id)

    # ==================== TAB: GÉRER ====================
    with tab_manage:
        st.subheader("➕ Créer un Nouveau Portefeuille")

        col1, col2 = st.columns(2)

        with col1:
            new_name = st.text_input("Nom du portefeuille", placeholder="Ex: Mon PEA Boursorama")
            new_type = st.selectbox("Type de compte", ["PEA", "CTO", "ASSURANCE_VIE", "PER", "CRYPTO", "AUTRE"])
            new_broker = st.text_input("Courtier", placeholder="Ex: Boursorama, Degiro, Trade Republic")

        with col2:
            new_currency = st.selectbox("Devise", ["EUR", "USD", "GBP", "CHF"])
            new_target = st.number_input("Objectif de valorisation (€)", min_value=0.0, value=0.0, step=1000.0)
            new_monthly = st.number_input("Versement mensuel prévu (€)", min_value=0.0, value=0.0, step=50.0)

        if st.button("✅ Créer le Portefeuille", type="primary"):
            if new_name:
                try:
                    pm.create_portfolio(
                        name=new_name,
                        portfolio_type=new_type,
                        broker=new_broker if new_broker else None,
                        currency=new_currency,
                        target_value=new_target if new_target > 0 else None,
                        monthly_contribution=new_monthly if new_monthly > 0 else None
                    )
                    st.success(f"Portefeuille '{new_name}' créé avec succès!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")
            else:
                st.error("Veuillez entrer un nom pour le portefeuille")

        st.divider()

        # Liste des portefeuilles existants
        st.subheader("📁 Portefeuilles Existants")

        portfolios = pm.get_all_portfolios()
        if portfolios:
            for portfolio in portfolios:
                with st.expander(f"📂 {portfolio.name} ({portfolio.portfolio_type})"):
                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.write(f"**Courtier:** {portfolio.broker or 'Non renseigné'}")
                        st.write(f"**Devise:** {portfolio.currency}")
                        if portfolio.target_value:
                            st.write(f"**Objectif:** {portfolio.target_value:,.0f} €")

                    with col2:
                        # Export JSON
                        if st.button("📥 Exporter JSON", key=f"export_{portfolio.id}"):
                            json_data = pm.export_portfolio_to_json(portfolio.id)
                            st.download_button(
                                "Télécharger",
                                json_data,
                                file_name=f"{portfolio.name.replace(' ', '_')}.json",
                                mime="application/json",
                                key=f"dl_{portfolio.id}"
                            )

                    with col3:
                        if st.button("🗑️ Supprimer", key=f"delete_{portfolio.id}", type="secondary"):
                            pm.delete_portfolio(portfolio.id)
                            st.success(f"Portefeuille '{portfolio.name}' supprimé")
                            st.rerun()
        else:
            st.info("Aucun portefeuille créé")

        st.divider()

        # Import
        st.subheader("📤 Importer un Portefeuille")
        uploaded_file = st.file_uploader("Fichier JSON", type=['json'])
        if uploaded_file:
            if st.button("Importer"):
                try:
                    json_data = uploaded_file.read().decode('utf-8')
                    pm.import_portfolio_from_json(json_data)
                    st.success("Portefeuille importé avec succès!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur d'import: {e}")

    # ==================== TAB: AJOUTER POSITION ====================
    with tab_add_position:
        portfolios = pm.get_all_portfolios()

        if not portfolios:
            st.warning("Créez d'abord un portefeuille dans l'onglet 'Gérer'")
        else:
            st.subheader("🛒 Acheter une Action")

            col1, col2 = st.columns(2)

            with col1:
                portfolio_names = {p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios}
                selected_portfolio = st.selectbox(
                    "Portefeuille",
                    options=list(portfolio_names.keys()),
                    format_func=lambda x: portfolio_names[x],
                    key="buy_portfolio"
                )

                buy_ticker = st.text_input("Ticker", placeholder="Ex: AAPL, MC.PA", key="buy_ticker_new").upper()

                if buy_ticker:
                    score_data = calculate_full_score(buy_ticker)
                    if score_data:
                        st.success(f"✅ {score_data['name']} - Prix: {score_data['price']:.2f} {score_data['currency']}")
                        st.write(f"Score: {score_data['scores']['global']:.0f}/100 - {score_data['recommendation']}")

            with col2:
                buy_quantity = st.number_input("Quantité", min_value=0.0, value=1.0, step=1.0)
                buy_price = st.number_input("Prix unitaire (€)", min_value=0.0, value=0.0, step=0.01)
                buy_fees = st.number_input("Frais de courtage (€)", min_value=0.0, value=0.0, step=0.50)
                buy_date = st.date_input("Date d'achat", value=datetime.now())

            # Auto-fill price
            if buy_ticker and buy_price == 0:
                score_data = calculate_full_score(buy_ticker)
                if score_data:
                    buy_price = score_data['price']

            if buy_quantity > 0 and buy_price > 0:
                total_cost = buy_quantity * buy_price + buy_fees
                st.info(f"💵 Coût total: {total_cost:,.2f} €")

            if st.button("🛒 Acheter", type="primary", key="btn_buy"):
                if buy_ticker and buy_quantity > 0 and buy_price > 0:
                    try:
                        position, transaction = pm.add_position(
                            portfolio_id=selected_portfolio,
                            ticker=buy_ticker,
                            quantity=buy_quantity,
                            price=buy_price,
                            fees=buy_fees,
                            transaction_date=datetime.combine(buy_date, datetime.min.time())
                        )
                        st.success(f"✅ Acheté {buy_quantity}x {buy_ticker} @ {buy_price:.2f}€")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
                else:
                    st.error("Veuillez remplir tous les champs")

            st.divider()

            # Vendre une position
            st.subheader("📤 Vendre une Position")

            if selected_portfolio:
                positions = pm.get_positions(selected_portfolio)

                if positions:
                    position_options = {p.id: f"{p.ticker} ({p.quantity} actions)" for p in positions if p.quantity > 0}

                    if position_options:
                        col1, col2 = st.columns(2)

                        with col1:
                            sell_position_id = st.selectbox(
                                "Position à vendre",
                                options=list(position_options.keys()),
                                format_func=lambda x: position_options[x],
                                key="sell_position"
                            )

                            # Trouver la position sélectionnée
                            sell_position = next((p for p in positions if p.id == sell_position_id), None)

                            if sell_position:
                                current_price = pm.get_current_price(sell_position.ticker)
                                st.write(f"PRU: {sell_position.average_cost:.2f}€ | Prix actuel: {current_price:.2f}€" if current_price else f"PRU: {sell_position.average_cost:.2f}€")

                        with col2:
                            max_qty = sell_position.quantity if sell_position else 1
                            sell_quantity = st.number_input("Quantité à vendre", min_value=0.0, max_value=float(max_qty), value=float(max_qty))
                            sell_price = st.number_input("Prix de vente (€)", min_value=0.0, value=current_price if current_price else 0.0, step=0.01)
                            sell_fees = st.number_input("Frais de vente (€)", min_value=0.0, value=0.0, step=0.50, key="sell_fees")

                        if sell_quantity > 0 and sell_price > 0:
                            sell_total = sell_quantity * sell_price - sell_fees
                            gain = sell_total - (sell_quantity * (sell_position.average_cost or 0))
                            st.info(f"💵 Montant net: {sell_total:,.2f} € | Gain: {gain:+,.2f}€")

                        if st.button("📤 Vendre", type="secondary", key="btn_sell"):
                            if sell_position and sell_quantity > 0 and sell_price > 0:
                                try:
                                    pm.sell_position(
                                        portfolio_id=selected_portfolio,
                                        ticker=sell_position.ticker,
                                        quantity=sell_quantity,
                                        price=sell_price,
                                        fees=sell_fees
                                    )
                                    st.success(f"✅ Vendu {sell_quantity}x {sell_position.ticker} @ {sell_price:.2f}€")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")
                    else:
                        st.info("Aucune position dans ce portefeuille")
                else:
                    st.info("Aucune position dans ce portefeuille")

    # ==================== TAB: DIVIDENDES ====================
    with tab_dividends:
        portfolios = pm.get_all_portfolios()
        dividend_tracker = services["dividend_tracker"]

        if not portfolios:
            st.warning("Créez d'abord un portefeuille")
        else:
            portfolio_names = {p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios}
            div_portfolio = st.selectbox(
                "Sélectionner un portefeuille",
                options=list(portfolio_names.keys()),
                format_func=lambda x: portfolio_names[x],
                key="div_portfolio"
            )

            if div_portfolio:
                positions = pm.get_positions(div_portfolio)

                if positions:
                    # Préparer les données pour le tracker
                    position_data = [
                        {'ticker': p.ticker, 'quantity': p.quantity, 'name': p.name or p.ticker}
                        for p in positions if p.quantity > 0
                    ]

                    # ===== DIVIDENDES À VENIR =====
                    st.subheader("📅 Dividendes à Venir (90 jours)")

                    with st.spinner("Récupération des dates de dividendes..."):
                        upcoming = dividend_tracker.get_upcoming_dividends(position_data, days_ahead=90)

                    if upcoming:
                        upcoming_data = []
                        for div in upcoming:
                            urgency = "🔴" if div.days_until_ex <= 7 else "🟡" if div.days_until_ex <= 30 else "🟢"
                            upcoming_data.append({
                                '': urgency,
                                'Ticker': div.ticker,
                                'Nom': div.name[:20],
                                'Date Ex-Div': div.ex_date.strftime('%Y-%m-%d'),
                                'Dans': f"{div.days_until_ex}j",
                                'Actions': int(div.shares_held),
                                '/Action': f"{div.amount_per_share:.2f}",
                                'Attendu': f"{div.expected_amount:.2f}€"
                            })

                        df_upcoming = pd.DataFrame(upcoming_data)
                        st.dataframe(df_upcoming, use_container_width=True, hide_index=True)

                        total_upcoming = sum(d.expected_amount for d in upcoming)
                        st.success(f"💰 Total attendu sur 90 jours: **{total_upcoming:.2f}€**")
                    else:
                        st.info("Aucun dividende prévu dans les 90 prochains jours")

                    st.divider()

                    # ===== RENDEMENT PAR POSITION =====
                    st.subheader("📊 Rendement Dividende par Position")

                    yield_data = []
                    for pos in positions:
                        if pos.quantity <= 0:
                            continue
                        info = dividend_tracker.get_dividend_info(pos.ticker)
                        if info:
                            annual_div = info.amount * pos.quantity
                            yield_data.append({
                                'Ticker': pos.ticker,
                                'Nom': (info.name or pos.ticker)[:20],
                                'Rendement': f"{info.dividend_yield:.2f}%",
                                'Div/Action': f"{info.amount:.2f} {info.currency}",
                                'Fréquence': info.frequency.capitalize(),
                                'Actions': int(pos.quantity),
                                'Div Annuel': f"{annual_div:.2f}€"
                            })

                    if yield_data:
                        # Trier par rendement décroissant
                        yield_data.sort(key=lambda x: float(x['Rendement'].replace('%', '')), reverse=True)
                        df_yield = pd.DataFrame(yield_data)
                        st.dataframe(df_yield, use_container_width=True, hide_index=True)

                    st.divider()

                    # ===== ESTIMATION ANNUELLE =====
                    st.subheader("💵 Estimation Annuelle")

                    with st.spinner("Calcul des estimations..."):
                        estimate = dividend_tracker.get_annual_dividend_estimate(position_data)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Annuel Estimé", f"{estimate['total_annual']:.2f}€")
                    with col2:
                        st.metric("Moyenne Mensuelle", f"{estimate['monthly_average']:.2f}€")
                    with col3:
                        # Rendement global du portefeuille
                        summary = pm.get_portfolio_summary(div_portfolio)
                        if summary and summary.current_value > 0:
                            portfolio_yield = (estimate['total_annual'] / summary.current_value) * 100
                            st.metric("Rendement Portefeuille", f"{portfolio_yield:.2f}%")

                    # Graphique mensuel estimé
                    months = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
                    monthly_values = [estimate['by_month'].get(i, 0) for i in range(1, 13)]

                    fig = go.Figure(data=[
                        go.Bar(x=months, y=monthly_values, marker_color='#28a745')
                    ])
                    fig.update_layout(
                        title="Dividendes Estimés par Mois",
                        xaxis_title="Mois",
                        yaxis_title="Montant (€)",
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.divider()

                    # ===== CALENDRIER DÉTAILLÉ =====
                    st.subheader("📆 Calendrier Détaillé")

                    with st.spinner("Génération du calendrier..."):
                        calendar = dividend_tracker.get_dividend_calendar(position_data, year=datetime.now().year)

                    # Afficher par mois
                    selected_month = st.selectbox(
                        "Voir un mois",
                        options=list(range(1, 13)),
                        format_func=lambda x: months[x-1],
                        index=datetime.now().month - 1
                    )

                    month_key = str(selected_month).zfill(2)
                    month_divs = calendar.get(month_key, [])

                    if month_divs:
                        month_data = []
                        for d in month_divs:
                            month_data.append({
                                'Ticker': d['ticker'],
                                'Nom': d['name'][:20],
                                '/Action': f"{d['amount_per_share']:.2f}€",
                                'Actions': int(d['quantity']),
                                'Montant': f"{d['expected_amount']:.2f}€",
                                'Rendement': f"{d['yield']:.1f}%"
                            })
                        df_month = pd.DataFrame(month_data)
                        st.dataframe(df_month, use_container_width=True, hide_index=True)

                        month_total = sum(d['expected_amount'] for d in month_divs)
                        st.info(f"Total {months[selected_month-1]}: **{month_total:.2f}€**")
                    else:
                        st.info(f"Aucun dividende prévu en {months[selected_month-1]}")

                    st.divider()

                    # ===== ENREGISTRER UN DIVIDENDE REÇU =====
                    st.subheader("✏️ Enregistrer un Dividende Reçu")

                    with st.expander("Ajouter un dividende manuellement"):
                        col1, col2 = st.columns(2)

                        with col1:
                            position_options = {p.id: f"{p.ticker} ({p.quantity} actions)" for p in positions}
                            div_position = st.selectbox(
                                "Position",
                                options=list(position_options.keys()),
                                format_func=lambda x: position_options[x],
                                key="div_position"
                            )

                            div_gross = st.number_input("Montant brut (€)", min_value=0.0, step=0.01)
                            div_tax = st.number_input("Retenue à la source (€)", min_value=0.0, step=0.01)

                        with col2:
                            div_date = st.date_input("Date de paiement", value=datetime.now())
                            div_type = st.selectbox("Type", ["regular", "special", "return_of_capital"])
                            div_drip = st.checkbox("Réinvestissement automatique (DRIP)")

                        if div_gross > 0:
                            st.info(f"💵 Montant net: {div_gross - div_tax:.2f}€")

                        if st.button("💰 Enregistrer le dividende", type="primary"):
                            if div_gross > 0:
                                try:
                                    pm.add_dividend(
                                        position_id=div_position,
                                        gross_amount=div_gross,
                                        tax_withheld=div_tax,
                                        payment_date=datetime.combine(div_date, datetime.min.time()),
                                        dividend_type=div_type,
                                        is_drip=div_drip
                                    )
                                    st.success("Dividende enregistré!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erreur: {e}")

                    # ===== HISTORIQUE DES DIVIDENDES REÇUS =====
                    st.subheader("📜 Historique des Dividendes Reçus")

                    received_dividends = pm.get_dividends(portfolio_id=div_portfolio)
                    if received_dividends:
                        hist_data = []
                        for d in received_dividends[:20]:
                            hist_data.append({
                                'Date': d.payment_date.strftime('%Y-%m-%d'),
                                'Ticker': d.ticker,
                                'Brut': f"{d.gross_amount:.2f}€",
                                'Retenue': f"{d.tax_withheld:.2f}€",
                                'Net': f"{d.net_amount:.2f}€",
                                'Type': d.dividend_type or 'regular'
                            })
                        df_hist = pd.DataFrame(hist_data)
                        st.dataframe(df_hist, use_container_width=True, hide_index=True)

                        total_received = sum(d.net_amount or 0 for d in received_dividends)
                        st.metric("Total reçu", f"{total_received:.2f}€")
                    else:
                        st.info("Aucun dividende enregistré")
                else:
                    st.info("Aucune position dans ce portefeuille")

    # ==================== TAB: TRANSACTIONS ====================
    with tab_transactions:
        portfolios = pm.get_all_portfolios()

        if not portfolios:
            st.warning("Créez d'abord un portefeuille")
        else:
            st.subheader("📜 Historique des Transactions")

            portfolio_names = {0: "Tous les portefeuilles"}
            portfolio_names.update({p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios})

            trans_portfolio = st.selectbox(
                "Filtrer par portefeuille",
                options=list(portfolio_names.keys()),
                format_func=lambda x: portfolio_names[x],
                key="trans_portfolio"
            )

            col1, col2 = st.columns(2)
            with col1:
                trans_type = st.selectbox("Type", ["Tous", "buy", "sell"])
            with col2:
                trans_limit = st.slider("Nombre max", 10, 200, 50)

            transactions = pm.get_transactions(
                portfolio_id=trans_portfolio if trans_portfolio > 0 else None,
                transaction_type=trans_type if trans_type != "Tous" else None,
                limit=trans_limit
            )

            if transactions:
                trans_data = []
                for t in transactions:
                    trans_data.append({
                        'Date': t.transaction_date.strftime('%Y-%m-%d'),
                        'Type': '🟢 ACHAT' if t.transaction_type == 'buy' else '🔴 VENTE',
                        'Ticker': t.ticker,
                        'Quantité': t.quantity,
                        'Prix': f"{t.price:.2f}€",
                        'Frais': f"{t.fees:.2f}€" if t.fees else "0€",
                        'Total': f"{t.total_amount:.2f}€"
                    })

                df = pd.DataFrame(trans_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune transaction")


def display_portfolio_details(pm: PortfolioManager, portfolio_id: int):
    """Affiche les détails d'un portefeuille."""
    details = pm.get_position_details(portfolio_id)

    if not details:
        st.info("Aucune position dans ce portefeuille")
        return

    # Tableau des positions
    st.write("### 📊 Positions")

    positions_data = []
    for d in details:
        positions_data.append({
            'Ticker': d.ticker,
            'Nom': d.name[:20] if d.name else d.ticker,
            'Qté': d.quantity,
            'PRU': f"{d.average_cost:.2f}€",
            'Prix': f"{d.current_price:.2f}€",
            'Valeur': f"{d.current_value:,.2f}€",
            '+/-': f"{d.gain:+,.2f}€",
            '%': f"{d.gain_pct:+.1f}%",
            'Poids': f"{d.weight:.1f}%",
            'Secteur': d.sector or "N/A"
        })

    df = pd.DataFrame(positions_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Graphiques de répartition
    col1, col2 = st.columns(2)

    with col1:
        st.write("### 🏭 Répartition Sectorielle")
        sector_data = pm.get_allocation_by_sector(portfolio_id)
        if sector_data:
            fig = px.pie(
                values=list(sector_data.values()),
                names=list(sector_data.keys()),
                hole=0.4
            )
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("### 🌍 Répartition Géographique")
        country_data = pm.get_allocation_by_country(portfolio_id)
        if country_data:
            fig = px.pie(
                values=list(country_data.values()),
                names=list(country_data.keys()),
                hole=0.4
            )
            fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# PAGE: ANALYSE DÉTAILLÉE
# ============================================================================
def analyze_stock_detailed(ticker: str):
    """Analyse détaillée d'une action."""
    st.divider()
    st.subheader(f"📊 Analyse de {ticker}")

    with st.spinner(f"Analyse en cours..."):
        score_data = calculate_full_score(ticker)

    if not score_data:
        st.error(f"Impossible d'analyser {ticker}")
        return

    # Header
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"### {score_data['name']}")
        st.write(f"**Secteur:** {score_data['sector']}")
        pea_badge = "🇪🇺 Eligible PEA" if score_data['pea_eligible'] else "🌍 CTO uniquement"
        st.write(pea_badge)
        # Indicateur Etat francais
        state_info = score_data.get('french_state')
        if state_info:
            if state_info['pct'] > 0:
                st.markdown(f"""<div style="background: linear-gradient(90deg, #002395 33%, #FFFFFF 33%, #FFFFFF 66%, #ED2939 66%);
                    padding: 8px 15px; border-radius: 8px; margin-top: 5px; display: inline-block;">
                    <span style="color: #002395; font-weight: bold; background: rgba(255,255,255,0.9); padding: 2px 8px; border-radius: 4px;">
                    🏛 Etat francais : {state_info['pct']:.1f}% — {state_info['type']}</span></div>""",
                    unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="background: #f0f0f0; padding: 8px 15px; border-radius: 8px;
                    margin-top: 5px; display: inline-block;">
                    <span style="font-weight: bold;">🏛 {state_info['type']}</span></div>""",
                    unsafe_allow_html=True)

    with col2:
        st.metric("Prix actuel", f"{score_data['price']:.2f} {score_data['currency']}")

    with col3:
        st.markdown(f"""
        <div style="background-color: {score_data['rec_color']}; padding: 15px;
                    border-radius: 10px; text-align: center;">
            <h3 style="margin: 0;">{score_data['recommendation']}</h3>
            <h2 style="margin: 0;">{score_data['scores']['global']:.0f}/100</h2>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Scores
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.plotly_chart(create_gauge_chart(score_data['scores']['technical'], "Technique"), use_container_width=True)
    with col2:
        st.plotly_chart(create_gauge_chart(score_data['scores']['fundamental'], "Fondamental"), use_container_width=True)
    with col3:
        st.plotly_chart(create_gauge_chart(score_data['scores']['sentiment'], "Sentiment"), use_container_width=True)
    with col4:
        st.plotly_chart(create_gauge_chart(score_data['scores']['smart_money'], "Smart Money"), use_container_width=True)

    # Détails des scores
    st.subheader("📋 Détails de l'Analyse")

    tab1, tab2, tab3, tab4 = st.tabs(["📈 Technique", "💰 Fondamental", "😊 Sentiment", "🎯 Smart Money"])

    with tab1:
        for detail in score_data['details']['technical']:
            st.write(f"• {detail}")

    with tab2:
        for detail in score_data['details']['fundamental']:
            st.write(f"• {detail}")

    with tab3:
        for detail in score_data['details']['sentiment']:
            st.write(f"• {detail}")

    with tab4:
        for detail in score_data['details']['smart_money']:
            st.write(f"• {detail}")

    # Graphique prix
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1y")
        if not hist.empty:
            st.plotly_chart(create_price_chart(hist, ticker), use_container_width=True)
    except:
        pass

    # Actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🛒 Acheter cette action"):
            st.session_state.buy_ticker_prefill = ticker
            st.info("Allez dans l'onglet Portefeuille pour finaliser l'achat")
    with col2:
        if ticker not in st.session_state.watchlist:
            if st.button("⭐ Ajouter à la watchlist"):
                st.session_state.watchlist.append(ticker)
                st.success(f"{ticker} ajouté à la watchlist")
        else:
            if st.button("❌ Retirer de la watchlist"):
                st.session_state.watchlist.remove(ticker)
                st.success(f"{ticker} retiré de la watchlist")

# ============================================================================
# PAGE: FILTRES
# ============================================================================
def page_filters():
    """Page de configuration des filtres."""
    st.title("🔧 Configuration des Filtres")

    st.write("Personnalisez vos critères de sélection d'actions.")

    # Filtres éthiques
    st.subheader("🌿 Filtres Éthiques")

    col1, col2 = st.columns(2)
    with col1:
        exclude_tobacco = st.checkbox("Exclure Tabac", value=True)
        exclude_weapons = st.checkbox("Exclure Armement", value=True)
    with col2:
        exclude_gambling = st.checkbox("Exclure Jeux d'argent", value=True)
        exclude_fossil = st.checkbox("Exclure Énergies fossiles", value=False)

    st.divider()

    # Filtres fondamentaux
    st.subheader("💰 Filtres Fondamentaux")

    col1, col2, col3 = st.columns(3)

    with col1:
        max_pe = st.slider("P/E Maximum", 0, 100, 50)
        min_roe = st.slider("ROE Minimum (%)", 0, 50, 10)

    with col2:
        max_debt = st.slider("Dette/Equity Maximum", 0.0, 5.0, 2.0, 0.1)
        min_dividend = st.slider("Dividende Minimum (%)", 0.0, 10.0, 0.0, 0.1)

    with col3:
        min_score = st.slider("Score Global Minimum", 0, 100, 55)
        pea_only = st.checkbox("PEA uniquement", value=False)

    if st.button("💾 Sauvegarder", type="primary"):
        st.session_state.filters = {
            'exclude_tobacco': exclude_tobacco,
            'exclude_weapons': exclude_weapons,
            'exclude_gambling': exclude_gambling,
            'exclude_fossil': exclude_fossil,
            'max_pe': max_pe,
            'min_roe': min_roe,
            'max_debt': max_debt,
            'min_dividend': min_dividend,
            'min_score': min_score,
            'pea_only': pea_only
        }
        st.success("Filtres sauvegardés!")

# ============================================================================
# PAGE: HARDWARE
# ============================================================================
def page_hardware():
    """Page de configuration hardware/LLM."""
    st.title("🖥️ Configuration Hardware")

    detector = services["hardware_detector"]

    with st.spinner("Détection du hardware..."):
        system_info = detector.detect_system()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("💻 Système")
        st.write(f"**OS:** {system_info.os}")
        st.write(f"**CPU:** {system_info.cpu_name}")
        st.write(f"**Cœurs:** {system_info.cpu_cores}")
        st.write(f"**RAM:** {system_info.ram_gb:.1f} GB")

    with col2:
        st.subheader("🎮 GPU")
        if system_info.gpu:
            st.write(f"**GPU:** {system_info.gpu.name}")
            st.write(f"**Type:** {system_info.gpu.gpu_type.value.upper()}")
            st.write(f"**VRAM:** {system_info.gpu.vram_gb:.1f} GB")
        else:
            st.warning("Aucun GPU détecté")

    st.divider()

    st.subheader("🤖 Recommandation LLM")

    recommendation = detector.recommend_llm(system_info)

    st.info(f"""
    **Modèle recommandé:** {recommendation.model_name}

    - **Taille:** {recommendation.model_size}
    - **Quantification:** {recommendation.quantization}

    {recommendation.reason}
    """)

    st.code(recommendation.ollama_command, language="bash")

# ============================================================================
# PAGE: PROJECTIONS & FIRE
# ============================================================================
def page_projections():
    """Page Projections - Monte Carlo, FIRE, Dividendes long terme."""
    st.title("📊 Projections & Simulateurs")

    engine = services["projection_engine"]
    pm = services["portfolio_manager"]

    tab_monte_carlo, tab_fire, tab_dividends = st.tabs([
        "🎲 Monte Carlo", "🔥 Calculateur FIRE", "💰 Projection Dividendes"
    ])

    # ===== TAB MONTE CARLO =====
    with tab_monte_carlo:
        st.subheader("🎲 Simulation Monte Carlo (5000 scénarios)")
        st.caption("Projette l'évolution de votre patrimoine avec différents scénarios")

        col1, col2 = st.columns(2)
        with col1:
            initial_capital = st.number_input("Capital initial (€)", min_value=0, value=10000, step=1000)
            monthly_contrib = st.number_input("Versement mensuel (€)", min_value=0, value=500, step=50)
            years = st.slider("Durée (années)", 5, 40, 20)
        with col2:
            risk_profile = st.selectbox("Profil de risque", [
                "Conservateur (4%/an, vol 8%)",
                "Modéré (6%/an, vol 12%)",
                "Dynamique (8%/an, vol 18%)",
                "Agressif (10%/an, vol 25%)"
            ], index=1)

            profile_map = {
                "Conservateur": RiskProfile.CONSERVATEUR,
                "Modéré": RiskProfile.MODERE,
                "Dynamique": RiskProfile.DYNAMIQUE,
                "Agressif": RiskProfile.AGRESSIF
            }
            selected_profile = profile_map.get(risk_profile.split()[0], RiskProfile.MODERE)

        if st.button("🚀 Lancer la simulation", type="primary"):
            with st.spinner("Simulation en cours (5000 scénarios)..."):
                result = engine.monte_carlo_simulation(
                    initial_capital=initial_capital,
                    monthly_contribution=monthly_contrib,
                    years=years,
                    risk_profile=selected_profile
                )

            # Résultats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Scénario Médian", f"{result.final_median:,.0f}€")
            with col2:
                st.metric("Optimiste (95%)", f"{result.final_optimistic:,.0f}€")
            with col3:
                st.metric("Pessimiste (5%)", f"{result.final_pessimistic:,.0f}€")
            with col4:
                total_invested = initial_capital + monthly_contrib * years * 12
                st.metric("Total Investi", f"{total_invested:,.0f}€")

            # Graphique
            months = list(range(len(result.median_trajectory)))
            years_labels = [m/12 for m in months]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=years_labels, y=result.optimistic_trajectory,
                fill=None, mode='lines', name='Optimiste (95%)',
                line=dict(color='rgba(0,200,0,0.3)')
            ))
            fig.add_trace(go.Scatter(
                x=years_labels, y=result.pessimistic_trajectory,
                fill='tonexty', mode='lines', name='Pessimiste (5%)',
                line=dict(color='rgba(200,0,0,0.3)')
            ))
            fig.add_trace(go.Scatter(
                x=years_labels, y=result.median_trajectory,
                mode='lines', name='Médian (50%)',
                line=dict(color='blue', width=3)
            ))

            fig.update_layout(
                title=f"Projection sur {years} ans - {result.num_simulations} simulations",
                xaxis_title="Années",
                yaxis_title="Valeur (€)",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Stats
            st.info(f"📊 Probabilité de doubler votre investissement: **{result.probability_of_success:.1f}%** | Max Drawdown moyen: **-{result.max_drawdown:.1f}%**")

    # ===== TAB FIRE =====
    with tab_fire:
        st.subheader("🔥 Calculateur d'Indépendance Financière (FIRE)")
        st.caption("Quand pourrez-vous vivre de vos investissements?")

        col1, col2 = st.columns(2)
        with col1:
            current_age = st.number_input("Votre âge actuel", min_value=18, max_value=80, value=30)

            # Récupérer la valeur du portefeuille si disponible
            global_summary = pm.get_all_portfolios_summary()
            default_portfolio = int(global_summary.get('total_value', 50000))

            current_portfolio = st.number_input("Portefeuille actuel (€)", min_value=0, value=default_portfolio, step=5000)
            monthly_savings = st.number_input("Épargne mensuelle (€)", min_value=0, value=1000, step=100)

        with col2:
            monthly_expenses = st.number_input("Dépenses mensuelles souhaitées (€)", min_value=500, value=3000, step=100)
            expected_return = st.slider("Rendement annuel attendu (%)", 3.0, 12.0, 7.0, 0.5) / 100
            swr = st.slider("Taux de retrait sûr (%)", 2.0, 5.0, 4.0, 0.5) / 100

        if st.button("📈 Calculer FIRE", type="primary"):
            fire = engine.calculate_fire(
                current_age=current_age,
                current_portfolio=current_portfolio,
                monthly_contribution=monthly_savings,
                monthly_expenses=monthly_expenses,
                expected_return=expected_return,
                safe_withdrawal_rate=swr
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 FIRE Number", f"{fire.fire_number:,.0f}€", help="Capital nécessaire pour l'indépendance financière")
            with col2:
                st.metric("📅 Âge FIRE", f"{fire.fire_age} ans", delta=f"dans {fire.years_to_fire} ans")
            with col3:
                st.metric("📊 Progrès", f"{fire.current_progress:.1f}%")

            # Barre de progression
            st.progress(min(fire.current_progress / 100, 1.0))

            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"🟢 Scénario optimiste: **{fire.optimistic_age} ans**")
            with col2:
                st.warning(f"🟡 Scénario médian: **{fire.fire_age} ans**")
            with col3:
                st.error(f"🔴 Scénario pessimiste: **{fire.pessimistic_age} ans**")

            st.success(f"💰 Revenu passif mensuel à FIRE: **{fire.monthly_passive_income:,.0f}€**")

            for a in fire.analysis:
                st.write(f"• {a}")

    # ===== TAB DIVIDENDES =====
    with tab_dividends:
        st.subheader("💰 Projection Dividendes sur 40 ans")
        st.caption("Estimez vos revenus passifs futurs")

        col1, col2 = st.columns(2)
        with col1:
            div_initial = st.number_input("Capital initial (€)", min_value=0, value=10000, step=1000, key="div_init")
            div_monthly = st.number_input("Versement mensuel (€)", min_value=0, value=200, step=50, key="div_month")
        with col2:
            div_yield = st.slider("Rendement dividende initial (%)", 1.0, 8.0, 3.0, 0.5) / 100
            div_growth = st.slider("Croissance dividende (%/an)", 0.0, 10.0, 5.0, 0.5) / 100

        if st.button("📊 Projeter", type="primary", key="project_div"):
            proj = engine.project_dividends(
                initial_capital=div_initial,
                monthly_contribution=div_monthly,
                years=40,
                initial_yield=div_yield,
                dividend_growth=div_growth
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Valeur à 40 ans", f"{proj.portfolio_value[-1]:,.0f}€")
            with col2:
                st.metric("Dividende annuel", f"{proj.final_annual_dividend:,.0f}€")
            with col3:
                st.metric("Revenu mensuel", f"{proj.final_monthly_income:,.0f}€")

            # Graphique
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=proj.years, y=proj.portfolio_value, name='Valeur portefeuille', fill='tozeroy'))
            fig.add_trace(go.Scatter(x=proj.years, y=proj.cumulative_dividends, name='Dividendes cumulés'))
            fig.update_layout(title="Projection sur 40 ans", xaxis_title="Années", yaxis_title="€", height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Tableau des jalons
            milestones = [5, 10, 15, 20, 25, 30, 35, 40]
            data = []
            for y in milestones:
                if y < len(proj.years):
                    data.append({
                        'Année': y,
                        'Valeur': f"{proj.portfolio_value[y]:,.0f}€",
                        'Div/an': f"{proj.annual_dividends[y]:,.0f}€",
                        'Div/mois': f"{proj.annual_dividends[y]/12:,.0f}€",
                        'YoC': f"{proj.yield_on_cost[y]:.1f}%"
                    })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


# ============================================================================
# PAGE: ETF SCREENER
# ============================================================================
def page_etf():
    """Page ETF - Screener et Comparateur."""
    st.title("📈 ETF Screener & Comparateur")

    analyzer = services["etf_analyzer"]

    tab_screener, tab_compare, tab_fees = st.tabs([
        "🔍 Screener", "⚖️ Comparateur", "💸 Analyse Frais"
    ])

    # ===== TAB SCREENER =====
    with tab_screener:
        st.subheader("🔍 Rechercher des ETF")

        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox("Catégorie", ["Tous", "WORLD", "SP500", "NASDAQ", "EUROPE", "EMERGING", "DIVIDENDS", "BONDS"])
        with col2:
            max_ter = st.slider("TER Maximum (%)", 0.0, 1.0, 0.5, 0.05)
        with col3:
            pea_only = st.checkbox("PEA uniquement")

        if st.button("🔍 Rechercher", type="primary"):
            with st.spinner("Recherche en cours..."):
                etfs = analyzer.get_etf_screener(
                    category=category if category != "Tous" else None,
                    max_ter=max_ter,
                    pea_only=pea_only
                )

            if etfs:
                data = []
                for etf in etfs:
                    data.append({
                        'Ticker': etf.ticker,
                        'Nom': etf.name[:30],
                        'Catégorie': etf.category,
                        'TER': f"{etf.expense_ratio:.2f}%",
                        'Perf 1Y': f"{etf.perf_1y:+.1f}%",
                        'Perf 5Y': f"{etf.perf_5y:+.1f}%/an" if etf.perf_5y else "N/A",
                        'AUM (M)': f"{etf.aum:,.0f}",
                        'Div': f"{etf.dividend_yield:.2f}%",
                        'PEA': "✅" if etf.pea_eligible else "❌"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
            else:
                st.warning("Aucun ETF trouvé avec ces critères")

    # ===== TAB COMPARATEUR =====
    with tab_compare:
        st.subheader("⚖️ Comparer des ETF")

        # Suggestions par catégorie
        suggestions = {
            "S&P 500": "SPY, VOO, IVV",
            "World": "IWDA.AS, VWCE.DE, CW8.PA",
            "NASDAQ": "QQQ, EQQQ.DE",
        }
        st.caption(f"Exemples: {suggestions.get('S&P 500')}")

        tickers_input = st.text_input("Entrez les tickers (séparés par des virgules)", "SPY, VOO, IVV")
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

        if st.button("⚖️ Comparer", type="primary") and len(tickers) >= 2:
            with st.spinner("Comparaison en cours..."):
                comparison = analyzer.compare_etfs(tickers)

            if comparison:
                # Tableau
                data = []
                for etf in comparison.etfs:
                    data.append({
                        'Ticker': etf.ticker,
                        'Nom': etf.name[:25],
                        'TER': f"{etf.expense_ratio:.2f}%",
                        'Perf 1Y': f"{etf.perf_1y:+.1f}%",
                        'Perf 5Y/an': f"{etf.perf_5y:+.1f}%" if etf.perf_5y else "N/A",
                        'AUM': f"{etf.aum:,.0f}M",
                        'Dividende': f"{etf.dividend_yield:.2f}%"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

                # Recommandation
                st.success(f"🏆 **Recommandation: {comparison.recommendation}**")
                for a in comparison.analysis:
                    st.write(f"• {a}")

                # Graphique comparatif
                fig = go.Figure()
                for etf in comparison.etfs:
                    fig.add_trace(go.Bar(name=etf.ticker, x=['TER', 'Perf 1Y', 'Div Yield'],
                                        y=[etf.expense_ratio, etf.perf_1y, etf.dividend_yield]))
                fig.update_layout(barmode='group', title="Comparaison", height=300)
                st.plotly_chart(fig, use_container_width=True)

    # ===== TAB FEES =====
    with tab_fees:
        st.subheader("💸 Analyse des Frais de votre Portefeuille")

        pm = services["portfolio_manager"]
        portfolios = pm.get_all_portfolios()

        if portfolios:
            portfolio_names = {p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios}
            selected = st.selectbox("Portefeuille à analyser", list(portfolio_names.keys()),
                                   format_func=lambda x: portfolio_names[x])

            if st.button("💸 Analyser les frais", type="primary"):
                positions = pm.get_positions(selected)
                pos_data = []
                for p in positions:
                    price = pm.get_current_price(p.ticker)
                    value = p.quantity * price if price else 0
                    pos_data.append({'ticker': p.ticker, 'value': value})

                if pos_data:
                    fees = analyzer.analyze_portfolio_fees(pos_data)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("TER moyen pondéré", f"{fees.weighted_ter:.2f}%")
                    with col2:
                        st.metric("Frais annuels", f"{fees.annual_fees:,.0f}€")
                    with col3:
                        st.metric("Frais sur 20 ans", f"{fees.fees_over_20y:,.0f}€")

                    if fees.alternatives:
                        st.warning("💡 **Alternatives moins chères disponibles:**")
                        for alt in fees.alternatives:
                            st.write(f"• {alt['current']} ({alt['current_ter']:.2f}%) → **{alt['alternative']}** ({alt['alternative_ter']:.2f}%) = -{alt['annual_savings']:.0f}€/an")
                        st.success(f"Économies potentielles sur 20 ans: **{fees.potential_savings_20y:,.0f}€**")
        else:
            st.info("Créez d'abord un portefeuille pour analyser les frais")


# ============================================================================
# PAGE: ANALYSE IA
# ============================================================================
def page_ai_analysis():
    """Page Analyse IA du portefeuille."""
    st.title("🤖 Analyse IA du Portefeuille")

    advisor = services["ai_advisor"]
    pm = services["portfolio_manager"]
    moning = services["moning_scorer"]

    portfolios = pm.get_all_portfolios()

    if not portfolios:
        st.warning("Créez d'abord un portefeuille pour l'analyser")
        return

    portfolio_names = {p.id: f"{p.name} ({p.portfolio_type})" for p in portfolios}
    selected = st.selectbox("Portefeuille à analyser", list(portfolio_names.keys()),
                           format_func=lambda x: portfolio_names[x])

    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("🤖 Lancer l'analyse IA", type="primary"):
            with st.spinner("Analyse en cours... (peut prendre quelques secondes)"):
                # Récupérer les données du portefeuille
                summary = pm.get_portfolio_summary(selected)
                details = pm.get_position_details(selected)
                sector_alloc = pm.get_allocation_by_sector(selected)
                country_alloc = pm.get_allocation_by_country(selected)

                # Préparer les données pour l'IA
                positions_data = []
                for d in details:
                    score_data = calculate_full_score(d.ticker)
                    score = score_data['scores']['global'] if score_data else 50
                    positions_data.append({
                        'ticker': d.ticker,
                        'name': d.name,
                        'value': d.current_value,
                        'weight': d.weight,
                        'gain_pct': d.gain_pct,
                        'sector': d.sector,
                        'score': score
                    })

                # Calculer le score de diversification
                div_engine = services["projection_engine"]
                div_score = div_engine.calculate_diversification_score([
                    {'ticker': p['ticker'], 'value': p['value'], 'sector': p['sector'], 'country': ''}
                    for p in positions_data
                ])

                portfolio_data = {
                    'total_value': summary.current_value if summary else 0,
                    'total_gain': summary.total_gain if summary else 0,
                    'gain_pct': summary.total_gain_pct if summary else 0,
                    'diversification_score': div_score.total_score,
                    'positions': positions_data,
                    'sector_allocation': {s: v/summary.current_value*100 for s, v in sector_alloc.items()} if summary and summary.current_value > 0 else {},
                    'country_allocation': {c: v/summary.current_value*100 for c, v in country_alloc.items()} if summary and summary.current_value > 0 else {}
                }

                # Lancer l'analyse
                result = advisor.analyze_portfolio(portfolio_data)

            # Afficher les résultats
            st.markdown("---")
            st.subheader("📊 Résumé")
            st.info(result.summary)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("✅ Points Forts")
                for s in result.strengths:
                    st.success(f"• {s}")

            with col2:
                st.subheader("⚠️ Points Faibles")
                for w in result.weaknesses:
                    st.warning(f"• {w}")

            st.subheader("💡 Recommandations")
            for i, r in enumerate(result.recommendations, 1):
                st.write(f"{i}. {r}")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🎯 Risque")
                st.write(result.risk_assessment)
            with col2:
                st.subheader("📈 Perspective")
                st.write(result.outlook)

            st.caption(f"Confiance: {result.confidence} | Analyse: {result.timestamp.strftime('%Y-%m-%d %H:%M')}")

    with col2:
        st.subheader("📊 Scores Moning")
        st.caption("Analyse d'une position")

        if selected:
            positions = pm.get_positions(selected)
            if positions:
                ticker = st.selectbox("Position", [p.ticker for p in positions])

                if st.button("📊 Analyser"):
                    with st.spinner("Calcul des scores..."):
                        div_score = moning.calculate_dividend_safety_score(ticker)
                        growth_score = moning.calculate_growth_score(ticker)
                        valuation = moning.calculate_valuation_indicator(ticker)

                    if div_score:
                        st.metric("Score Sûreté Dividende", f"{div_score.total_score:.1f}/20", div_score.rating)

                    if growth_score:
                        st.metric("Score Croissance", f"{growth_score.total_score:.1f}/20", growth_score.rating)

                    if valuation:
                        color = "green" if valuation.status == "SOUS-EVALUE" else "red" if valuation.status == "SUREVALUE" else "orange"
                        st.markdown(f"**Valorisation:** :{color}[{valuation.status}]")
                        st.write(f"Prix: {valuation.current_price:.2f}€")
                        st.write(f"Fair Value: {valuation.fair_value:.2f}€")
                        st.write(f"Potentiel: {valuation.upside_potential:+.1f}%")


# ============================================================================
# PAGE: À PROPOS
# ============================================================================
def page_about():
    """Page À propos."""
    st.title("ℹ️ À propos de Stock Advisor")

    st.markdown("""
    ## 📈 Stock Advisor v3.0

    Outil complet de gestion de patrimoine et d'aide à la décision pour l'investissement en actions,
    inspiré de **Moning** et **Finary**.

    ### 💼 Gestion Multi-Portefeuilles

    | Fonctionnalité | Description |
    |----------------|-------------|
    | Multi-comptes | PEA, CTO, Assurance-Vie, PER, Crypto |
    | Positions | Suivi en temps réel avec PRU |
    | Transactions | Historique complet achats/ventes |
    | Dividendes | Calendrier et suivi des versements |
    | Allocation | Répartition sectorielle et géographique |
    | Import/Export | Format JSON pour backup |

    ### 🎯 Système de Scoring (4 composantes)

    | Composante | Poids | Description |
    |------------|-------|-------------|
    | Technique | 30% | MA50, MA200, momentum, tendance |
    | Fondamental | 30% | P/E, ROE, dette, croissance |
    | Sentiment | 20% | Momentum court terme, volume |
    | Smart Money | 20% | Holdings institutionnels, insiders |

    ### ✅ Performance Validée (Backtest)

    | Période | Algo | S&P 500 | Surperformance |
    |---------|------|---------|----------------|
    | 3 ans | +15.4%/an | +9.3%/an | **+66%** |
    | 5 ans | +9.0%/an | +8.2%/an | **+10%** |
    | 10 ans (B&H) | +13.9%/an | +8.3%/an | **+67%** |

    ### 📊 Sources de Données

    - Yahoo Finance (cours, fondamentaux)
    - Analyse en temps réel
    - Base de données SQLite locale

    ### 🔐 Confidentialité

    - **100% local** : aucune donnée envoyée à des serveurs externes
    - Stockage sur votre machine uniquement
    - Export JSON pour vos propres backups

    ### ⚠️ Avertissement

    Cet outil est fourni à titre informatif uniquement.
    Il ne constitue pas un conseil en investissement.

    ---
    **Version:** 3.0.0 - Multi-Portefeuilles
    """)

# ============================================================================
# MAIN
# ============================================================================
def main():
    """Point d'entrée principal."""
    # Init session state pour navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Dashboard"

    # Sidebar Header
    st.sidebar.markdown("""
        <div style="text-align: center; padding: 1rem 0 0.5rem;">
            <h1 style="font-size: 1.5rem; margin: 0; background: linear-gradient(90deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                📈 Stock Advisor
            </h1>
            <p style="color: #64748b; font-size: 0.75rem; margin-top: 0.3rem;">v4.0 Pro</p>
        </div>
    """, unsafe_allow_html=True)

    # Pages
    pages = {
        "🏠 Dashboard": page_dashboard,
        "🏆 Top Opportunités": page_opportunities,
        "💼 Mes Portefeuilles": page_portfolio,
        "📊 Projections & FIRE": page_projections,
        "📈 ETF Screener": page_etf,
        "🤖 Analyse IA": page_ai_analysis,
        "🔧 Filtres": page_filters,
        "🖥️ Hardware/LLM": page_hardware,
        "ℹ️ À propos": page_about
    }

    if HAS_EXTENDED_PAGES:
        pages.update(EXTENDED_PAGES)

    # CSS Navigation
    st.sidebar.markdown("""
        <style>
            div[data-testid="stSidebar"] .stButton > button {
                width: 100%;
                text-align: left;
                padding: 0.6rem 0.8rem;
                margin: 1px 0;
                background: transparent;
                border: none;
                border-radius: 8px;
                color: #cbd5e1;
                font-size: 0.9rem;
                transition: all 0.15s;
                box-shadow: none;
            }
            div[data-testid="stSidebar"] .stButton > button:hover {
                background: rgba(99, 102, 241, 0.2);
                color: #e2e8f0;
                transform: none;
                box-shadow: none;
            }
            .nav-title {
                color: #475569;
                font-size: 0.65rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                padding: 0.8rem 0.5rem 0.3rem;
                font-weight: 700;
            }
        </style>
    """, unsafe_allow_html=True)

    # Navigation: Principal
    st.sidebar.markdown('<p class="nav-title">📌 Principal</p>', unsafe_allow_html=True)
    for page in ["🏠 Dashboard", "🏆 Top Opportunités", "💼 Mes Portefeuilles", "📊 Projections & FIRE", "📈 ETF Screener"]:
        if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True):
            st.session_state.current_page = page

    # Navigation: v4.0
    if HAS_EXTENDED_PAGES:
        st.sidebar.markdown('<p class="nav-title">🆕 Nouveau</p>', unsafe_allow_html=True)
        for page in EXTENDED_PAGES.keys():
            if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page

    # Navigation: Config
    st.sidebar.markdown('<p class="nav-title">⚙️ Config</p>', unsafe_allow_html=True)
    for page in ["🤖 Analyse IA", "🔧 Filtres", "🖥️ Hardware/LLM", "ℹ️ À propos"]:
        if st.sidebar.button(page, key=f"nav_{page}", use_container_width=True):
            st.session_state.current_page = page

    # Watchlist
    st.sidebar.markdown('<p class="nav-title">⭐ Watchlist</p>', unsafe_allow_html=True)
    if st.session_state.watchlist:
        for ticker in st.session_state.watchlist[:5]:
            if st.sidebar.button(f"  {ticker}", key=f"wl_{ticker}", use_container_width=True):
                st.session_state.analyze_ticker = ticker
    else:
        st.sidebar.caption("Aucune action")

    # Render
    current = st.session_state.current_page
    if current in pages:
        pages[current]()
    else:
        pages["🏠 Dashboard"]()

    # Footer
    st.sidebar.markdown('<div style="text-align:center;color:#475569;font-size:0.7rem;padding:1rem;">© 2025 Stock Advisor</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
