"""
Fixtures pytest partagées pour les tests Stock Advisor.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture
def sample_price_data():
    """Génère des données de prix simulées pour les tests."""
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=250, freq='D')

    # Simuler un prix qui monte progressivement avec du bruit
    base_price = 100
    trend = np.linspace(0, 30, 250)  # Tendance haussière
    noise = np.random.randn(250) * 2  # Bruit

    close_prices = base_price + trend + noise

    # Générer OHLCV
    df = pd.DataFrame({
        'Open': close_prices - np.random.rand(250) * 2,
        'High': close_prices + np.random.rand(250) * 3,
        'Low': close_prices - np.random.rand(250) * 3,
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 10000000, 250)
    }, index=dates)

    # S'assurer que High >= Close >= Low et High >= Open >= Low
    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)

    return df


@pytest.fixture
def sample_price_data_bearish():
    """Génère des données de prix simulées en tendance baissière."""
    np.random.seed(123)
    dates = pd.date_range(start='2023-01-01', periods=250, freq='D')

    base_price = 150
    trend = np.linspace(0, -40, 250)  # Tendance baissière
    noise = np.random.randn(250) * 2

    close_prices = base_price + trend + noise

    df = pd.DataFrame({
        'Open': close_prices + np.random.rand(250) * 2,
        'High': close_prices + np.random.rand(250) * 3,
        'Low': close_prices - np.random.rand(250) * 3,
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 10000000, 250)
    }, index=dates)

    df['High'] = df[['Open', 'High', 'Close']].max(axis=1)
    df['Low'] = df[['Open', 'Low', 'Close']].min(axis=1)

    return df


@pytest.fixture
def sample_fundamentals_good():
    """Données fondamentales d'une bonne entreprise."""
    return {
        "pe_ratio": 18.5,
        "peg_ratio": 1.1,
        "pb_ratio": 3.2,
        "ev_ebitda": 10.5,
        "roe": 0.22,  # 22%
        "profit_margin": 0.18,  # 18%
        "roa": 0.12,  # 12%
        "revenue_growth": 0.15,  # 15%
        "earnings_growth": 0.20,  # 20%
        "debt_to_equity": 0.5,
        "current_ratio": 2.0,
        "dividend_yield": 0.025  # 2.5%
    }


@pytest.fixture
def sample_fundamentals_poor():
    """Données fondamentales d'une entreprise en difficulté."""
    return {
        "pe_ratio": 45.0,
        "peg_ratio": 3.5,
        "pb_ratio": 8.0,
        "ev_ebitda": 25.0,
        "roe": 0.05,  # 5%
        "profit_margin": 0.02,  # 2%
        "roa": 0.02,  # 2%
        "revenue_growth": -0.05,  # -5%
        "earnings_growth": -0.15,  # -15%
        "debt_to_equity": 2.5,
        "current_ratio": 0.8,
        "dividend_yield": 0.0
    }


@pytest.fixture
def sample_fundamentals_mixed():
    """Données fondamentales mixtes."""
    return {
        "pe_ratio": 25.0,
        "peg_ratio": 1.8,
        "pb_ratio": 4.0,
        "ev_ebitda": 14.0,
        "roe": 0.15,  # 15%
        "profit_margin": 0.10,  # 10%
        "roa": 0.08,  # 8%
        "revenue_growth": 0.08,  # 8%
        "earnings_growth": 0.10,  # 10%
        "debt_to_equity": 1.0,
        "current_ratio": 1.5,
        "dividend_yield": 0.015  # 1.5%
    }


@pytest.fixture
def sample_stock_filter_data():
    """Données de stock pour les tests de filtres."""
    from src.filters.base import StockFilterData

    return [
        StockFilterData(
            ticker="AAPL",
            name="Apple Inc",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            market_cap=3000000,
            pe_ratio=28,
            peg_ratio=2.1,
            debt_to_equity=1.5,
            roe=0.25,
            pea_eligible=False
        ),
        StockFilterData(
            ticker="PM",
            name="Philip Morris",
            sector="Consumer Staples",
            industry="Tobacco",
            country="United States",
            market_cap=150000,
            pe_ratio=15,
            pea_eligible=False
        ),
        StockFilterData(
            ticker="MC.PA",
            name="LVMH",
            sector="Consumer Discretionary",
            industry="Luxury Goods",
            country="France",
            market_cap=400000,
            pe_ratio=25,
            pea_eligible=True
        ),
        StockFilterData(
            ticker="LMT",
            name="Lockheed Martin",
            sector="Aerospace & Defense",
            industry="Defense",
            country="United States",
            market_cap=120000,
            pe_ratio=18,
            pea_eligible=False
        ),
        StockFilterData(
            ticker="TINY",
            name="Tiny Corp",
            sector="Technology",
            industry="Software",
            country="United States",
            market_cap=500,  # Small cap
            pe_ratio=60,
            debt_to_equity=3.0,
            pea_eligible=False
        )
    ]
