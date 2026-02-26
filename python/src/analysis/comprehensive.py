"""
Module d'Analyse Comprehensive - Style Moning.fr

Combine toutes les analyses en un verdict unique et clair:
- Valorisation (sous/sur-évalué)
- Croissance (historique et estimée)
- Dividendes (sécurité, croissance)
- Santé financière
- Momentum technique
- Sentiment marché
- Smart Money

Output: Score global + Verdict clair + Résumé IA
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class Verdict(Enum):
    """Verdict final d'investissement."""
    STRONG_BUY = "ACHAT FORT"
    BUY = "ACHAT"
    HOLD = "CONSERVER"
    SELL = "VENDRE"
    STRONG_SELL = "VENDRE URGENT"


class StarRating(Enum):
    """Notation étoiles style Morningstar."""
    FIVE_STARS = 5
    FOUR_STARS = 4
    THREE_STARS = 3
    TWO_STARS = 2
    ONE_STAR = 1


@dataclass
class ScoreComponent:
    """Composant de score avec détails."""
    name: str
    score: float  # 0-100
    weight: float  # Pondération
    signal: str  # "bullish", "neutral", "bearish"
    details: str  # Explication courte
    sub_scores: dict = field(default_factory=dict)


@dataclass
class DividendAnalysis:
    """Analyse dividende détaillée."""
    yield_current: Optional[float]
    yield_5y_avg: Optional[float]
    payout_ratio: Optional[float]
    growth_5y: Optional[float]  # Croissance annuelle sur 5 ans
    years_of_growth: int  # Années consécutives de hausse
    safety_score: float  # 0-100
    is_dividend_king: bool  # 25+ ans de hausse
    is_dividend_aristocrat: bool  # 10+ ans de hausse
    next_ex_date: Optional[str]
    annual_amount: Optional[float]


@dataclass
class GrowthAnalysis:
    """Analyse croissance."""
    revenue_growth_1y: Optional[float]
    revenue_growth_5y: Optional[float]
    earnings_growth_1y: Optional[float]
    earnings_growth_5y: Optional[float]
    fcf_growth_5y: Optional[float]
    growth_score: float  # 0-100
    growth_consistency: str  # "stable", "volatile", "declining"


@dataclass
class ValuationAnalysis:
    """Analyse valorisation."""
    pe_ratio: Optional[float]
    pe_5y_avg: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    pb_ratio: Optional[float]
    ps_ratio: Optional[float]
    ev_ebitda: Optional[float]
    fcf_yield: Optional[float]

    fair_value_pe: Optional[float]
    fair_value_dcf: Optional[float]
    fair_value_dividend: Optional[float]

    upside_potential: float  # % de hausse potentielle
    valuation_score: float  # 0-100 (100 = très sous-évalué)
    valuation_signal: str  # "undervalued", "fair", "overvalued"


@dataclass
class HealthAnalysis:
    """Analyse santé financière."""
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    debt_to_equity: Optional[float]
    interest_coverage: Optional[float]
    roe: Optional[float]
    roa: Optional[float]
    profit_margin: Optional[float]
    health_score: float  # 0-100


@dataclass
class ComprehensiveAnalysis:
    """Résultat complet de l'analyse."""
    # Identité
    ticker: str
    name: str
    sector: str
    industry: str
    currency: str

    # Prix
    current_price: float
    price_change_1d: Optional[float]
    price_change_1y: Optional[float]
    high_52w: float
    low_52w: float

    # Capitalisation
    market_cap: float
    market_cap_category: str  # "Large", "Mid", "Small"

    # Beta
    beta: Optional[float]
    volatility_level: str  # "low", "medium", "high"

    # Analyses détaillées
    valuation: ValuationAnalysis
    growth: GrowthAnalysis
    dividend: DividendAnalysis
    health: HealthAnalysis

    # Scores composants
    score_components: list  # Liste de ScoreComponent

    # Score global
    global_score: float  # 0-100
    star_rating: StarRating
    verdict: Verdict
    confidence: str  # "high", "medium", "low"

    # Résumé
    strengths: list
    weaknesses: list
    summary: str
    ai_recommendation: str

    # Meta
    analysis_date: datetime = field(default_factory=datetime.now)
    data_quality: str = "complete"  # "complete", "partial", "limited"


