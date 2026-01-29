"""
API FastAPI - Stock Advisor
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scrapers.yahoo_finance import YahooFinanceScraper, StockData, FundamentalData
from src.analysis.technical import TechnicalAnalyzer, TechnicalAnalysis
from src.analysis.fundamental import FundamentalAnalyzer, FundamentalAnalysis
from src.filters.base import FilterManager, StockFilterData
from src.hardware.detector import HardwareDetector


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
