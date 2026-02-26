"""
Global Scorer - Calcul du score global combinant les 4 analyses.

Ce module combine:
- Analyse Technique (25%)
- Analyse Fondamentale (25%)
- Analyse Sentiment (25%)
- Analyse Smart Money (25%)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Recommendation(Enum):
    """Recommandation d'investissement."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


@dataclass
class ScoreBreakdown:
    """Detail des scores par composante."""
    technical_score: float = 0.0
    technical_weight: float = 0.25
    fundamental_score: float = 0.0
    fundamental_weight: float = 0.25
    sentiment_score: float = 0.0
    sentiment_weight: float = 0.25
    smart_money_score: float = 0.0
    smart_money_weight: float = 0.25

    @property
    def weighted_technical(self) -> float:
        return self.technical_score * self.technical_weight

    @property
    def weighted_fundamental(self) -> float:
        return self.fundamental_score * self.fundamental_weight

    @property
    def weighted_sentiment(self) -> float:
        return self.sentiment_score * self.sentiment_weight

    @property
    def weighted_smart_money(self) -> float:
        return self.smart_money_score * self.smart_money_weight

    @property
    def total_score(self) -> float:
        return (
            self.weighted_technical +
            self.weighted_fundamental +
            self.weighted_sentiment +
            self.weighted_smart_money
        )


@dataclass
class GlobalAnalysis:
    """Resultat de l'analyse globale d'une action."""
    ticker: str
    company_name: str
    score: float  # Score global 0-100
    breakdown: ScoreBreakdown
    recommendation: Recommendation
    confidence: str  # "high", "medium", "low"
    strengths: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    summary: str = ""
    analysis_date: datetime = field(default_factory=datetime.now)

    # Details des analyses individuelles (optionnel)
    technical_analysis: Optional[object] = None
    fundamental_analysis: Optional[object] = None
    sentiment_analysis: Optional[object] = None
    smart_money_analysis: Optional[object] = None