class ComprehensiveAnalyzer:
    """
    Analyseur comprehensive combinant toutes les sources.
    """

    # Pondérations des composants
    WEIGHTS = {
        'valuation': 0.25,      # Sous/sur-évalué
        'growth': 0.20,         # Croissance
        'dividend': 0.15,       # Dividende
        'health': 0.15,         # Santé financière
        'technical': 0.15,      # Momentum technique
        'sentiment': 0.10,      # Sentiment marché
    }

    # Seuils par secteur pour P/E
    SECTOR_PE = {
        'Technology': 25,
        'Financial Services': 10,
        'Healthcare': 20,
        'Consumer Cyclical': 18,
        'Consumer Defensive': 20,
        'Industrials': 18,
        'Energy': 12,
        'Utilities': 15,
        'Real Estate': 20,
        'Basic Materials': 15,
        'Communication Services': 18,
        'default': 18
    }

    def __init__(self):
        from src.scrapers.yahoo_finance import YahooFinanceScraper
        from src.analysis.technical import TechnicalAnalyzer

        self.yahoo = YahooFinanceScraper()
        self.technical = TechnicalAnalyzer()

    def analyze(self, ticker: str, include_sentiment: bool = False) -> Optional[ComprehensiveAnalysis]:
        """
        Analyse comprehensive d'une action.

        Args:
            ticker: Symbole de l'action
            include_sentiment: Inclure analyse sentiment (plus lent)

        Returns:
            ComprehensiveAnalysis ou None
        """
        # Récupérer toutes les données
        info = self.yahoo.get_stock_info(ticker)
        if not info or not info.current_price:
            logger.error(f"Impossible de récupérer les données pour {ticker}")
            return None

        fund = self.yahoo.get_fundamentals(ticker)
        history = self.yahoo.get_price_history(ticker, period="5y")

        # Données de base
        current_price = info.current_price
        name = info.name or ticker
        sector = info.sector or "Unknown"
        industry = info.industry or "Unknown"
        currency = info.currency or "EUR"
        market_cap = info.market_cap or 0

        # Catégorie capitalisation
        if market_cap > 10e9:
            cap_category = "Large Cap"
        elif market_cap > 2e9:
            cap_category = "Mid Cap"
        else:
            cap_category = "Small Cap"

        # Beta et volatilité
        beta = fund.beta if fund else None
        if beta:
            if beta < 0.8:
                volatility = "low"
            elif beta < 1.2:
                volatility = "medium"
            else:
                volatility = "high"
        else:
            volatility = "unknown"

        # 52 semaines high/low
        high_52w = info.fifty_two_week_high or current_price
        low_52w = info.fifty_two_week_low or current_price

        # Variation prix
        price_change_1d = None
        if info.previous_close:
            price_change_1d = ((current_price / info.previous_close) - 1) * 100

        price_change_1y = None
        if history is not None and len(history) >= 252:
            price_1y_ago = history['Close'].iloc[-252]
            price_change_1y = ((current_price / price_1y_ago) - 1) * 100

        # Analyses détaillées
        valuation = self._analyze_valuation(ticker, current_price, fund, sector)
        growth = self._analyze_growth(fund, history)
        dividend = self._analyze_dividend(current_price, fund)
        health = self._analyze_health(fund)

        # Analyse technique
        tech_score = 50
        tech_signal = "neutral"
        tech_details = "Données insuffisantes"

        if history is not None and len(history) >= 200:
            tech_analysis = self.technical.analyze(history, ticker)
            if tech_analysis:
                tech_score = tech_analysis.score
                tech_signal = "bullish" if tech_score > 60 else "bearish" if tech_score < 40 else "neutral"
                tech_details = f"Tendance {tech_analysis.trend}, momentum {tech_analysis.momentum}"

        # Construire les composants de score
        score_components = [
            ScoreComponent(
                name="Valorisation",
                score=valuation.valuation_score,
                weight=self.WEIGHTS['valuation'],
                signal=valuation.valuation_signal,
                details=f"P/E {valuation.pe_ratio:.1f}x" if valuation.pe_ratio else "N/A",
                sub_scores={
                    'pe_vs_sector': self._pe_score(valuation.pe_ratio, sector),
                    'pb_score': self._pb_score(valuation.pb_ratio),
                    'upside': valuation.upside_potential
                }
            ),
            ScoreComponent(
                name="Croissance",
                score=growth.growth_score,
                weight=self.WEIGHTS['growth'],
                signal="bullish" if growth.growth_score > 60 else "bearish" if growth.growth_score < 40 else "neutral",
                details=f"CA {growth.revenue_growth_1y:+.1f}%" if growth.revenue_growth_1y else "N/A",
                sub_scores={
                    'revenue': growth.revenue_growth_1y,
                    'earnings': growth.earnings_growth_1y
                }
            ),
            ScoreComponent(
                name="Dividende",
                score=dividend.safety_score,
                weight=self.WEIGHTS['dividend'],
                signal="bullish" if dividend.safety_score > 60 else "neutral",
                details=f"Yield {dividend.yield_current:.2f}%" if dividend.yield_current else "Pas de dividende",
                sub_scores={
                    'yield': dividend.yield_current,
                    'payout': dividend.payout_ratio,
                    'growth': dividend.growth_5y
                }
            ),
            ScoreComponent(
                name="Santé Financière",
                score=health.health_score,
                weight=self.WEIGHTS['health'],
                signal="bullish" if health.health_score > 60 else "bearish" if health.health_score < 40 else "neutral",
                details=f"ROE {health.roe*100:.1f}%" if health.roe else "N/A",
                sub_scores={
                    'roe': health.roe,
                    'debt': health.debt_to_equity,
                    'margin': health.profit_margin
                }
            ),
            ScoreComponent(
                name="Technique",
                score=tech_score,
                weight=self.WEIGHTS['technical'],
                signal=tech_signal,
                details=tech_details
            ),
        ]

        # Sentiment (optionnel)
        if include_sentiment:
            try:
                from src.sentiment.analyzer import SentimentAnalyzer
                sentiment_analyzer = SentimentAnalyzer()
                sent_analysis = sentiment_analyzer.analyze(ticker, name, use_llm=False, max_news=5, max_reddit=5)
                sent_score = sent_analysis.score if sent_analysis else 50
            except Exception:
                sent_score = 50

            score_components.append(ScoreComponent(
                name="Sentiment",
                score=sent_score,
                weight=self.WEIGHTS['sentiment'],
                signal="bullish" if sent_score > 60 else "bearish" if sent_score < 40 else "neutral",
                details="Analyse news/réseaux"
            ))

        # Calculer score global
        total_weight = sum(c.weight for c in score_components)
        global_score = sum(c.score * c.weight for c in score_components) / total_weight

        # Notation étoiles
        if global_score >= 80:
            stars = StarRating.FIVE_STARS
        elif global_score >= 65:
            stars = StarRating.FOUR_STARS
        elif global_score >= 50:
            stars = StarRating.THREE_STARS
        elif global_score >= 35:
            stars = StarRating.TWO_STARS
        else:
            stars = StarRating.ONE_STAR

        # Verdict
        if global_score >= 75 and valuation.valuation_signal == "undervalued":
            verdict = Verdict.STRONG_BUY
        elif global_score >= 60:
            verdict = Verdict.BUY
        elif global_score >= 45:
            verdict = Verdict.HOLD
        elif global_score >= 30:
            verdict = Verdict.SELL
        else:
            verdict = Verdict.STRONG_SELL

        # Identifier forces et faiblesses
        strengths = []
        weaknesses = []

        for comp in score_components:
            if comp.score >= 70:
                strengths.append(f"{comp.name}: {comp.details}")
            elif comp.score < 40:
                weaknesses.append(f"{comp.name}: {comp.details}")

        if valuation.upside_potential > 20:
            strengths.append(f"Potentiel de hausse: +{valuation.upside_potential:.0f}%")
        if dividend.yield_current and dividend.yield_current > 4:
            strengths.append(f"Rendement dividende élevé: {dividend.yield_current:.1f}%")
        if dividend.is_dividend_aristocrat:
            strengths.append("Aristocrate du dividende (10+ ans)")
        if health.debt_to_equity and health.debt_to_equity < 50:
            strengths.append("Faible endettement")

        if valuation.upside_potential < -10:
            weaknesses.append(f"Potentiellement surévalué: {valuation.upside_potential:.0f}%")
        if health.debt_to_equity and health.debt_to_equity > 150:
            weaknesses.append(f"Endettement élevé: {health.debt_to_equity:.0f}%")
        if growth.growth_score < 40:
            weaknesses.append("Croissance faible")

        # Confiance
        data_points = sum(1 for c in score_components if c.score != 50)
        confidence = "high" if data_points >= 5 else "medium" if data_points >= 3 else "low"

        # Générer résumé
        summary = self._generate_summary(name, global_score, verdict, valuation, growth, dividend)
        ai_recommendation = self._generate_ai_recommendation(
            name, ticker, current_price, global_score, verdict,
            valuation, growth, dividend, health, strengths, weaknesses
        )

        return ComprehensiveAnalysis(
            ticker=ticker,
            name=name,
            sector=sector,
            industry=industry,
            currency=currency,
            current_price=current_price,
            price_change_1d=price_change_1d,
            price_change_1y=price_change_1y,
            high_52w=high_52w,
            low_52w=low_52w,
            market_cap=market_cap,
            market_cap_category=cap_category,
            beta=beta,
            volatility_level=volatility,
            valuation=valuation,
            growth=growth,
            dividend=dividend,
            health=health,
            score_components=score_components,
            global_score=global_score,
            star_rating=stars,
            verdict=verdict,
            confidence=confidence,
            strengths=strengths,
            weaknesses=weaknesses,
            summary=summary,
            ai_recommendation=ai_recommendation,
            data_quality="complete" if confidence == "high" else "partial"
        )

    def _analyze_valuation(self, ticker: str, price: float, fund, sector: str) -> ValuationAnalysis:
        """Analyse la valorisation."""
        pe = fund.pe_ratio if fund else None
        forward_pe = fund.forward_pe if fund else None
        peg = fund.peg_ratio if fund else None
        pb = fund.pb_ratio if fund else None
        ps = fund.ps_ratio if fund else None
        ev_ebitda = fund.ev_ebitda if fund else None

        # FCF Yield
        fcf_yield = None
        if fund and fund.free_cash_flow and fund.free_cash_flow > 0:
            info = self.yahoo.get_stock_info(ticker)
            if info and info.market_cap:
                fcf_yield = (fund.free_cash_flow / info.market_cap) * 100

        # P/E sectoriel
        sector_pe = self.SECTOR_PE.get(sector, self.SECTOR_PE['default'])

        # Fair values
        fair_pe = None
        if fund and fund.eps and fund.eps > 0:
            fair_pe = fund.eps * sector_pe

        fair_dcf = None
        if fcf_yield and fcf_yield > 0:
            # Prix pour FCF yield de 5%
            fair_dcf = price * (fcf_yield / 5)

        fair_div = None
        if fund and fund.dividend_yield and fund.dividend_yield > 0:
            div_per_share = price * (fund.dividend_yield / 100)
            fair_div = div_per_share / 0.05  # Target 5%

        # Calculer upside moyen
        fair_values = [v for v in [fair_pe, fair_dcf, fair_div] if v]
        if fair_values:
            avg_fair = sum(fair_values) / len(fair_values)
            upside = ((avg_fair / price) - 1) * 100
        else:
            upside = 0

        # Score valorisation
        score = 50
        signal = "fair"

        if pe:
            pe_ratio_to_sector = pe / sector_pe
            if pe_ratio_to_sector < 0.7:
                score += 25
                signal = "undervalued"
            elif pe_ratio_to_sector < 1.0:
                score += 10
                signal = "undervalued"
            elif pe_ratio_to_sector > 1.5:
                score -= 20
                signal = "overvalued"
            elif pe_ratio_to_sector > 1.2:
                score -= 10
                signal = "overvalued"

        if pb:
            if pb < 1.0:
                score += 15
                if signal != "undervalued":
                    signal = "undervalued"
            elif pb > 3.0:
                score -= 10

        if upside > 20:
            score += 10
        elif upside < -20:
            score -= 15

        score = max(0, min(100, score))

        return ValuationAnalysis(
            pe_ratio=pe,
            pe_5y_avg=None,
            forward_pe=forward_pe,
            peg_ratio=peg,
            pb_ratio=pb,
            ps_ratio=ps,
            ev_ebitda=ev_ebitda,
            fcf_yield=fcf_yield,
            fair_value_pe=fair_pe,
            fair_value_dcf=fair_dcf,
            fair_value_dividend=fair_div,
            upside_potential=upside,
            valuation_score=score,
            valuation_signal=signal
        )

    def _analyze_growth(self, fund, history) -> GrowthAnalysis:
        """Analyse la croissance."""
        rev_growth_1y = fund.revenue_growth * 100 if fund and fund.revenue_growth else None
        earn_growth_1y = fund.earnings_growth * 100 if fund and fund.earnings_growth else None

        # Estimations 5 ans (simplifiées)
        rev_growth_5y = rev_growth_1y  # Pas de données historiques
        earn_growth_5y = earn_growth_1y

        # Score croissance
        score = 50

        if rev_growth_1y:
            if rev_growth_1y > 15:
                score += 20
            elif rev_growth_1y > 5:
                score += 10
            elif rev_growth_1y < 0:
                score -= 15

        if earn_growth_1y:
            if earn_growth_1y > 20:
                score += 20
            elif earn_growth_1y > 10:
                score += 10
            elif earn_growth_1y < 0:
                score -= 15

        score = max(0, min(100, score))

        # Consistance
        if rev_growth_1y and earn_growth_1y:
            if rev_growth_1y > 0 and earn_growth_1y > 0:
                consistency = "stable"
            elif rev_growth_1y < 0 and earn_growth_1y < 0:
                consistency = "declining"
            else:
                consistency = "volatile"
        else:
            consistency = "unknown"

        return GrowthAnalysis(
            revenue_growth_1y=rev_growth_1y,
            revenue_growth_5y=rev_growth_5y,
            earnings_growth_1y=earn_growth_1y,
            earnings_growth_5y=earn_growth_5y,
            fcf_growth_5y=None,
            growth_score=score,
            growth_consistency=consistency
        )

    def _analyze_dividend(self, price: float, fund) -> DividendAnalysis:
        """Analyse le dividende."""
        div_yield = fund.dividend_yield if fund else None
        payout = fund.dividend_payout_ratio * 100 if fund and fund.dividend_payout_ratio else None

        # Calcul sécurité dividende
        safety_score = 50

        if not div_yield or div_yield == 0:
            safety_score = 30  # Pas de dividende
        else:
            # Yield attractif
            if div_yield > 6:
                safety_score += 15  # Mais attention durabilité
            elif div_yield > 4:
                safety_score += 20
            elif div_yield > 2:
                safety_score += 10

            # Payout ratio
            if payout:
                if payout < 50:
                    safety_score += 15  # Très sûr
                elif payout < 70:
                    safety_score += 5
                elif payout > 90:
                    safety_score -= 20  # Risqué

        safety_score = max(0, min(100, safety_score))

        # Montant annuel
        annual_amount = None
        if div_yield and price:
            annual_amount = price * (div_yield / 100)

        return DividendAnalysis(
            yield_current=div_yield,
            yield_5y_avg=None,
            payout_ratio=payout,
            growth_5y=None,
            years_of_growth=0,
            safety_score=safety_score,
            is_dividend_king=False,
            is_dividend_aristocrat=False,
            next_ex_date=None,
            annual_amount=annual_amount
        )

    def _analyze_health(self, fund) -> HealthAnalysis:
        """Analyse la santé financière."""
        current_ratio = fund.current_ratio if fund else None
        quick_ratio = fund.quick_ratio if fund else None
        debt_equity = fund.debt_to_equity if fund else None
        roe = fund.roe if fund else None
        roa = fund.roa if fund else None
        margin = fund.profit_margin if fund else None

        score = 50

        # ROE
        if roe:
            if roe > 0.20:
                score += 20
            elif roe > 0.15:
                score += 10
            elif roe < 0.05:
                score -= 15

        # Dette
        if debt_equity:
            if debt_equity < 50:
                score += 15
            elif debt_equity < 100:
                score += 5
            elif debt_equity > 200:
                score -= 20

        # Marge
        if margin:
            if margin > 0.20:
                score += 10
            elif margin > 0.10:
                score += 5
            elif margin < 0:
                score -= 15

        score = max(0, min(100, score))

        return HealthAnalysis(
            current_ratio=current_ratio,
            quick_ratio=quick_ratio,
            debt_to_equity=debt_equity,
            interest_coverage=None,
            roe=roe,
            roa=roa,
            profit_margin=margin,
            health_score=score
        )

    def _pe_score(self, pe: Optional[float], sector: str) -> float:
        """Score basé sur P/E vs secteur."""
        if not pe:
            return 50
        sector_pe = self.SECTOR_PE.get(sector, self.SECTOR_PE['default'])
        ratio = pe / sector_pe
        if ratio < 0.7:
            return 90
        elif ratio < 1.0:
            return 70
        elif ratio < 1.3:
            return 50
        else:
            return 30

    def _pb_score(self, pb: Optional[float]) -> float:
        """Score basé sur P/B."""
        if not pb:
            return 50
        if pb < 1.0:
            return 80
        elif pb < 2.0:
            return 60
        elif pb < 3.0:
            return 40
        else:
            return 20

    def _generate_summary(self, name: str, score: float, verdict: Verdict,
                          valuation: ValuationAnalysis, growth: GrowthAnalysis,
                          dividend: DividendAnalysis) -> str:
        """Génère un résumé court."""
        parts = [f"{name}: Score {score:.0f}/100 - {verdict.value}"]

        if valuation.valuation_signal == "undervalued":
            parts.append("Valorisation attractive")
        elif valuation.valuation_signal == "overvalued":
            parts.append("Valorisation élevée")

        if growth.growth_score >= 60:
            parts.append("bonne croissance")

        if dividend.yield_current and dividend.yield_current > 3:
            parts.append(f"dividende {dividend.yield_current:.1f}%")

        return ". ".join(parts) + "."

    def _generate_ai_recommendation(self, name: str, ticker: str, price: float,
                                    score: float, verdict: Verdict,
                                    valuation: ValuationAnalysis,
                                    growth: GrowthAnalysis,
                                    dividend: DividendAnalysis,
                                    health: HealthAnalysis,
                                    strengths: list,
                                    weaknesses: list) -> str:
        """Génère une recommandation style IA."""

        lines = []
        lines.append(f"ANALYSE {name.upper()} ({ticker})")
        lines.append("=" * 50)
        lines.append("")

        # Verdict principal
        stars = "★" * int(score / 20) + "☆" * (5 - int(score / 20))
        lines.append(f"VERDICT: {verdict.value} {stars} ({score:.0f}/100)")
        lines.append("")

        # Valorisation
        lines.append("VALORISATION:")
        if valuation.pe_ratio:
            lines.append(f"  - P/E: {valuation.pe_ratio:.1f}x ({valuation.valuation_signal})")
        if valuation.pb_ratio:
            status = "< valeur comptable" if valuation.pb_ratio < 1 else "prime sur actifs"
            lines.append(f"  - P/B: {valuation.pb_ratio:.2f}x ({status})")
        if valuation.upside_potential != 0:
            lines.append(f"  - Potentiel: {valuation.upside_potential:+.0f}%")
        lines.append("")

        # Croissance
        lines.append("CROISSANCE:")
        if growth.revenue_growth_1y:
            lines.append(f"  - Chiffre d'affaires: {growth.revenue_growth_1y:+.1f}%")
        if growth.earnings_growth_1y:
            lines.append(f"  - Bénéfices: {growth.earnings_growth_1y:+.1f}%")
        lines.append(f"  - Tendance: {growth.growth_consistency}")
        lines.append("")

        # Dividende
        lines.append("DIVIDENDE:")
        if dividend.yield_current and dividend.yield_current > 0:
            lines.append(f"  - Rendement: {dividend.yield_current:.2f}%")
            if dividend.payout_ratio:
                safety = "sûr" if dividend.payout_ratio < 60 else "élevé" if dividend.payout_ratio > 80 else "modéré"
                lines.append(f"  - Payout ratio: {dividend.payout_ratio:.0f}% ({safety})")
            if dividend.annual_amount:
                lines.append(f"  - Montant/action: {dividend.annual_amount:.2f} EUR/an")
        else:
            lines.append("  - Pas de dividende")
        lines.append("")

        # Santé
        lines.append("SANTE FINANCIERE:")
        if health.roe:
            quality = "excellent" if health.roe > 0.15 else "correct" if health.roe > 0.08 else "faible"
            lines.append(f"  - ROE: {health.roe*100:.1f}% ({quality})")
        if health.debt_to_equity:
            level = "faible" if health.debt_to_equity < 50 else "modéré" if health.debt_to_equity < 100 else "élevé"
            lines.append(f"  - Dette/Equity: {health.debt_to_equity:.0f}% ({level})")
        lines.append("")

        # Forces & Faiblesses
        if strengths:
            lines.append("POINTS FORTS:")
            for s in strengths[:3]:
                lines.append(f"  + {s}")
            lines.append("")

        if weaknesses:
            lines.append("POINTS FAIBLES:")
            for w in weaknesses[:3]:
                lines.append(f"  - {w}")
            lines.append("")

        # Recommandation finale
        lines.append("RECOMMANDATION:")
        if verdict in [Verdict.STRONG_BUY, Verdict.BUY]:
            if valuation.valuation_signal == "undervalued":
                lines.append(f"  L'action semble sous-évaluée. Bon point d'entrée autour de {price:.2f} EUR.")
            else:
                lines.append(f"  Action de qualité avec de bons fondamentaux.")

            if dividend.yield_current and dividend.yield_current > 3:
                lines.append(f"  Le dividende de {dividend.yield_current:.1f}% apporte un revenu régulier.")
        elif verdict == Verdict.HOLD:
            lines.append("  Conserver si déjà en portefeuille. Attendre un meilleur point d'entrée pour acheter.")
        else:
            lines.append("  Prudence recommandée. Considérer d'autres opportunités.")

        return "\n".join(lines)


def print_analysis(analysis: ComprehensiveAnalysis):
    """Affiche l'analyse de manière formatée."""
    print(analysis.ai_recommendation)


# Test
if __name__ == "__main__":
    analyzer = ComprehensiveAnalyzer()

    # Test sur Crédit Agricole
    print("Analyse en cours...")
    result = analyzer.analyze("ACA.PA")

    if result:
        print_analysis(result)
