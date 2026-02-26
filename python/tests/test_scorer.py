"""
Tests pour le module Global Scorer.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.scorer import (
    GlobalScorer, GlobalAnalysis, ScoreBreakdown, Recommendation
)


class TestScoreBreakdown:
    """Tests pour ScoreBreakdown."""

    def test_create_breakdown(self):
        """Test creation breakdown."""
        breakdown = ScoreBreakdown(
            technical_score=70,
            fundamental_score=65,
            sentiment_score=80,
            smart_money_score=75
        )

        assert breakdown.technical_score == 70
        assert breakdown.fundamental_score == 65

    def test_weighted_scores(self):
        """Test calcul scores ponderes."""
        breakdown = ScoreBreakdown(
            technical_score=80,
            technical_weight=0.25,
            fundamental_score=60,
            fundamental_weight=0.25,
            sentiment_score=70,
            sentiment_weight=0.25,
            smart_money_score=90,
            smart_money_weight=0.25
        )

        assert breakdown.weighted_technical == 20.0
        assert breakdown.weighted_fundamental == 15.0
        assert breakdown.weighted_sentiment == 17.5
        assert breakdown.weighted_smart_money == 22.5

    def test_total_score(self):
        """Test calcul score total."""
        breakdown = ScoreBreakdown(
            technical_score=80,
            technical_weight=0.25,
            fundamental_score=60,
            fundamental_weight=0.25,
            sentiment_score=70,
            sentiment_weight=0.25,
            smart_money_score=90,
            smart_money_weight=0.25
        )

        # 20 + 15 + 17.5 + 22.5 = 75
        assert breakdown.total_score == 75.0


class TestRecommendation:
    """Tests pour l'enum Recommendation."""

    def test_recommendation_values(self):
        """Test valeurs de l'enum."""
        assert Recommendation.STRONG_BUY.value == "strong_buy"
        assert Recommendation.BUY.value == "buy"
        assert Recommendation.HOLD.value == "hold"
        assert Recommendation.SELL.value == "sell"
        assert Recommendation.STRONG_SELL.value == "strong_sell"


class TestGlobalScorer:
    """Tests pour GlobalScorer."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scorer = GlobalScorer()

    def test_default_weights(self):
        """Test poids par defaut."""
        assert self.scorer.technical_weight == 0.25
        assert self.scorer.fundamental_weight == 0.25
        assert self.scorer.sentiment_weight == 0.25
        assert self.scorer.smart_money_weight == 0.25

    def test_custom_weights(self):
        """Test poids personnalises."""
        scorer = GlobalScorer(
            technical_weight=0.4,
            fundamental_weight=0.3,
            sentiment_weight=0.2,
            smart_money_weight=0.1
        )

        assert scorer.technical_weight == 0.4
        assert scorer.fundamental_weight == 0.3

    def test_weights_normalization(self):
        """Test normalisation des poids."""
        # Poids qui ne somment pas a 1
        scorer = GlobalScorer(
            technical_weight=0.5,
            fundamental_weight=0.5,
            sentiment_weight=0.5,
            smart_money_weight=0.5
        )

        total = (scorer.technical_weight + scorer.fundamental_weight +
                 scorer.sentiment_weight + scorer.smart_money_weight)

        assert abs(total - 1.0) < 0.001

    def test_calculate_all_scores_present(self):
        """Test calcul avec tous les scores."""
        analysis = self.scorer.calculate_global_score(
            ticker="AAPL",
            company_name="Apple Inc.",
            technical_score=80,
            fundamental_score=70,
            sentiment_score=75,
            smart_money_score=85
        )

        assert analysis.ticker == "AAPL"
        assert analysis.company_name == "Apple Inc."
        # (80+70+75+85) / 4 = 77.5
        assert analysis.score == 77.5

    def test_calculate_missing_scores(self):
        """Test calcul avec scores manquants."""
        analysis = self.scorer.calculate_global_score(
            ticker="AAPL",
            company_name="Apple Inc.",
            technical_score=80,
            fundamental_score=70,
            sentiment_score=None,  # Manquant
            smart_money_score=None  # Manquant
        )

        # Scores manquants = 50 par defaut, poids redistribues
        assert analysis.score is not None

    def test_recommendation_strong_buy(self):
        """Test recommandation strong_buy."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=85,
            fundamental_score=80,
            sentiment_score=90,
            smart_money_score=85
        )

        assert analysis.recommendation == Recommendation.STRONG_BUY

    def test_recommendation_buy(self):
        """Test recommandation buy."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=65,
            fundamental_score=60,
            sentiment_score=70,
            smart_money_score=65
        )

        assert analysis.recommendation == Recommendation.BUY

    def test_recommendation_hold(self):
        """Test recommandation hold."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=50,
            fundamental_score=45,
            sentiment_score=55,
            smart_money_score=50
        )

        assert analysis.recommendation == Recommendation.HOLD

    def test_recommendation_sell(self):
        """Test recommandation sell."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=30,
            fundamental_score=25,
            sentiment_score=35,
            smart_money_score=30
        )

        assert analysis.recommendation == Recommendation.SELL

    def test_recommendation_strong_sell(self):
        """Test recommandation strong_sell."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=15,
            fundamental_score=10,
            sentiment_score=20,
            smart_money_score=15
        )

        assert analysis.recommendation == Recommendation.STRONG_SELL

    def test_confidence_high(self):
        """Test confiance elevee."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=75,
            fundamental_score=78,
            sentiment_score=72,
            smart_money_score=76
        )

        # Tous les scores coherents, 4 analyses
        assert analysis.confidence == "high"

    def test_confidence_low_few_analyses(self):
        """Test confiance faible avec peu d'analyses."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=70,
            fundamental_score=None,
            sentiment_score=None,
            smart_money_score=None
        )

        assert analysis.confidence == "low"

    def test_strengths_identification(self):
        """Test identification des forces."""
        analysis = self.scorer.calculate_global_score(
            ticker="TEST",
            company_name="Test",
            technical_score=85,  # Force
            fundamental_score=75,  # Force
            sentiment_score=30,  # Faiblesse
            smart_money_score=25  # Faiblesse
        )

        assert len(analysis.strengths) >= 2
        assert len(analysis.weaknesses) >= 2

    def test_summary_generation(self):
        """Test generation du resume."""
        analysis = self.scorer.calculate_global_score(
            ticker="AAPL",
            company_name="Apple Inc.",
            technical_score=70,
            fundamental_score=65,
            sentiment_score=75,
            smart_money_score=70
        )

        assert "AAPL" in analysis.summary
        assert "Score" in analysis.summary or "score" in analysis.summary.lower()


