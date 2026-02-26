"""
API FastAPI - Stock Advisor
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sys
import logging
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.yahoo_finance import YahooFinanceScraper, StockData, FundamentalData
from src.analysis.technical import TechnicalAnalyzer, TechnicalAnalysis
from src.analysis.fundamental import FundamentalAnalyzer, FundamentalAnalysis
from src.analysis.scorer import GlobalScorer, Recommendation
from src.filters.base import FilterManager, StockFilterData
from src.hardware.detector import HardwareDetector
from src.data.stock_universe import (
    get_all_stocks, get_stocks_by_region, get_pea_eligible,
    get_stock_count, CAC40, SP500_TOP100, NASDAQ100, DAX40,
    SBF120_EXTRA, EUROSTOXX50, FTSE100
)

logger = logging.getLogger(__name__)


# Initialisation FastAPI
app = FastAPI(
    title="Stock Advisor API",
    description="API d'aide à la décision pour l'achat d'actions sur PEA et CTO",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services singleton
scraper = YahooFinanceScraper()
technical_analyzer = TechnicalAnalyzer()
fundamental_analyzer = FundamentalAnalyzer()
global_scorer = GlobalScorer()
filter_manager = FilterManager()
hardware_detector = HardwareDetector()


# Modèles Pydantic pour l'API
class StockResponse(BaseModel):
    """Réponse pour les informations d'une action."""
    ticker: str
    name: str
    exchange: str
    currency: str
    country: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: float
    current_price: float
    previous_close: float
    day_high: float
    day_low: float
    volume: int
    avg_volume: int
    fifty_two_week_high: float
    fifty_two_week_low: float
    pea_eligible: bool


class FundamentalsResponse(BaseModel):
    """Réponse pour les données fondamentales."""
    ticker: str
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    pb_ratio: Optional[float]
    ps_ratio: Optional[float]
    ev_ebitda: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    profit_margin: Optional[float]
    operating_margin: Optional[float]
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]
    debt_to_equity: Optional[float]
    current_ratio: Optional[float]
    dividend_yield: Optional[float]
    beta: Optional[float]
    eps: Optional[float]


class TechnicalScoreResponse(BaseModel):
    """Réponse pour le score technique."""
    ticker: str
    score: float
    trend: str
    momentum: str
    volatility: float
    signals: list[dict]


class FundamentalScoreResponse(BaseModel):
    """Réponse pour le score fondamental."""
    ticker: str
    score: float
    valuation: str
    quality: str
    growth: str
    financial_health: str
    signals: list[dict]


class FullAnalysisResponse(BaseModel):
    """Réponse pour l'analyse complète."""
    ticker: str
    name: str
    pea_eligible: bool
    current_price: float
    currency: str

    # Scores
    global_score: float
    technical_score: float
    fundamental_score: float
    sentiment_score: Optional[float] = None
    smart_money_score: Optional[float] = None

    # Analyses détaillées
    technical: Optional[dict]
    fundamental: Optional[dict]

    # Timestamp
    analyzed_at: datetime


class MarketSummaryResponse(BaseModel):
    """Réponse pour le résumé du marché."""
    indices: dict


class HardwareInfoResponse(BaseModel):
    """Réponse pour les informations hardware."""
    os: str
    cpu: str
    cpu_cores: int
    ram_gb: float
    gpu_type: Optional[str]
    gpu_name: Optional[str]
    gpu_vram_gb: Optional[float]
    ollama_installed: bool
    recommended_model: str
    ollama_command: str


class CompleteAnalysisResponse(BaseModel):
    """Reponse pour l'analyse complete 4 piliers."""
    ticker: str
    name: str
    pea_eligible: bool
    current_price: float
    currency: str
    sector: Optional[str] = None
    industry: Optional[str] = None

    # Scores
    global_score: float
    technical_score: float
    fundamental_score: float
    sentiment_score: Optional[float] = None
    smart_money_score: Optional[float] = None

    # Recommandation
    recommendation: str
    confidence: str
    strengths: list[str]
    weaknesses: list[str]
    summary: str

    # Analyses detaillees
    technical: Optional[dict] = None
    fundamental: Optional[dict] = None

    analyzed_at: datetime


class ScreenRequest(BaseModel):
    """Requete de screening."""
    tickers: list[str]
    sort_by: str = "global_score"
    limit: int = 20
    min_score: float = 0
    pea_only: bool = False


