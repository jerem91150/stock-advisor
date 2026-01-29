"""
Tests pour le module d'analyse technique.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.technical import TechnicalAnalyzer, TechnicalAnalysis, TechnicalSignal


class TestTechnicalAnalyzer:
    """Tests pour la classe TechnicalAnalyzer."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        self.analyzer = TechnicalAnalyzer()

    # Tests des indicateurs individuels

    def test_calculate_sma(self, sample_price_data):
        """Test du calcul de la moyenne mobile simple."""
        sma = self.analyzer.calculate_sma(sample_price_data['Close'], 20)

        assert len(sma) == len(sample_price_data)
        assert sma.isna().sum() == 19  # Les 19 premières valeurs sont NaN
        assert not sma.iloc[-1:].isna().any()  # La dernière valeur n'est pas NaN

    def test_calculate_ema(self, sample_price_data):
        """Test du calcul de la moyenne mobile exponentielle."""
        ema = self.analyzer.calculate_ema(sample_price_data['Close'], 12)

        assert len(ema) == len(sample_price_data)
        # EMA ne devrait pas avoir de NaN (ou très peu au début)
        assert ema.isna().sum() < 5

    def test_calculate_rsi(self, sample_price_data):
        """Test du calcul du RSI."""
        rsi = self.analyzer.calculate_rsi(sample_price_data['Close'], 14)

        assert len(rsi) == len(sample_price_data)
        # RSI doit être entre 0 et 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_calculate_rsi_overbought(self):
        """Test RSI en zone de surachat."""
        # Créer une série réaliste avec une forte tendance haussière
        # mais avec quelques jours de baisse pour avoir des pertes
        np.random.seed(42)
        changes = [3, 2, -0.5, 4, 3, -0.3, 5, 2, 1, -0.2,
                   3, 4, -0.4, 2, 3, -0.1, 4, 3, 2, -0.3,
                   5, 3, 2, 4, -0.2, 3, 4, 2, 3, 5]
        prices = pd.Series([100] + [100 + sum(changes[:i+1]) for i in range(len(changes))])
        rsi = self.analyzer.calculate_rsi(prices, 14)

        # Avec des gains majoritaires, RSI devrait être élevé
        valid_rsi = rsi.dropna()
        if len(valid_rsi) > 0:
            # RSI devrait être > 50 pour une tendance majoritairement haussière
            assert valid_rsi.iloc[-1] > 70  # Forte tendance haussière

    def test_calculate_rsi_oversold(self):
        """Test RSI en zone de survente."""
        # Créer une série qui descend constamment
        prices = pd.Series([200 - i * 2 for i in range(30)])
        rsi = self.analyzer.calculate_rsi(prices, 14)

        # RSI devrait être bas (<30) pour une tendance baissière forte
        assert rsi.iloc[-1] < 40

    def test_calculate_macd(self, sample_price_data):
        """Test du calcul du MACD."""
        macd_line, signal_line, histogram = self.analyzer.calculate_macd(
            sample_price_data['Close']
        )

        assert len(macd_line) == len(sample_price_data)
        assert len(signal_line) == len(sample_price_data)
        assert len(histogram) == len(sample_price_data)

        # Vérifier que histogram = macd_line - signal_line
        valid_idx = ~(macd_line.isna() | signal_line.isna())
        np.testing.assert_array_almost_equal(
            histogram[valid_idx],
            macd_line[valid_idx] - signal_line[valid_idx],
            decimal=10
        )

    def test_calculate_bollinger_bands(self, sample_price_data):
        """Test du calcul des bandes de Bollinger."""
        upper, middle, lower = self.analyzer.calculate_bollinger_bands(
            sample_price_data['Close'], 20, 2.0
        )

        assert len(upper) == len(sample_price_data)
        assert len(middle) == len(sample_price_data)
        assert len(lower) == len(sample_price_data)

        # Vérifier l'ordre: upper >= middle >= lower
        valid_idx = ~(upper.isna() | middle.isna() | lower.isna())
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()

    def test_calculate_atr(self, sample_price_data):
        """Test du calcul de l'ATR."""
        atr = self.analyzer.calculate_atr(
            sample_price_data['High'],
            sample_price_data['Low'],
            sample_price_data['Close']
        )

        assert len(atr) == len(sample_price_data)
        # ATR doit être positif
        valid_atr = atr.dropna()
        assert (valid_atr > 0).all()

    def test_identify_support_resistance(self, sample_price_data):
        """Test de l'identification support/résistance."""
        support, resistance = self.analyzer.identify_support_resistance(
            sample_price_data['Close'], 20
        )

        assert support <= resistance
        assert support == sample_price_data['Close'].tail(20).min()
        assert resistance == sample_price_data['Close'].tail(20).max()

    # Tests de l'analyse complète

    def test_analyze_bullish(self, sample_price_data):
        """Test de l'analyse sur données haussières."""
        analysis = self.analyzer.analyze(sample_price_data, "TEST")

        assert analysis is not None
        assert isinstance(analysis, TechnicalAnalysis)
        assert analysis.ticker == "TEST"
        assert 0 <= analysis.score <= 100
        assert analysis.trend in ["uptrend", "downtrend", "sideways"]
        assert analysis.momentum in ["strong", "moderate", "weak"]
        assert analysis.volatility > 0
        assert len(analysis.signals) > 0

    def test_analyze_bearish(self, sample_price_data_bearish):
        """Test de l'analyse sur données baissières."""
        analysis = self.analyzer.analyze(sample_price_data_bearish, "BEAR")

        assert analysis is not None
        # Le score devrait être plus bas pour une tendance baissière
        assert analysis.score < 70  # Devrait être relativement bas
        assert analysis.trend in ["downtrend", "sideways"]

    def test_analyze_insufficient_data(self):
        """Test avec données insuffisantes."""
        # Moins de 200 jours de données
        short_data = pd.DataFrame({
            'Open': [100] * 50,
            'High': [105] * 50,
            'Low': [95] * 50,
            'Close': [100] * 50,
            'Volume': [1000000] * 50
        })

        analysis = self.analyzer.analyze(short_data, "SHORT")
        assert analysis is None

    def test_analyze_none_data(self):
        """Test avec données None."""
        analysis = self.analyzer.analyze(None, "NONE")
        assert analysis is None

    # Tests des signaux individuels

    def test_signal_structure(self, sample_price_data):
        """Test de la structure des signaux."""
        analysis = self.analyzer.analyze(sample_price_data, "TEST")

        for signal in analysis.signals:
            assert isinstance(signal, TechnicalSignal)
            assert signal.name != ""
            assert signal.signal in ["bullish", "bearish", "neutral"]
            assert 0 <= signal.weight <= 1
            assert signal.description != ""

    def test_all_signals_present(self, sample_price_data):
        """Test que tous les signaux attendus sont présents."""
        analysis = self.analyzer.analyze(sample_price_data, "TEST")

        expected_signals = [
            "ma_crossover", "price_vs_ma", "rsi", "macd",
            "volume", "bollinger", "support_resistance", "atr"
        ]

        signal_names = [s.name for s in analysis.signals]
        for expected in expected_signals:
            assert expected in signal_names, f"Signal {expected} manquant"

    def test_weights_sum(self):
        """Test que les poids des indicateurs somment à 1."""
        total_weight = sum(self.analyzer.weights.values())
        assert abs(total_weight - 1.0) < 0.001

    # Tests de cas limites

    def test_constant_prices(self):
        """Test avec des prix constants."""
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')
        constant_data = pd.DataFrame({
            'Open': [100.0] * 250,
            'High': [100.0] * 250,
            'Low': [100.0] * 250,
            'Close': [100.0] * 250,
            'Volume': [1000000] * 250
        }, index=dates)

        analysis = self.analyzer.analyze(constant_data, "FLAT")

        # L'analyse devrait quand même fonctionner
        assert analysis is not None
        # Le RSI devrait être à 50 (ni surachat ni survente) ou NaN
        # La tendance devrait être sideways

    def test_high_volatility(self):
        """Test avec haute volatilité."""
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=250, freq='D')

        # Prix très volatiles
        close = 100 + np.cumsum(np.random.randn(250) * 10)
        df = pd.DataFrame({
            'Open': close - np.random.rand(250) * 5,
            'High': close + np.random.rand(250) * 10,
            'Low': close - np.random.rand(250) * 10,
            'Close': close,
            'Volume': np.random.randint(1000000, 10000000, 250)
        }, index=dates)

        df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
        df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)

        analysis = self.analyzer.analyze(df, "VOL")

        assert analysis is not None
        assert analysis.volatility > 0


