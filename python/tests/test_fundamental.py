"""
Tests pour le module d'analyse fondamentale.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.fundamental import (
    FundamentalAnalyzer, FundamentalAnalysis, FundamentalSignal
)


class TestFundamentalAnalyzer:
    """Tests pour la classe FundamentalAnalyzer."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        self.analyzer = FundamentalAnalyzer()

    # Tests d'analyse complète

    def test_analyze_good_company(self, sample_fundamentals_good):
        """Test d'analyse d'une bonne entreprise."""
        analysis = self.analyzer.analyze(
            sample_fundamentals_good, "GOOD", "Technology"
        )

        assert analysis is not None
        assert isinstance(analysis, FundamentalAnalysis)
        assert analysis.ticker == "GOOD"
        assert 0 <= analysis.score <= 100
        # Une bonne entreprise devrait avoir un score > 50
        assert analysis.score > 50
        assert analysis.quality in ["high", "medium"]

    def test_analyze_poor_company(self, sample_fundamentals_poor):
        """Test d'analyse d'une entreprise en difficulté."""
        analysis = self.analyzer.analyze(
            sample_fundamentals_poor, "POOR", "Technology"
        )

        assert analysis is not None
        # Une entreprise en difficulté devrait avoir un score < 50
        assert analysis.score < 50
        assert analysis.valuation == "overvalued"
        assert analysis.growth in ["low", "negative"]

    def test_analyze_mixed_company(self, sample_fundamentals_mixed):
        """Test d'analyse d'une entreprise mixte."""
        analysis = self.analyzer.analyze(
            sample_fundamentals_mixed, "MIX", "Technology"
        )

        assert analysis is not None
        # Score devrait être autour de 50
        assert 30 <= analysis.score <= 70

    def test_analyze_without_sector(self, sample_fundamentals_good):
        """Test d'analyse sans secteur spécifié."""
        analysis = self.analyzer.analyze(
            sample_fundamentals_good, "TEST", None
        )

        assert analysis is not None

    def test_analyze_empty_fundamentals(self):
        """Test avec des données vides."""
        analysis = self.analyzer.analyze({}, "EMPTY", None)

        # Devrait retourner une analyse avec des signaux neutres
        assert analysis is not None

    def test_analyze_partial_fundamentals(self):
        """Test avec des données partielles."""
        partial_data = {
            "pe_ratio": 20.0,
            "roe": 0.15
        }

        analysis = self.analyzer.analyze(partial_data, "PARTIAL", None)

        assert analysis is not None

    # Tests des signaux individuels

    def test_analyze_pe_bullish(self):
        """Test P/E attractif."""
        # PE de 8 est en-dessous du seuil par défaut de 10
        signal = self.analyzer._analyze_pe(8.0, None)

        assert signal.signal == "bullish"
        assert signal.name == "pe_ratio"

    def test_analyze_pe_bearish(self):
        """Test P/E élevé."""
        signal = self.analyzer._analyze_pe(40.0, None)

        assert signal.signal == "bearish"

    def test_analyze_pe_negative(self):
        """Test P/E négatif (entreprise non rentable)."""
        signal = self.analyzer._analyze_pe(-5.0, None)

        assert signal.signal == "neutral"

    def test_analyze_pe_none(self):
        """Test P/E non disponible."""
        signal = self.analyzer._analyze_pe(None, None)

        assert signal.signal == "neutral"
        assert signal.value is None

    def test_analyze_peg_bullish(self):
        """Test PEG attractif."""
        signal = self.analyzer._analyze_peg(0.8, None)

        assert signal.signal == "bullish"

    def test_analyze_peg_bearish(self):
        """Test PEG élevé."""
        signal = self.analyzer._analyze_peg(3.0, None)

        assert signal.signal == "bearish"

    def test_analyze_roe_bullish(self):
        """Test ROE excellent."""
        signal = self.analyzer._analyze_roe(0.25, None)  # 25%

        assert signal.signal == "bullish"

    def test_analyze_roe_bearish(self):
        """Test ROE faible."""
        signal = self.analyzer._analyze_roe(0.03, None)  # 3%

        assert signal.signal == "bearish"

    def test_analyze_debt_bullish(self):
        """Test dette faible."""
        signal = self.analyzer._analyze_debt(0.2, None)

        assert signal.signal == "bullish"

    def test_analyze_debt_bearish(self):
        """Test dette élevée."""
        signal = self.analyzer._analyze_debt(2.5, None)

        assert signal.signal == "bearish"

    def test_analyze_dividend_with_yield(self):
        """Test rendement dividende."""
        signal = self.analyzer._analyze_dividend(0.035, None)  # 3.5%

        assert signal.signal in ["bullish", "neutral"]
        assert signal.value > 0

    def test_analyze_dividend_too_high(self):
        """Test rendement dividende trop élevé (risque de coupe)."""
        signal = self.analyzer._analyze_dividend(0.12, None)  # 12%

        assert signal.signal == "bearish"

    def test_analyze_dividend_none(self):
        """Test pas de dividende."""
        signal = self.analyzer._analyze_dividend(None, None)

        assert signal.signal == "neutral"

    # Tests des seuils par secteur

    def test_sector_adjustments_technology(self):
        """Test des seuils ajustés pour la technologie."""
        thresholds = self.analyzer.get_thresholds("pe_ratio", "Technology")

        # La tech a des seuils P/E plus élevés
        assert thresholds["high"] > self.analyzer.default_thresholds["pe_ratio"]["high"]

    def test_sector_adjustments_financials(self):
        """Test des seuils ajustés pour la finance."""
        thresholds = self.analyzer.get_thresholds("pe_ratio", "Financials")

        # La finance a des seuils P/E plus bas
        assert thresholds["high"] < self.analyzer.default_thresholds["pe_ratio"]["high"]

    def test_sector_adjustments_unknown(self):
        """Test avec secteur inconnu (utilise les défauts)."""
        thresholds = self.analyzer.get_thresholds("pe_ratio", "Unknown Sector")

        assert thresholds == self.analyzer.default_thresholds["pe_ratio"]

    # Tests des évaluations qualitatives

    def test_assess_valuation_undervalued(self):
        """Test évaluation sous-valorisée."""
        signals = [
            FundamentalSignal("pe_ratio", 10.0, "bullish", 0.1, "Test"),
            FundamentalSignal("peg_ratio", 0.5, "bullish", 0.1, "Test"),
            FundamentalSignal("pb_ratio", 0.8, "bullish", 0.1, "Test"),
            FundamentalSignal("ev_ebitda", 5.0, "bullish", 0.1, "Test"),
        ]

        valuation = self.analyzer._assess_valuation(signals)
        assert valuation == "undervalued"

    def test_assess_valuation_overvalued(self):
        """Test évaluation sur-valorisée."""
        signals = [
            FundamentalSignal("pe_ratio", 50.0, "bearish", 0.1, "Test"),
            FundamentalSignal("peg_ratio", 4.0, "bearish", 0.1, "Test"),
            FundamentalSignal("pb_ratio", 10.0, "bearish", 0.1, "Test"),
            FundamentalSignal("ev_ebitda", 30.0, "bearish", 0.1, "Test"),
        ]

        valuation = self.analyzer._assess_valuation(signals)
        assert valuation == "overvalued"

    def test_assess_quality_high(self):
        """Test qualité élevée."""
        signals = [
            FundamentalSignal("roe", 25.0, "bullish", 0.1, "Test"),
            FundamentalSignal("profit_margin", 20.0, "bullish", 0.1, "Test"),
            FundamentalSignal("roa", 15.0, "bullish", 0.1, "Test"),
        ]

        quality = self.analyzer._assess_quality(signals)
        assert quality == "high"

    def test_assess_growth_high(self):
        """Test croissance élevée."""
        signals = [
            FundamentalSignal("revenue_growth", 25.0, "bullish", 0.1, "Test"),
            FundamentalSignal("earnings_growth", 30.0, "bullish", 0.1, "Test"),
        ]

        growth = self.analyzer._assess_growth(signals)
        assert growth == "high"

    def test_assess_growth_negative(self):
        """Test croissance négative."""
        signals = [
            FundamentalSignal("revenue_growth", -10.0, "bearish", 0.1, "Test"),
            FundamentalSignal("earnings_growth", -15.0, "bearish", 0.1, "Test"),
        ]

        growth = self.analyzer._assess_growth(signals)
        assert growth == "negative"

    def test_assess_financial_health_strong(self):
        """Test santé financière forte."""
        signals = [
            FundamentalSignal("debt_to_equity", 0.2, "bullish", 0.1, "Test"),
            FundamentalSignal("current_ratio", 2.5, "bullish", 0.1, "Test"),
        ]

        health = self.analyzer._assess_financial_health(signals)
        assert health == "strong"

    def test_assess_financial_health_weak(self):
        """Test santé financière faible."""
        signals = [
            FundamentalSignal("debt_to_equity", 3.0, "bearish", 0.1, "Test"),
            FundamentalSignal("current_ratio", 0.5, "bearish", 0.1, "Test"),
        ]

        health = self.analyzer._assess_financial_health(signals)
        assert health == "weak"

    # Tests des poids

    def test_weights_sum_to_one(self):
        """Test que les poids somment à 1."""
        total = sum(self.analyzer.weights.values())
        assert abs(total - 1.0) < 0.001


class TestFundamentalSignal:
    """Tests pour la structure FundamentalSignal."""

    def test_signal_creation(self):
        """Test de création d'un signal."""
        signal = FundamentalSignal(
            name="test",
            value=10.0,
            signal="bullish",
            weight=0.1,
            description="Test description"
        )

        assert signal.name == "test"
        assert signal.value == 10.0
        assert signal.signal == "bullish"
        assert signal.weight == 0.1
        assert signal.description == "Test description"

    def test_signal_with_thresholds(self):
        """Test de création d'un signal avec seuils."""
        signal = FundamentalSignal(
            name="test",
            value=10.0,
            signal="bullish",
            weight=0.1,
            description="Test",
            threshold_low=5.0,
            threshold_high=15.0
        )

        assert signal.threshold_low == 5.0
        assert signal.threshold_high == 15.0