class CompareRequest(BaseModel):
    """Requete de comparaison."""
    tickers: list[str] = Field(..., min_length=2, max_length=5)


class PortfolioSuggestRequest(BaseModel):
    """Requete de suggestion de portefeuille."""
    budget: float
    risk_profile: str = "moderate"  # conservative, moderate, aggressive
    horizon: str = "medium"  # short (1-2y), medium (3-5y), long (5y+)
    pea_only: bool = False
    max_positions: int = 10
    region: Optional[str] = None


class FilterConfig(BaseModel):
    """Configuration des filtres."""
    exclude_tobacco: bool = True
    exclude_weapons: bool = True
    exclude_gambling: bool = True
    exclude_fossil_fuels: bool = False
    pea_only: bool = False
    max_pe: Optional[float] = 50
    max_peg: Optional[float] = 3
    max_debt_to_equity: Optional[float] = 2
    min_roe: Optional[float] = None
    min_market_cap: Optional[float] = 1000
    min_dividend_yield: Optional[float] = None


# Routes API

@app.get("/")
async def root():
    """Route racine."""
    return {
        "name": "Stock Advisor API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Vérification de santé de l'API."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


@app.get("/stock/{ticker}", response_model=StockResponse)
async def get_stock_info(ticker: str):
    """
    Récupère les informations d'une action.

    - **ticker**: Symbole de l'action (ex: AAPL, MC.PA)
    """
    stock_info = scraper.get_stock_info(ticker.upper())

    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Action {ticker} non trouvée")

    pea_eligible = scraper.is_pea_eligible(ticker.upper())

    return StockResponse(
        ticker=ticker.upper(),
        name=stock_info.name,
        exchange=stock_info.exchange,
        currency=stock_info.currency,
        country=stock_info.country,
        sector=stock_info.sector,
        industry=stock_info.industry,
        market_cap=stock_info.market_cap,
        current_price=stock_info.current_price,
        previous_close=stock_info.previous_close,
        day_high=stock_info.day_high,
        day_low=stock_info.day_low,
        volume=stock_info.volume,
        avg_volume=stock_info.avg_volume,
        fifty_two_week_high=stock_info.fifty_two_week_high,
        fifty_two_week_low=stock_info.fifty_two_week_low,
        pea_eligible=pea_eligible
    )


@app.get("/stock/{ticker}/fundamentals", response_model=FundamentalsResponse)
async def get_stock_fundamentals(ticker: str):
    """
    Récupère les données fondamentales d'une action.

    - **ticker**: Symbole de l'action
    """
    fundamentals = scraper.get_fundamentals(ticker.upper())

    if not fundamentals:
        raise HTTPException(status_code=404, detail=f"Fondamentaux non disponibles pour {ticker}")

    return FundamentalsResponse(
        ticker=ticker.upper(),
        pe_ratio=fundamentals.pe_ratio,
        forward_pe=fundamentals.forward_pe,
        peg_ratio=fundamentals.peg_ratio,
        pb_ratio=fundamentals.pb_ratio,
        ps_ratio=fundamentals.ps_ratio,
        ev_ebitda=fundamentals.ev_ebitda,
        roe=fundamentals.roe,
        roa=fundamentals.roa,
        profit_margin=fundamentals.profit_margin,
        operating_margin=fundamentals.operating_margin,
        revenue_growth=fundamentals.revenue_growth,
        earnings_growth=fundamentals.earnings_growth,
        debt_to_equity=fundamentals.debt_to_equity,
        current_ratio=fundamentals.current_ratio,
        dividend_yield=fundamentals.dividend_yield,
        beta=fundamentals.beta,
        eps=fundamentals.eps
    )


@app.get("/stock/{ticker}/technical", response_model=TechnicalScoreResponse)
async def get_technical_analysis(
    ticker: str,
    period: str = Query("1y", description="Période: 1mo, 3mo, 6mo, 1y, 2y")
):
    """
    Analyse technique d'une action.

    - **ticker**: Symbole de l'action
    - **period**: Période d'historique pour l'analyse
    """
    price_history = scraper.get_price_history(ticker.upper(), period=period)

    if price_history is None or len(price_history) < 50:
        raise HTTPException(
            status_code=400,
            detail="Données insuffisantes pour l'analyse technique"
        )

    analysis = technical_analyzer.analyze(price_history, ticker.upper())

    if not analysis:
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse technique")

    signals = [
        {
            "name": s.name,
            "value": s.value,
            "signal": s.signal,
            "description": s.description
        }
        for s in analysis.signals
    ]

    return TechnicalScoreResponse(
        ticker=ticker.upper(),
        score=analysis.score,
        trend=analysis.trend,
        momentum=analysis.momentum,
        volatility=analysis.volatility,
        signals=signals
    )


@app.get("/stock/{ticker}/fundamental-analysis", response_model=FundamentalScoreResponse)
async def get_fundamental_analysis(ticker: str):
    """
    Analyse fondamentale d'une action.

    - **ticker**: Symbole de l'action
    """
    stock_info = scraper.get_stock_info(ticker.upper())
    fundamentals = scraper.get_fundamentals(ticker.upper())

    if not fundamentals:
        raise HTTPException(
            status_code=404,
            detail="Données fondamentales non disponibles"
        )

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

    sector = stock_info.sector if stock_info else None
    analysis = fundamental_analyzer.analyze(fund_dict, ticker.upper(), sector)

    if not analysis:
        raise HTTPException(status_code=500, detail="Erreur lors de l'analyse fondamentale")

    signals = [
        {
            "name": s.name,
            "value": s.value,
            "signal": s.signal,
            "description": s.description
        }
        for s in analysis.signals
    ]

    return FundamentalScoreResponse(
        ticker=ticker.upper(),
        score=analysis.score,
        valuation=analysis.valuation,
        quality=analysis.quality,
        growth=analysis.growth,
        financial_health=analysis.financial_health,
        signals=signals
    )


@app.get("/stock/{ticker}/full-analysis", response_model=FullAnalysisResponse)
async def get_full_analysis(ticker: str):
    """
    Analyse complète d'une action (technique + fondamentale).

    - **ticker**: Symbole de l'action
    """
    ticker = ticker.upper()

    # Récupérer les données
    stock_info = scraper.get_stock_info(ticker)
    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Action {ticker} non trouvée")

    fundamentals = scraper.get_fundamentals(ticker)
    price_history = scraper.get_price_history(ticker, period="1y")

    # Analyse technique
    technical_score = 50.0
    technical_data = None

    if price_history is not None and len(price_history) >= 50:
        tech_analysis = technical_analyzer.analyze(price_history, ticker)
        if tech_analysis:
            technical_score = tech_analysis.score
            technical_data = {
                "score": tech_analysis.score,
                "trend": tech_analysis.trend,
                "momentum": tech_analysis.momentum,
                "volatility": tech_analysis.volatility,
                "signals": [
                    {"name": s.name, "signal": s.signal, "description": s.description}
                    for s in tech_analysis.signals
                ]
            }

    # Analyse fondamentale
    fundamental_score = 50.0
    fundamental_data = None

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
        fund_analysis = fundamental_analyzer.analyze(fund_dict, ticker, stock_info.sector)
        if fund_analysis:
            fundamental_score = fund_analysis.score
            fundamental_data = {
                "score": fund_analysis.score,
                "valuation": fund_analysis.valuation,
                "quality": fund_analysis.quality,
                "growth": fund_analysis.growth,
                "financial_health": fund_analysis.financial_health,
                "signals": [
                    {"name": s.name, "signal": s.signal, "description": s.description}
                    for s in fund_analysis.signals
                ]
            }

    # Score global (moyenne pour MVP)
    global_score = (technical_score + fundamental_score) / 2

    return FullAnalysisResponse(
        ticker=ticker,
        name=stock_info.name,
        pea_eligible=scraper.is_pea_eligible(ticker),
        current_price=stock_info.current_price,
        currency=stock_info.currency,
        global_score=global_score,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        technical=technical_data,
        fundamental=fundamental_data,
        analyzed_at=datetime.utcnow()
    )


@app.get("/market/summary", response_model=MarketSummaryResponse)
async def get_market_summary():
    """Récupère le résumé des principaux indices."""
    summary = scraper.get_market_summary()
    return MarketSummaryResponse(indices=summary)


@app.get("/market/indices/{index_name}")
async def get_index_constituents(index_name: str):
    """
    Récupère les constituants d'un indice.

    - **index_name**: Nom de l'indice (CAC40, SP500, NASDAQ100)
    """
    constituents = scraper.get_index_constituents(index_name.upper())

    if not constituents:
        raise HTTPException(
            status_code=404,
            detail=f"Indice {index_name} non trouvé ou vide"
        )

    return {"index": index_name.upper(), "constituents": constituents}


@app.get("/hardware", response_model=HardwareInfoResponse)
async def get_hardware_info():
    """Récupère les informations hardware et la recommandation LLM."""
    system_info = hardware_detector.detect_system()
    recommendation = hardware_detector.recommend_llm(system_info)

    return HardwareInfoResponse(
        os=system_info.os,
        cpu=system_info.cpu_name,
        cpu_cores=system_info.cpu_cores,
        ram_gb=system_info.ram_gb,
        gpu_type=system_info.gpu.gpu_type.value if system_info.gpu else None,
        gpu_name=system_info.gpu.name if system_info.gpu else None,
        gpu_vram_gb=system_info.gpu.vram_gb if system_info.gpu else None,
        ollama_installed=hardware_detector.check_ollama_installed(),
        recommended_model=recommendation.model_name,
        ollama_command=recommendation.ollama_command
    )


@app.post("/filters/apply")
async def apply_filters(
    tickers: list[str],
    config: FilterConfig
):
    """
    Applique les filtres à une liste d'actions.

    - **tickers**: Liste de symboles à filtrer
    - **config**: Configuration des filtres
    """
    from src.filters.base import EthicalFilter, FundamentalFilter, GeographicFilter

    # Configurer les filtres
    filter_manager.filters = [
        EthicalFilter(
            exclude_tobacco=config.exclude_tobacco,
            exclude_weapons=config.exclude_weapons,
            exclude_gambling=config.exclude_gambling,
            exclude_fossil_fuels=config.exclude_fossil_fuels
        ),
        FundamentalFilter(
            max_pe=config.max_pe,
            max_peg=config.max_peg,
            max_debt_to_equity=config.max_debt_to_equity,
            min_roe=config.min_roe,
            min_market_cap=config.min_market_cap,
            min_dividend_yield=config.min_dividend_yield
        ),
        GeographicFilter(pea_only=config.pea_only)
    ]

    results = []
    passed = []
    rejected = []

    for ticker in tickers:
        stock_info = scraper.get_stock_info(ticker.upper())
        fundamentals = scraper.get_fundamentals(ticker.upper())

        if not stock_info:
            rejected.append({"ticker": ticker, "reason": "Action non trouvée"})
            continue

        filter_data = StockFilterData(
            ticker=ticker.upper(),
            name=stock_info.name,
            sector=stock_info.sector,
            industry=stock_info.industry,
            country=stock_info.country,
            exchange=stock_info.exchange,
            market_cap=stock_info.market_cap,
            pea_eligible=scraper.is_pea_eligible(ticker.upper()),
            pe_ratio=fundamentals.pe_ratio if fundamentals else None,
            peg_ratio=fundamentals.peg_ratio if fundamentals else None,
            debt_to_equity=fundamentals.debt_to_equity if fundamentals else None,
            dividend_yield=fundamentals.dividend_yield if fundamentals else None,
            roe=fundamentals.roe if fundamentals else None
        )

        is_passed, filter_results = filter_manager.apply_filters(filter_data)

        if is_passed:
            passed.append(ticker.upper())
        else:
            reasons = [r.reason for r in filter_results if not r.passed and r.reason]
            rejected.append({"ticker": ticker.upper(), "reasons": reasons})

    return {
        "total": len(tickers),
        "passed": passed,
        "rejected": rejected,
        "passed_count": len(passed),
        "rejected_count": len(rejected)
    }


# =====================================================================
# Helper: analyse complete d'un ticker (reutilise par plusieurs endpoints)
# =====================================================================

def _analyze_ticker(ticker: str) -> dict:
    """Analyse complete d'un ticker, retourne un dict ou leve HTTPException."""
    ticker = ticker.upper()
    stock_info = scraper.get_stock_info(ticker)
    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Action {ticker} non trouvee")

    fundamentals = scraper.get_fundamentals(ticker)
    price_history = scraper.get_price_history(ticker, period="1y")

    # Technique
    technical_score = None
    technical_data = None
    tech_analysis = None
    if price_history is not None and len(price_history) >= 50:
        tech_analysis = technical_analyzer.analyze(price_history, ticker)
        if tech_analysis:
            technical_score = tech_analysis.score
            technical_data = {
                "score": tech_analysis.score,
                "trend": tech_analysis.trend,
                "momentum": tech_analysis.momentum,
                "volatility": tech_analysis.volatility,
                "signals": [
                    {"name": s.name, "signal": s.signal, "description": s.description}
                    for s in tech_analysis.signals
                ],
            }

    # Fondamental
    fundamental_score = None
    fundamental_data = None
    fund_analysis = None
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
            "dividend_yield": fundamentals.dividend_yield,
        }
        fund_analysis = fundamental_analyzer.analyze(fund_dict, ticker, stock_info.sector)
        if fund_analysis:
            fundamental_score = fund_analysis.score
            fundamental_data = {
                "score": fund_analysis.score,
                "valuation": fund_analysis.valuation,
                "quality": fund_analysis.quality,
                "growth": fund_analysis.growth,
                "financial_health": fund_analysis.financial_health,
                "signals": [
                    {"name": s.name, "signal": s.signal, "description": s.description}
                    for s in fund_analysis.signals
                ],
            }

    # Score global via GlobalScorer
    global_analysis = global_scorer.calculate_global_score(
        ticker=ticker,
        company_name=stock_info.name,
        technical_score=technical_score,
        fundamental_score=fundamental_score,
        technical_analysis=tech_analysis,
        fundamental_analysis=fund_analysis,
    )

    return {
        "ticker": ticker,
        "name": stock_info.name,
        "pea_eligible": scraper.is_pea_eligible(ticker),
        "current_price": stock_info.current_price,
        "currency": stock_info.currency,
        "sector": stock_info.sector,
        "industry": stock_info.industry,
        "global_score": round(global_analysis.score, 1),
        "technical_score": round(technical_score, 1) if technical_score else None,
        "fundamental_score": round(fundamental_score, 1) if fundamental_score else None,
        "sentiment_score": None,
        "smart_money_score": None,
        "recommendation": global_analysis.recommendation.value,
        "confidence": global_analysis.confidence,
        "strengths": global_analysis.strengths,
        "weaknesses": global_analysis.weaknesses,
        "summary": global_analysis.summary,
        "technical": technical_data,
        "fundamental": fundamental_data,
        "analyzed_at": datetime.utcnow(),
    }


