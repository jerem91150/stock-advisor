"""
Tests pour le module Backtest.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtest.simulator import (
    BacktestSimulator, Strategy, Position, Transaction,
    DividendPayment, MonthlySnapshot, BacktestResult
)


class TestStrategy:
    """Tests pour l'enum Strategy."""

    def test_strategy_values(self):
        """Test des valeurs de l'enum."""
        assert Strategy.ALGO_SCORE.value == "algo_score"
        assert Strategy.BUY_AND_HOLD_ETF.value == "etf"
        assert Strategy.RANDOM.value == "random"
        assert Strategy.SAVINGS_ACCOUNT.value == "livret"


class TestPosition:
    """Tests pour la structure Position."""

    def test_create_position(self):
        """Test creation d'une position."""
        pos = Position(
            ticker="AAPL",
            shares=10.0,
            avg_cost=150.0,
            purchase_date=datetime(2024, 1, 15),
            current_price=175.0
        )

        assert pos.ticker == "AAPL"
        assert pos.shares == 10.0
        assert pos.avg_cost == 150.0
        assert pos.current_price == 175.0

    def test_position_value(self):
        """Test calcul valeur position."""
        pos = Position(
            ticker="AAPL",
            shares=10.0,
            avg_cost=150.0,
            purchase_date=datetime(2024, 1, 15),
            current_price=175.0
        )

        assert pos.value == 1750.0  # 10 * 175

    def test_position_gain_pct(self):
        """Test calcul gain en pourcentage."""
        pos = Position(
            ticker="AAPL",
            shares=10.0,
            avg_cost=150.0,
            purchase_date=datetime(2024, 1, 15),
            current_price=175.0
        )

        assert pos.gain_pct == pytest.approx(16.67, rel=0.01)  # (175/150 - 1) * 100

    def test_position_zero_cost(self):
        """Test gain avec cout zero."""
        pos = Position(
            ticker="AAPL",
            shares=10.0,
            avg_cost=0.0,
            purchase_date=datetime(2024, 1, 15),
            current_price=175.0
        )

        assert pos.gain_pct == 0  # Pas de division par zero


class TestTransaction:
    """Tests pour la structure Transaction."""

    def test_create_buy_transaction(self):
        """Test creation transaction achat."""
        tx = Transaction(
            date=datetime(2024, 1, 15),
            ticker="AAPL",
            action="BUY",
            shares=10.0,
            price=150.0,
            total=1500.0,
            reason="Score 75"
        )

        assert tx.action == "BUY"
        assert tx.total == 1500.0

    def test_create_sell_transaction(self):
        """Test creation transaction vente."""
        tx = Transaction(
            date=datetime(2024, 6, 15),
            ticker="AAPL",
            action="SELL",
            shares=10.0,
            price=175.0,
            total=1750.0,
            reason="Score 30 < 35"
        )

        assert tx.action == "SELL"
        assert tx.reason == "Score 30 < 35"


class TestDividendPayment:
    """Tests pour la structure DividendPayment."""

    def test_create_dividend(self):
        """Test creation dividende."""
        div = DividendPayment(
            date=datetime(2024, 5, 15),
            ticker="AAPL",
            amount_per_share=0.96,
            shares_held=100.0,
            total=96.0,
            reinvested=True
        )

        assert div.total == 96.0
        assert div.reinvested is True


