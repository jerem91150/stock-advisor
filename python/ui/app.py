"""
Interface Streamlit - Stock Advisor
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
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


# Configuration de la page
st.set_page_config(
    page_title="Stock Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .score-card {
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .score-high { background-color: #28a745; color: white; }
    .score-medium { background-color: #ffc107; color: black; }
    .score-low { background-color: #dc3545; color: white; }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 5px;
    }
    .pea-badge {
        background-color: #007bff;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 0.8em;
    }
    .cto-badge {
        background-color: #6c757d;
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)


# Initialisation des services
@st.cache_resource
def init_services():
    """Initialise les services (singleton)."""
    return {
        "scraper": YahooFinanceScraper(),
        "technical_analyzer": TechnicalAnalyzer(),
        "fundamental_analyzer": FundamentalAnalyzer(),
        "filter_manager": FilterManager(),
        "hardware_detector": HardwareDetector()
    }


services = init_services()


def get_score_color(score: float) -> str:
    """Retourne la couleur selon le score."""
    if score >= 70:
        return "score-high"
    elif score >= 40:
        return "score-medium"
    else:
        return "score-low"


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
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
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

    if len(df) >= 200:
        df['MA200'] = df['Close'].rolling(window=200).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA200'],
            mode='lines', name='MA200',
            line=dict(color='red', width=1)
        ))

    fig.update_layout(
        title=f'{ticker} - Historique des prix',
        yaxis_title='Prix',
        xaxis_title='Date',
        xaxis_rangeslider_visible=False,
        height=500
    )

    return fig


def page_dashboard():
    """Page principale - Dashboard."""
    st.title("📈 Stock Advisor - Dashboard")

    # Résumé du marché
    st.subheader("Résumé du Marché")

    with st.spinner("Chargement des indices..."):
        market_summary = services["scraper"].get_market_summary()

    if market_summary:
        cols = st.columns(len(market_summary))
        for i, (name, data) in enumerate(market_summary.items()):
            with cols[i]:
                change_color = "green" if data.get('change_percent', 0) >= 0 else "red"
                st.metric(
                    label=name,
                    value=f"{data.get('price', 0):,.2f}",
                    delta=f"{data.get('change_percent', 0):.2f}%"
                )

    st.divider()

    # Recherche d'action
    st.subheader("Rechercher une Action")

    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input(
            "Entrez un symbole (ex: AAPL, MC.PA, MSFT)",
            key="search_ticker"
        ).upper()

    with col2:
        st.write("")
        st.write("")
        search_button = st.button("🔍 Analyser", type="primary")

    if search_button and ticker:
        analyze_stock(ticker)

    # Actions rapides
    st.subheader("Actions Populaires")

    popular_stocks = ["AAPL", "MSFT", "GOOGL", "AMZN", "MC.PA", "ASML.AS"]
    cols = st.columns(len(popular_stocks))

    for i, stock in enumerate(popular_stocks):
        with cols[i]:
            if st.button(stock, key=f"quick_{stock}"):
                analyze_stock(stock)


def analyze_stock(ticker: str):
    """Analyse complète d'une action."""
    st.divider()
    st.subheader(f"Analyse de {ticker}")

    # Récupération des données
    with st.spinner(f"Chargement des données pour {ticker}..."):
        stock_info = services["scraper"].get_stock_info(ticker)
        fundamentals = services["scraper"].get_fundamentals(ticker)
        price_history = services["scraper"].get_price_history(ticker, period="1y")

    if not stock_info:
        st.error(f"Impossible de trouver des données pour {ticker}")
        return

    # Header avec informations de base
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"### {stock_info.name}")
        st.write(f"**Secteur:** {stock_info.sector}")
        st.write(f"**Industrie:** {stock_info.industry}")
        st.write(f"**Pays:** {stock_info.country}")

    with col2:
        st.metric(
            "Prix actuel",
            f"{stock_info.current_price:,.2f} {stock_info.currency}",
            delta=f"{((stock_info.current_price - stock_info.previous_close) / stock_info.previous_close * 100):.2f}%"
        )

    with col3:
        # Badge PEA/CTO
        pea_eligible = services["scraper"].is_pea_eligible(ticker)
        if pea_eligible:
            st.markdown('<span class="pea-badge">PEA Éligible</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="cto-badge">CTO uniquement</span>', unsafe_allow_html=True)

        st.write(f"**Market Cap:** {stock_info.market_cap:,.0f}M {stock_info.currency}")

    st.divider()

    # Scores
    st.subheader("Scores")

    # Analyse technique
    technical_score = 50
    technical_analysis = None
    if price_history is not None and len(price_history) >= 200:
        technical_analysis = services["technical_analyzer"].analyze(price_history, ticker)
        if technical_analysis:
            technical_score = technical_analysis.score

    # Analyse fondamentale
    fundamental_score = 50
    fundamental_analysis = None
    if fundamentals:
        fund_dict = {
            "pe_ratio": fundamentals.pe_ratio,
            "peg_ratio": fundamentals.peg_ratio,
            "pb_ratio": fundamentals.pb_ratio,
            "ev_ebitda": fundamentals.ev_ebitda,
            "roe": fundamentals.roe,
            "profit_margin": fundamentals.profit_margin,
            "roa": fundamentals.roa,
            "revenue_growth": fundamentals.revenue_growth,
            "earnings_growth": fundamentals.earnings_growth,
            "debt_to_equity": fundamentals.debt_to_equity,
            "current_ratio": fundamentals.current_ratio,
            "dividend_yield": fundamentals.dividend_yield
        }
        fundamental_analysis = services["fundamental_analyzer"].analyze(
            fund_dict, ticker, stock_info.sector
        )
        if fundamental_analysis:
            fundamental_score = fundamental_analysis.score

    # Score global (pour MVP: moyenne technique + fondamental)
    global_score = (technical_score + fundamental_score) / 2

    col1, col2, col3 = st.columns(3)

    with col1:
        st.plotly_chart(
            create_gauge_chart(global_score, "Score Global"),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            create_gauge_chart(technical_score, "Score Technique"),
            use_container_width=True
        )

    with col3:
        st.plotly_chart(
            create_gauge_chart(fundamental_score, "Score Fondamental"),
            use_container_width=True
        )

    # Graphique des prix
    if price_history is not None and not price_history.empty:
        st.plotly_chart(
            create_price_chart(price_history, ticker),
            use_container_width=True
        )

    # Détails des analyses
    tab1, tab2, tab3 = st.tabs(["📊 Technique", "💰 Fondamental", "📋 Informations"])

    with tab1:
        if technical_analysis:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Tendance:** {technical_analysis.trend}")
                st.write(f"**Momentum:** {technical_analysis.momentum}")
                st.write(f"**Volatilité:** {technical_analysis.volatility:.2f}%")

            with col2:
                st.write("**Signaux:**")
                for signal in technical_analysis.signals:
                    emoji = "🟢" if signal.signal == "bullish" else "🔴" if signal.signal == "bearish" else "🟡"
                    st.write(f"{emoji} {signal.description}")
        else:
            st.info("Données insuffisantes pour l'analyse technique (min 200 jours)")

    with tab2:
        if fundamental_analysis:
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Valorisation:** {fundamental_analysis.valuation}")
                st.write(f"**Qualité:** {fundamental_analysis.quality}")
                st.write(f"**Croissance:** {fundamental_analysis.growth}")
                st.write(f"**Santé financière:** {fundamental_analysis.financial_health}")

            with col2:
                st.write("**Métriques clés:**")
                if fundamentals:
                    metrics = {
                        "P/E": fundamentals.pe_ratio,
                        "PEG": fundamentals.peg_ratio,
                        "P/B": fundamentals.pb_ratio,
                        "ROE": f"{fundamentals.roe * 100:.1f}%" if fundamentals.roe else None,
                        "Dette/Equity": fundamentals.debt_to_equity,
                        "Dividende": f"{fundamentals.dividend_yield * 100:.2f}%" if fundamentals.dividend_yield else None
                    }
                    for name, value in metrics.items():
                        if value:
                            st.write(f"- {name}: {value}")
        else:
            st.info("Données fondamentales non disponibles")

    with tab3:
        if stock_info.description:
            st.write("**Description:**")
            st.write(stock_info.description[:500] + "..." if len(stock_info.description) > 500 else stock_info.description)

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Exchange:** {stock_info.exchange}")
            st.write(f"**Volume:** {stock_info.volume:,}")
            st.write(f"**Volume moyen:** {stock_info.avg_volume:,}")

        with col2:
            st.write(f"**52 sem. haut:** {stock_info.fifty_two_week_high:,.2f}")
            st.write(f"**52 sem. bas:** {stock_info.fifty_two_week_low:,.2f}")
            if stock_info.employees:
                st.write(f"**Employés:** {stock_info.employees:,}")