# =====================================================================
# Nouveaux endpoints pour AgentHub
# =====================================================================

@app.get("/stock/{ticker}/complete-analysis", response_model=CompleteAnalysisResponse)
async def get_complete_analysis(ticker: str):
    """
    Analyse complete 4 piliers avec score global, recommandation,
    forces/faiblesses et resume.
    """
    data = _analyze_ticker(ticker)
    return CompleteAnalysisResponse(**data)


@app.post("/screen")
async def screen_stocks(request: ScreenRequest):
    """
    Scorer et classer N tickers. Retourne la liste triee par score.
    """
    results = []
    for ticker in request.tickers:
        try:
            data = _analyze_ticker(ticker)
            if request.pea_only and not data["pea_eligible"]:
                continue
            if data["global_score"] >= request.min_score:
                results.append(data)
        except Exception as e:
            logger.warning(f"Screening skip {ticker}: {e}")
            continue

    # Tri
    sort_key = request.sort_by
    results.sort(key=lambda x: x.get(sort_key, 0) or 0, reverse=True)

    return {
        "total_screened": len(request.tickers),
        "results_count": len(results[:request.limit]),
        "results": results[:request.limit],
    }


@app.post("/compare")
async def compare_stocks(request: CompareRequest):
    """
    Comparer 2 a 5 actions cote a cote.
    """
    analyses = []
    for ticker in request.tickers:
        try:
            data = _analyze_ticker(ticker)
            analyses.append(data)
        except Exception as e:
            analyses.append({"ticker": ticker.upper(), "error": str(e)})

    # Classement
    valid = [a for a in analyses if "error" not in a]
    valid.sort(key=lambda x: x["global_score"], reverse=True)
    ranking = {a["ticker"]: i + 1 for i, a in enumerate(valid)}

    return {
        "stocks": analyses,
        "ranking": ranking,
        "best_pick": valid[0]["ticker"] if valid else None,
    }