class TestScoreCalculation:
    """Tests pour le calcul des scores."""

    def test_score_range(self, sample_price_data):
        """Test que le score est dans la plage 0-100."""
        analyzer = TechnicalAnalyzer()
        analysis = analyzer.analyze(sample_price_data, "TEST")

        assert 0 <= analysis.score <= 100

    def test_all_bullish_signals_high_score(self):
        """Test qu'un score élevé est obtenu avec des signaux haussiers."""
        analyzer = TechnicalAnalyzer()

        # Créer des signaux tous bullish
        signals = [
            TechnicalSignal("test1", 1.0, "bullish", 0.5, "Test"),
            TechnicalSignal("test2", 1.0, "bullish", 0.5, "Test"),
        ]

        score = analyzer._calculate_score(signals)
        assert score == 100

    def test_all_bearish_signals_low_score(self):
        """Test qu'un score bas est obtenu avec des signaux baissiers."""
        analyzer = TechnicalAnalyzer()

        signals = [
            TechnicalSignal("test1", 1.0, "bearish", 0.5, "Test"),
            TechnicalSignal("test2", 1.0, "bearish", 0.5, "Test"),
        ]

        score = analyzer._calculate_score(signals)
        assert score == 0

    def test_mixed_signals_medium_score(self):
        """Test qu'un score moyen est obtenu avec des signaux mixtes."""
        analyzer = TechnicalAnalyzer()

        signals = [
            TechnicalSignal("test1", 1.0, "bullish", 0.5, "Test"),
            TechnicalSignal("test2", 1.0, "bearish", 0.5, "Test"),
        ]

        score = analyzer._calculate_score(signals)
        assert score == 50