def page_filters():
    """Page de configuration des filtres."""
    st.title("🔧 Configuration des Filtres")

    st.write("Personnalisez les filtres pour affiner vos recherches d'opportunités.")

    # Filtres sectoriels
    st.subheader("Filtres Sectoriels")

    col1, col2 = st.columns(2)
    with col1:
        exclude_tobacco = st.checkbox("Exclure Tabac", value=True)
        exclude_weapons = st.checkbox("Exclure Armement", value=True)
        exclude_gambling = st.checkbox("Exclure Jeux d'argent", value=True)

    with col2:
        exclude_fossil = st.checkbox("Exclure Énergies fossiles", value=False)
        pea_only = st.checkbox("PEA uniquement", value=False)

    st.divider()

    # Filtres fondamentaux
    st.subheader("Filtres Fondamentaux")

    col1, col2, col3 = st.columns(3)

    with col1:
        max_pe = st.slider("P/E Maximum", 0, 100, 50)
        max_peg = st.slider("PEG Maximum", 0.0, 5.0, 3.0, 0.1)

    with col2:
        max_debt = st.slider("Dette/Equity Maximum", 0.0, 5.0, 2.0, 0.1)
        min_roe = st.slider("ROE Minimum (%)", 0, 50, 10)

    with col3:
        min_market_cap = st.number_input(
            "Market Cap Minimum (M$)",
            min_value=0,
            max_value=1000000,
            value=1000,
            step=100
        )
        min_dividend = st.slider("Dividende Minimum (%)", 0.0, 10.0, 0.0, 0.1)

    st.divider()

    # Sauvegarder les filtres
    if st.button("💾 Sauvegarder les filtres", type="primary"):
        # Mettre à jour le filter_manager
        services["filter_manager"].filters = [
            EthicalFilter(
                exclude_tobacco=exclude_tobacco,
                exclude_weapons=exclude_weapons,
                exclude_gambling=exclude_gambling,
                exclude_fossil_fuels=exclude_fossil
            ),
            FundamentalFilter(
                max_pe=max_pe if max_pe < 100 else None,
                max_peg=max_peg if max_peg < 5.0 else None,
                max_debt_to_equity=max_debt if max_debt < 5.0 else None,
                min_roe=min_roe if min_roe > 0 else None,
                min_market_cap=min_market_cap if min_market_cap > 0 else None,
                min_dividend_yield=min_dividend if min_dividend > 0 else None
            ),
            GeographicFilter(pea_only=pea_only)
        ]
        st.success("Filtres sauvegardés!")