@app.get("/universe")
async def get_universe(
    region: Optional[str] = Query(None, description="Region: USA, FRANCE, EUROPE, ASIE, etc."),
    index: Optional[str] = Query(None, description="Indice: CAC40, SP500, NASDAQ100, DAX40"),
    pea_only: bool = Query(False, description="Uniquement eligibles PEA"),
):
    """
    Lister les actions disponibles par region ou indice.
    """
    INDEX_MAP = {
        "CAC40": CAC40,
        "SP500": SP500_TOP100,
        "NASDAQ100": NASDAQ100,
        "DAX40": DAX40,
        "SBF120": list(set(CAC40 + SBF120_EXTRA)),
        "EUROSTOXX50": EUROSTOXX50,
        "FTSE100": FTSE100,
    }

    if index:
        tickers = INDEX_MAP.get(index.upper(), [])
        if not tickers:
            raise HTTPException(status_code=404, detail=f"Indice {index} non trouve")
    elif region:
        tickers = get_stocks_by_region(region)
        if not tickers:
            raise HTTPException(status_code=404, detail=f"Region {region} non trouvee")
    else:
        tickers = get_all_stocks()

    if pea_only:
        pea_set = set(get_pea_eligible())
        tickers = [t for t in tickers if t in pea_set]

    return {
        "count": len(tickers),
        "tickers": sorted(tickers),
        "available_regions": list(["USA", "FRANCE", "ALLEMAGNE", "EUROPE", "JAPON", "CHINE", "ASIE", "AUSTRALIE", "CANADA", "UK", "SUISSE"]),
        "available_indices": list(INDEX_MAP.keys()),
    }