class TestBacktestSimulator:
    """Tests pour BacktestSimulator."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.simulator = BacktestSimulator(monthly_investment=100.0)

    def test_initialization(self):
        """Test initialisation du simulateur."""
        assert self.simulator.monthly_investment == 100.0
        assert len(self.simulator.ELIGIBLE_STOCKS) > 0
        assert len(self.simulator.LIVRET_A_RATES) > 0

    def test_livret_a_rates(self):
        """Test que les taux Livret A sont definis."""
        assert self.simulator.LIVRET_A_RATES[2023] == 3.0
        assert self.simulator.LIVRET_A_RATES[2020] == 0.5
        assert self.simulator.LIVRET_A_RATES[2008] == 4.0

    def test_calculate_max_drawdown_empty(self):
        """Test drawdown avec liste vide."""
        dd = self.simulator._calculate_max_drawdown([])
        assert dd == 0

    def test_calculate_max_drawdown(self):
        """Test calcul drawdown."""
        values = [100, 110, 105, 95, 100, 90, 85, 100]
        dd = self.simulator._calculate_max_drawdown(values)

        # Max drawdown: 110 -> 85 = 22.7%
        assert dd == pytest.approx(22.7, rel=0.1)

    def test_calculate_volatility_short(self):
        """Test volatilite avec peu de valeurs."""
        vol = self.simulator._calculate_volatility([100])
        assert vol == 0

    def test_calculate_volatility(self):
        """Test calcul volatilite."""
        values = [100, 102, 98, 105, 103, 101, 107, 104, 106, 108, 105, 110]
        vol = self.simulator._calculate_volatility(values)

        assert vol > 0
        assert vol < 50  # Volatilite raisonnable

    def test_calculate_sharpe_zero_years(self):
        """Test Sharpe avec 0 annees."""
        sharpe = self.simulator._calculate_sharpe([100, 110], 0)
        assert sharpe == 0

    def test_calculate_sharpe(self):
        """Test calcul ratio Sharpe."""
        values = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122]
        sharpe = self.simulator._calculate_sharpe(values, 1)

        assert sharpe != 0  # Devrait avoir une valeur

    def test_backtest_savings_account(self):
        """Test backtest Livret A."""
        result = self.simulator.run_backtest(
            years=1,
            strategy=Strategy.SAVINGS_ACCOUNT
        )

        assert result.strategy == Strategy.SAVINGS_ACCOUNT
        assert result.total_invested == 1300.0  # 13 mois
        assert result.final_value > result.total_invested
        assert result.max_drawdown == 0
        assert result.volatility == 0

    def test_backtest_savings_positive_gain(self):
        """Test que Livret A a un gain positif."""
        result = self.simulator.run_backtest(
            years=5,
            strategy=Strategy.SAVINGS_ACCOUNT
        )

        assert result.total_gain > 0
        assert result.total_gain_pct > 0
        assert result.annualized_return > 0

    @patch('yfinance.download')
    def test_load_historical_data(self, mock_download):
        """Test chargement donnees historiques."""
        mock_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [99, 100, 101],
            'Close': [102, 103, 104],
            'Volume': [1000000, 1100000, 1200000]
        }, index=pd.date_range('2024-01-01', periods=3))

        mock_download.return_value = mock_df

        data = self.simulator._load_historical_data(
            datetime(2024, 1, 1),
            datetime(2024, 12, 31)
        )

        assert isinstance(data, dict)

    def test_calculate_historical_score_missing(self):
        """Test score avec ticker manquant."""
        score = self.simulator._calculate_historical_score(
            "UNKNOWN",
            datetime.now(),
            {}
        )

        assert score == 50  # Score neutre

    def test_calculate_historical_score(self):
        """Test calcul score historique."""
        # Creer des donnees de test
        dates = pd.date_range('2023-01-01', periods=250)
        prices = 100 + np.cumsum(np.random.randn(250) * 0.5)

        df = pd.DataFrame({
            'Open': prices * 0.99,
            'High': prices * 1.01,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(100000, 1000000, 250)
        }, index=dates)

        data = {'TEST.PA': df}

        score = self.simulator._calculate_historical_score(
            'TEST.PA',
            datetime(2023, 9, 1),
            data
        )

        assert 0 <= score <= 100

    def test_find_best_stock_empty(self):
        """Test trouver meilleure action sans donnees."""
        ticker, score = self.simulator._find_best_stock(
            datetime.now(),
            {},
            []
        )

        assert ticker is None
        assert score == 0

    def test_collect_dividends_not_may(self):
        """Test que dividendes ne sont collectes qu'en mai."""
        positions = {
            'TEST.PA': Position(
                ticker='TEST.PA',
                shares=100,
                avg_cost=50.0,
                purchase_date=datetime(2024, 1, 1),
                current_price=55.0
            )
        }

        # Janvier - pas de dividendes
        divs = self.simulator._collect_dividends(
            positions,
            datetime(2024, 1, 15),
            {},
            True
        )

        assert len(divs) == 0

    def test_collect_dividends_may(self):
        """Test collecte dividendes en mai."""
        positions = {
            'TEST.PA': Position(
                ticker='TEST.PA',
                shares=100,
                avg_cost=50.0,
                purchase_date=datetime(2024, 1, 1),
                current_price=55.0
            )
        }

        # Mai - dividendes
        divs = self.simulator._collect_dividends(
            positions,
            datetime(2024, 5, 15),
            {},
            True
        )

        assert len(divs) == 1
        assert divs[0].total > 0
        assert divs[0].reinvested is True

    def test_collect_dividends_bank_rate(self):
        """Test taux dividende eleve pour banques."""
        positions = {
            'BNP.PA': Position(
                ticker='BNP.PA',
                shares=100,
                avg_cost=50.0,
                purchase_date=datetime(2024, 1, 1),
                current_price=60.0
            )
        }

        divs = self.simulator._collect_dividends(
            positions,
            datetime(2024, 5, 15),
            {},
            True
        )

        # Banques ont 6% de rendement
        expected = 60.0 * 0.06 * 100
        assert divs[0].total == pytest.approx(expected, rel=0.01)


class TestBacktestResult:
    """Tests pour la structure BacktestResult."""

    def test_create_result(self):
        """Test creation resultat backtest."""
        result = BacktestResult(
            strategy=Strategy.ALGO_SCORE,
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2025, 1, 1),
            months=60,
            monthly_investment=100.0,
            total_invested=6000.0,
            final_value=8000.0,
            total_gain=2000.0,
            total_gain_pct=33.3,
            annualized_return=6.0,
            total_dividends=300.0,
            dividends_reinvested=300.0,
            benchmark_final=7500.0,
            benchmark_gain_pct=25.0,
            outperformance=8.3,
            max_drawdown=15.0,
            volatility=20.0,
            sharpe_ratio=0.8,
            transactions=[],
            dividends=[],
            monthly_snapshots=[],
            final_positions={}
        )

        assert result.strategy == Strategy.ALGO_SCORE
        assert result.total_gain == 2000.0
        assert result.outperformance == 8.3


class TestIntegration:
    """Tests d'integration."""

    def test_livret_a_1_year(self):
        """Test Livret A sur 1 an."""
        sim = BacktestSimulator(100)
        result = sim.run_backtest(1, Strategy.SAVINGS_ACCOUNT)

        # Verification basique
        assert result.months >= 12
        assert result.final_value > result.total_invested
        assert len(result.monthly_snapshots) >= 12

    def test_livret_a_5_years(self):
        """Test Livret A sur 5 ans."""
        sim = BacktestSimulator(100)
        result = sim.run_backtest(5, Strategy.SAVINGS_ACCOUNT)

        assert result.months >= 60
        assert result.final_value > result.total_invested

    def test_monthly_investment_amounts(self):
        """Test differents montants mensuels."""
        for amount in [50, 100, 200, 500]:
            sim = BacktestSimulator(amount)
            result = sim.run_backtest(1, Strategy.SAVINGS_ACCOUNT)

            assert result.monthly_investment == amount
            assert result.total_invested == amount * result.months