def page_hardware():
    """Page de configuration hardware/LLM."""
    st.title("🖥️ Configuration Hardware")

    detector = services["hardware_detector"]

    with st.spinner("Détection du hardware..."):
        system_info = detector.detect_system()

    # Informations système
    st.subheader("Système détecté")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**OS:** {system_info.os}")
        st.write(f"**CPU:** {system_info.cpu_name}")
        st.write(f"**Cœurs:** {system_info.cpu_cores}")
        st.write(f"**RAM:** {system_info.ram_gb:.1f} GB")

    with col2:
        if system_info.gpu:
            st.write(f"**GPU:** {system_info.gpu.name}")
            st.write(f"**Type:** {system_info.gpu.gpu_type.value.upper()}")
            st.write(f"**VRAM:** {system_info.gpu.vram_gb:.1f} GB")
            if system_info.gpu.cuda_version:
                st.write(f"**CUDA:** {system_info.gpu.cuda_version}")
        else:
            st.warning("Aucun GPU compatible détecté")

    st.divider()

    # Recommandation LLM
    st.subheader("Recommandation LLM")

    recommendation = detector.recommend_llm(system_info)

    st.info(f"""
    **Modèle recommandé:** {recommendation.model_name}

    - **Taille:** {recommendation.model_size}
    - **Quantification:** {recommendation.quantization}

    {recommendation.reason}
    """)

    st.code(recommendation.ollama_command, language="bash")

    # État Ollama
    st.subheader("État Ollama")

    ollama_installed = detector.check_ollama_installed()

    if ollama_installed:
        st.success("Ollama est installé")
        models = detector.get_ollama_models()
        if models:
            st.write("**Modèles installés:**")
            for model in models:
                st.write(f"- {model}")
        else:
            st.warning("Aucun modèle installé. Exécutez la commande ci-dessus.")
    else:
        st.error("Ollama n'est pas installé")
        st.write("Installez Ollama depuis: https://ollama.ai")


def page_about():
    """Page À propos."""
    st.title("ℹ️ À propos de Stock Advisor")

    st.markdown("""
    ## 📈 Stock Advisor

    Outil d'aide à la décision pour l'achat d'actions sur **PEA** et **CTO**.

    ### Fonctionnalités

    - **Analyse Technique** : Moyennes mobiles, RSI, MACD, Bollinger
    - **Analyse Fondamentale** : P/E, PEG, ROE, ratios de dette
    - **Filtres Personnalisables** : Sectoriels, éthiques, fondamentaux
    - **Éligibilité PEA/CTO** : Identification automatique

    ### Sources de Données

    - Yahoo Finance (via yfinance)
    - Données en temps réel et historiques

    ### Technologies

    - **Backend** : Python, FastAPI
    - **Frontend** : Streamlit
    - **Analyse** : pandas, numpy
    - **Visualisation** : Plotly

    ### Avertissement

    Cet outil est fourni à titre informatif uniquement.
    Il ne constitue pas un conseil en investissement.
    Faites vos propres recherches avant tout investissement.

    ---

    **Version:** 0.1.0 (MVP)
    """)


def main():
    """Point d'entrée principal."""
    # Sidebar navigation
    st.sidebar.title("📈 Stock Advisor")

    pages = {
        "Dashboard": page_dashboard,
        "Filtres": page_filters,
        "Hardware/LLM": page_hardware,
        "À propos": page_about
    }

    selection = st.sidebar.radio("Navigation", list(pages.keys()))

    # Render selected page
    pages[selection]()

    # Footer
    st.sidebar.divider()
    st.sidebar.caption("Stock Advisor v0.1.0")
    st.sidebar.caption("© 2025 - Outil d'aide à la décision")


if __name__ == "__main__":
    main()