@app.post("/suggest-portfolio")
async def suggest_portfolio(request: PortfolioSuggestRequest):
    """
    Suggerer un portefeuille diversifie selon budget, profil risque et horizon.
    """
    # Selectionner l'univers
    if request.region:
        candidates = get_stocks_by_region(request.region)
    elif request.pea_only:
        candidates = get_pea_eligible()
    else:
        candidates = CAC40 + SP500_TOP100[:30]  # Top picks FR + US

    if request.pea_only:
        pea_set = set(get_pea_eligible())
        candidates = [t for t in candidates if t in pea_set]

    # Scorer les candidats
    scored = []
    for ticker in candidates[:50]:  # Limiter pour performance
        try:
            data = _analyze_ticker(ticker)
            scored.append(data)
        except Exception:
            continue

    scored.sort(key=lambda x: x["global_score"], reverse=True)

    # Filtrer par profil de risque
    if request.risk_profile == "conservative":
        scored = [s for s in scored if s.get("recommendation") in ("strong_buy", "buy", "hold")]
    elif request.risk_profile == "aggressive":
        scored = [s for s in scored if s.get("recommendation") in ("strong_buy", "buy")]

    # Selectionner les top positions
    selected = scored[:request.max_positions]

    if not selected:
        return {"error": "Aucune action ne correspond aux criteres", "portfolio": []}

    # Repartir le budget
    total_score = sum(s["global_score"] for s in selected)
    portfolio = []
    for stock in selected:
        weight = stock["global_score"] / total_score if total_score > 0 else 1 / len(selected)
        allocation = round(request.budget * weight, 2)
        shares = int(allocation / stock["current_price"]) if stock["current_price"] > 0 else 0
        portfolio.append({
            "ticker": stock["ticker"],
            "name": stock["name"],
            "score": stock["global_score"],
            "recommendation": stock["recommendation"],
            "current_price": stock["current_price"],
            "currency": stock["currency"],
            "pea_eligible": stock["pea_eligible"],
            "weight": round(weight * 100, 1),
            "allocation": allocation,
            "shares": shares,
            "total_cost": round(shares * stock["current_price"], 2),
        })

    total_invested = sum(p["total_cost"] for p in portfolio)

    return {
        "budget": request.budget,
        "risk_profile": request.risk_profile,
        "horizon": request.horizon,
        "pea_only": request.pea_only,
        "portfolio": portfolio,
        "total_invested": total_invested,
        "cash_remaining": round(request.budget - total_invested, 2),
        "positions_count": len(portfolio),
    }


@app.get("/stock/{ticker}/pea-eligible")
async def check_pea_eligible(ticker: str):
    """
    Verifier l'eligibilite PEA d'une action.
    """
    ticker = ticker.upper()
    stock_info = scraper.get_stock_info(ticker)
    if not stock_info:
        raise HTTPException(status_code=404, detail=f"Action {ticker} non trouvee")

    pea_eligible = scraper.is_pea_eligible(ticker)
    pea_list = set(get_pea_eligible())

    return {
        "ticker": ticker,
        "name": stock_info.name,
        "pea_eligible": pea_eligible or ticker in pea_list,
        "country": stock_info.country,
        "exchange": stock_info.exchange,
        "reason": "Action europeenne (EEE)" if (pea_eligible or ticker in pea_list) else "Hors zone EEE",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