class TestWeightAdjustment:
    """Tests pour l'ajustement des poids."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scorer = GlobalScorer()

    def test_adjust_weights_all_present(self):
        """Test ajustement avec toutes analyses presentes."""
        weights = self.scorer._adjust_weights(70, 65, 80, 75)

        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001

    def test_adjust_weights_one_missing(self):
        """Test ajustement avec une analyse manquante."""
        weights = self.scorer._adjust_weights(70, 65, None, 75)

        assert weights['sentiment'] == 0.0
        # Le poids manquant est redistribue
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.001

    def test_adjust_weights_two_missing(self):
        """Test ajustement avec deux analyses manquantes."""
        weights = self.scorer._adjust_weights(70, 65, None, None)

        assert weights['sentiment'] == 0.0
        assert weights['smart_money'] == 0.0
        # Les deux analyses restantes se partagent le poids
        assert weights['technical'] == 0.5
        assert weights['fundamental'] == 0.5

    def test_adjust_weights_all_missing(self):
        """Test ajustement sans aucune analyse."""
        weights = self.scorer._adjust_weights(None, None, None, None)

        # Poids egaux par defaut
        for w in weights.values():
            assert w == 0.25


class TestGlobalAnalysis:
    """Tests pour la structure GlobalAnalysis."""

    def test_create_analysis(self):
        """Test creation analyse globale."""
        breakdown = ScoreBreakdown(
            technical_score=70,
            fundamental_score=65,
            sentiment_score=75,
            smart_money_score=70
        )

        analysis = GlobalAnalysis(
            ticker="AAPL",
            company_name="Apple Inc.",
            score=70.0,
            breakdown=breakdown,
            recommendation=Recommendation.BUY,
            confidence="high",
            strengths=["Technique positive"],
            weaknesses=["Fondamental moyen"],
            summary="Test summary"
        )

        assert analysis.ticker == "AAPL"
        assert analysis.score == 70.0
        assert analysis.recommendation == Recommendation.BUY

    def test_analysis_with_details(self):
        """Test analyse avec details."""
        breakdown = ScoreBreakdown()

        analysis = GlobalAnalysis(
            ticker="AAPL",
            company_name="Apple Inc.",
            score=70.0,
            breakdown=breakdown,
            recommendation=Recommendation.BUY,
            confidence="medium",
            technical_analysis={"score": 70},  # Mock object
            fundamental_analysis={"score": 65}  # Mock object
        )

        assert analysis.technical_analysis is not None
        assert analysis.fundamental_analysis is not None