class GlobalScorer:
    """
    Calculateur de score global combinant les 4 types d'analyse.
    """

    def __init__(
        self,
        technical_weight: float = 0.25,
        fundamental_weight: float = 0.25,
        sentiment_weight: float = 0.25,
        smart_money_weight: float = 0.25
    ):
        """
        Initialise le scorer avec les ponderations.

        Les poids doivent sommer a 1.0.
        """
        total = technical_weight + fundamental_weight + sentiment_weight + smart_money_weight
        if abs(total - 1.0) > 0.001:
            logger.warning(f"Les poids ne somment pas a 1.0 ({total}), normalisation...")
            technical_weight /= total
            fundamental_weight /= total
            sentiment_weight /= total
            smart_money_weight /= total

        self.technical_weight = technical_weight
        self.fundamental_weight = fundamental_weight
        self.sentiment_weight = sentiment_weight
        self.smart_money_weight = smart_money_weight

    def calculate_global_score(
        self,
        ticker: str,
        company_name: str,
        technical_score: Optional[float] = None,
        fundamental_score: Optional[float] = None,
        sentiment_score: Optional[float] = None,
        smart_money_score: Optional[float] = None,
        technical_analysis: Optional[object] = None,
        fundamental_analysis: Optional[object] = None,
        sentiment_analysis: Optional[object] = None,
        smart_money_analysis: Optional[object] = None
    ) -> GlobalAnalysis:
        """
        Calcule le score global a partir des scores individuels.

        Args:
            ticker: Symbole de l'action
            company_name: Nom de l'entreprise
            technical_score: Score technique (0-100)
            fundamental_score: Score fondamental (0-100)
            sentiment_score: Score sentiment (0-100)
            smart_money_score: Score smart money (0-100)
            *_analysis: Objets d'analyse detailles (optionnel)

        Returns:
            GlobalAnalysis avec score global et recommandation
        """
        # Utiliser 50 (neutre) pour les scores manquants
        tech = technical_score if technical_score is not None else 50.0
        fund = fundamental_score if fundamental_score is not None else 50.0
        sent = sentiment_score if sentiment_score is not None else 50.0
        smart = smart_money_score if smart_money_score is not None else 50.0

        # Ajuster les poids si certaines analyses manquent
        weights = self._adjust_weights(
            technical_score, fundamental_score,
            sentiment_score, smart_money_score
        )

        # Creer le breakdown
        breakdown = ScoreBreakdown(
            technical_score=tech,
            technical_weight=weights['technical'],
            fundamental_score=fund,
            fundamental_weight=weights['fundamental'],
            sentiment_score=sent,
            sentiment_weight=weights['sentiment'],
            smart_money_score=smart,
            smart_money_weight=weights['smart_money']
        )

        # Score global
        global_score = breakdown.total_score

        # Determiner la recommandation
        recommendation = self._determine_recommendation(global_score, breakdown)

        # Determiner la confiance
        confidence = self._calculate_confidence(
            technical_score, fundamental_score,
            sentiment_score, smart_money_score
        )

        # Identifier forces et faiblesses
        strengths, weaknesses = self._identify_strengths_weaknesses(breakdown)

        # Generer le resume
        summary = self._generate_summary(
            ticker, global_score, recommendation, strengths, weaknesses
        )

        return GlobalAnalysis(
            ticker=ticker,
            company_name=company_name,
            score=global_score,
            breakdown=breakdown,
            recommendation=recommendation,
            confidence=confidence,
            strengths=strengths,
            weaknesses=weaknesses,
            summary=summary,
            technical_analysis=technical_analysis,
            fundamental_analysis=fundamental_analysis,
            sentiment_analysis=sentiment_analysis,
            smart_money_analysis=smart_money_analysis
        )

    def _adjust_weights(
        self,
        technical_score: Optional[float],
        fundamental_score: Optional[float],
        sentiment_score: Optional[float],
        smart_money_score: Optional[float]
    ) -> dict:
        """
        Ajuste les poids si certaines analyses sont manquantes.
        Redistribue le poids des analyses manquantes aux autres.
        """
        available = {
            'technical': (technical_score is not None, self.technical_weight),
            'fundamental': (fundamental_score is not None, self.fundamental_weight),
            'sentiment': (sentiment_score is not None, self.sentiment_weight),
            'smart_money': (smart_money_score is not None, self.smart_money_weight)
        }

        # Compter les analyses disponibles
        available_count = sum(1 for avail, _ in available.values() if avail)

        if available_count == 0:
            # Aucune analyse, poids egaux
            return {k: 0.25 for k in available.keys()}

        if available_count == 4:
            # Toutes disponibles, utiliser les poids normaux
            return {k: w for k, (_, w) in available.items()}

        # Redistribuer le poids des manquantes
        missing_weight = sum(w for avail, w in available.values() if not avail)
        bonus_per_available = missing_weight / available_count

        result = {}
        for key, (avail, weight) in available.items():
            if avail:
                result[key] = weight + bonus_per_available
            else:
                result[key] = 0.0

        return result

    def _determine_recommendation(
        self,
        score: float,
        breakdown: ScoreBreakdown
    ) -> Recommendation:
        """Determine la recommandation basee sur le score global."""
        # Seuils releves pour corriger le biais haussier
        if score >= 78:
            return Recommendation.STRONG_BUY
        elif score >= 62:
            return Recommendation.BUY
        elif score >= 42:
            return Recommendation.HOLD
        elif score >= 28:
            return Recommendation.SELL
        else:
            return Recommendation.STRONG_SELL

    def _calculate_confidence(
        self,
        technical_score: Optional[float],
        fundamental_score: Optional[float],
        sentiment_score: Optional[float],
        smart_money_score: Optional[float]
    ) -> str:
        """
        Calcule le niveau de confiance basé sur:
        - Nombre d'analyses disponibles
        - Coherence entre les analyses
        """
        scores = [s for s in [technical_score, fundamental_score,
                              sentiment_score, smart_money_score] if s is not None]

        if len(scores) < 2:
            return "low"

        # Calculer l'ecart-type pour mesurer la coherence
        if len(scores) >= 2:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std_dev = variance ** 0.5

            # Plus l'ecart-type est faible, plus les analyses sont coherentes
            if std_dev < 10 and len(scores) >= 3:
                return "high"
            elif std_dev < 20 or len(scores) >= 3:
                return "medium"

        return "low"

    def _identify_strengths_weaknesses(
        self,
        breakdown: ScoreBreakdown
    ) -> tuple:
        """Identifie les forces et faiblesses de l'action."""
        strengths = []
        weaknesses = []

        score_labels = {
            'technical': ('Analyse Technique', breakdown.technical_score),
            'fundamental': ('Analyse Fondamentale', breakdown.fundamental_score),
            'sentiment': ('Sentiment Marche', breakdown.sentiment_score),
            'smart_money': ('Smart Money', breakdown.smart_money_score)
        }

        for key, (label, score) in score_labels.items():
            if score >= 70:
                strengths.append(f"{label} positive ({score:.0f}/100)")
            elif score >= 60:
                strengths.append(f"{label} correcte ({score:.0f}/100)")
            elif score < 40:
                weaknesses.append(f"{label} faible ({score:.0f}/100)")
            elif score < 50:
                weaknesses.append(f"{label} moyenne ({score:.0f}/100)")

        return strengths, weaknesses

    def _generate_summary(
        self,
        ticker: str,
        score: float,
        recommendation: Recommendation,
        strengths: list,
        weaknesses: list
    ) -> str:
        """Genere un resume textuel de l'analyse."""
        rec_text = {
            Recommendation.STRONG_BUY: "Achat fort recommande",
            Recommendation.BUY: "Achat recommande",
            Recommendation.HOLD: "Conserver/Attendre",
            Recommendation.SELL: "Vente recommandee",
            Recommendation.STRONG_SELL: "Vente forte recommandee"
        }

        parts = [
            f"{ticker} - Score global: {score:.0f}/100",
            f"Recommandation: {rec_text[recommendation]}"
        ]

        if strengths:
            parts.append(f"Points forts: {', '.join(strengths[:2])}")

        if weaknesses:
            parts.append(f"Points faibles: {', '.join(weaknesses[:2])}")

        return ". ".join(parts) + "."


class FullStockAnalyzer:
    """
    Analyseur complet combinant toutes les sources d'analyse.
    """

    def __init__(self):
        from src.scrapers.yahoo_finance import YahooFinanceScraper
        from src.analysis.technical import TechnicalAnalyzer
        from src.analysis.fundamental import FundamentalAnalyzer
        from src.sentiment.analyzer import SentimentAnalyzer
        from src.smart_money.tracker import SmartMoneyTracker

        self.yahoo = YahooFinanceScraper()
        self.technical = TechnicalAnalyzer()
        self.fundamental = FundamentalAnalyzer()
        self.sentiment = SentimentAnalyzer()
        self.smart_money = SmartMoneyTracker()
        self.scorer = GlobalScorer()

    def analyze(
        self,
        ticker: str,
        include_sentiment: bool = True,
        include_smart_money: bool = True,
        use_llm: bool = False
    ) -> Optional[GlobalAnalysis]:
        """
        Effectue une analyse complete d'une action.

        Args:
            ticker: Symbole de l'action
            include_sentiment: Inclure l'analyse sentiment
            include_smart_money: Inclure l'analyse smart money
            use_llm: Utiliser le LLM pour le sentiment

        Returns:
            GlobalAnalysis ou None si erreur
        """
        logger.info(f"Analyse complete de {ticker}...")

        # Recuperer les donnees de base
        stock_info = self.yahoo.get_stock_info(ticker)
        if not stock_info:
            logger.error(f"Impossible de recuperer les infos pour {ticker}")
            return None

        company_name = stock_info.name or ticker

        # Recuperer l'historique des prix
        price_history = self.yahoo.get_price_history(ticker, period="2y")

        # Recuperer les fondamentaux
        fundamentals = self.yahoo.get_fundamentals(ticker)

        # Analyse Technique
        tech_analysis = None
        tech_score = None
        if price_history is not None and len(price_history) >= 200:
            tech_analysis = self.technical.analyze(price_history, ticker)
            if tech_analysis:
                tech_score = tech_analysis.score
                logger.info(f"  Technique: {tech_score:.1f}/100")

        # Analyse Fondamentale
        fund_analysis = None
        fund_score = None
        if fundamentals:
            fund_analysis = self.fundamental.analyze(ticker, fundamentals.__dict__)
            if fund_analysis:
                fund_score = fund_analysis.score
                logger.info(f"  Fondamentale: {fund_score:.1f}/100")

        # Analyse Sentiment (optionnelle)
        sent_analysis = None
        sent_score = None
        if include_sentiment:
            try:
                sent_analysis = self.sentiment.analyze(
                    ticker, company_name, use_llm=use_llm
                )
                if sent_analysis:
                    sent_score = sent_analysis.score
                    logger.info(f"  Sentiment: {sent_score:.1f}/100")
            except Exception as e:
                logger.warning(f"Erreur analyse sentiment: {e}")

        # Analyse Smart Money (optionnelle)
        smart_analysis = None
        smart_score = None
        if include_smart_money:
            try:
                smart_analysis = self.smart_money.analyze(ticker)
                if smart_analysis:
                    smart_score = smart_analysis.conviction_score
                    logger.info(f"  Smart Money: {smart_score:.1f}/100")
            except Exception as e:
                logger.warning(f"Erreur analyse smart money: {e}")

        # Calculer le score global
        global_analysis = self.scorer.calculate_global_score(
            ticker=ticker,
            company_name=company_name,
            technical_score=tech_score,
            fundamental_score=fund_score,
            sentiment_score=sent_score,
            smart_money_score=smart_score,
            technical_analysis=tech_analysis,
            fundamental_analysis=fund_analysis,
            sentiment_analysis=sent_analysis,
            smart_money_analysis=smart_analysis
        )

        logger.info(f"  Score Global: {global_analysis.score:.1f}/100")
        logger.info(f"  Recommandation: {global_analysis.recommendation.value}")

        return global_analysis


# Exemple d'utilisation
if __name__ == "__main__":
    # Test du scorer seul
    scorer = GlobalScorer()

    analysis = scorer.calculate_global_score(
        ticker="AAPL",
        company_name="Apple Inc.",
        technical_score=72,
        fundamental_score=65,
        sentiment_score=80,
        smart_money_score=85
    )

    print("=== Analyse Globale AAPL ===")
    print(f"Score: {analysis.score:.1f}/100")
    print(f"Recommandation: {analysis.recommendation.value}")
    print(f"Confiance: {analysis.confidence}")
    print(f"\nDetails:")
    print(f"  Technique: {analysis.breakdown.technical_score:.0f} x {analysis.breakdown.technical_weight:.0%} = {analysis.breakdown.weighted_technical:.1f}")
    print(f"  Fondamental: {analysis.breakdown.fundamental_score:.0f} x {analysis.breakdown.fundamental_weight:.0%} = {analysis.breakdown.weighted_fundamental:.1f}")
    print(f"  Sentiment: {analysis.breakdown.sentiment_score:.0f} x {analysis.breakdown.sentiment_weight:.0%} = {analysis.breakdown.weighted_sentiment:.1f}")
    print(f"  Smart Money: {analysis.breakdown.smart_money_score:.0f} x {analysis.breakdown.smart_money_weight:.0%} = {analysis.breakdown.weighted_smart_money:.1f}")
    print(f"\nForces: {analysis.strengths}")
    print(f"Faiblesses: {analysis.weaknesses}")
    print(f"\nResume: {analysis.summary}")
