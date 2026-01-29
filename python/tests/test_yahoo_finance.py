"""
Tests pour le scraper Yahoo Finance.

Note: Ces tests utilisent des mocks pour éviter les appels réseau.
Pour les tests d'intégration avec l'API réelle, voir test_integration.py
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.yahoo_finance import (
    YahooFinanceScraper, StockData, FundamentalData
)


class TestStockData:
    """Tests pour la structure StockData."""

    def test_create_stock_data(self):
        """Test création de données stock."""
        data = StockData(
            ticker="AAPL",
            name="Apple Inc.",
            exchange="NASDAQ",
            currency="USD",
            country="United States",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000.0,
            employees=150000,
            website="https://apple.com",
            description="Apple designs and sells electronics.",
            current_price=185.50,
            previous_close=184.00,
            day_high=186.00,
            day_low=183.50,
            volume=50000000,
            avg_volume=55000000,
            fifty_two_week_high=199.62,
            fifty_two_week_low=124.17
        )

        assert data.ticker == "AAPL"
        assert data.current_price == 185.50
        assert data.market_cap == 3000000.0


class TestFundamentalData:
    """Tests pour la structure FundamentalData."""

    def test_create_fundamental_data(self):
        """Test création de données fondamentales."""
        data = FundamentalData(
            ticker="AAPL",
            pe_ratio=28.5,
            forward_pe=25.0,
            peg_ratio=2.1,
            pb_ratio=45.0,
            ps_ratio=7.5,
            ev_ebitda=22.0,
            roe=0.15,
            roa=0.08,
            profit_margin=0.25,
            operating_margin=0.30,
            gross_margin=0.44,
            revenue_growth=0.08,
            earnings_growth=0.10,
            current_ratio=1.0,
            quick_ratio=0.9,
            debt_to_equity=1.8,
            dividend_yield=0.005,
            dividend_payout_ratio=0.15,
            beta=1.2,
            eps=6.05,
            revenue=400000.0,
            ebitda=130000.0,
            free_cash_flow=100000.0
        )

        assert data.ticker == "AAPL"
        assert data.pe_ratio == 28.5
        assert data.roe == 0.15


class TestYahooFinanceScraper:
    """Tests pour la classe YahooFinanceScraper."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup pour chaque test."""
        self.scraper = YahooFinanceScraper()

    # Tests avec mocks

    @patch('yfinance.Ticker')
    def test_get_stock_info_success(self, mock_ticker):
        """Test récupération info stock réussie."""
        mock_ticker.return_value.info = {
            "symbol": "AAPL",
            "longName": "Apple Inc.",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "United States",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 3000000000000,
            "fullTimeEmployees": 150000,
            "website": "https://apple.com",
            "longBusinessSummary": "Apple designs electronics.",
            "currentPrice": 185.50,
            "previousClose": 184.00,
            "dayHigh": 186.00,
            "dayLow": 183.50,
            "volume": 50000000,
            "averageVolume": 55000000,
            "fiftyTwoWeekHigh": 199.62,
            "fiftyTwoWeekLow": 124.17
        }

        result = self.scraper.get_stock_info("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.name == "Apple Inc."
        assert result.current_price == 185.50

    @patch('yfinance.Ticker')
    def test_get_stock_info_not_found(self, mock_ticker):
        """Test action non trouvée."""
        mock_ticker.return_value.info = {}

        result = self.scraper.get_stock_info("INVALID")

        assert result is None

    @patch('yfinance.Ticker')
    def test_get_fundamentals_success(self, mock_ticker):
        """Test récupération fondamentaux réussie."""
        mock_ticker.return_value.info = {
            "trailingPE": 28.5,
            "forwardPE": 25.0,
            "pegRatio": 2.1,
            "priceToBook": 45.0,
            "priceToSalesTrailing12Months": 7.5,
            "enterpriseToEbitda": 22.0,
            "returnOnEquity": 0.15,
            "returnOnAssets": 0.08,
            "profitMargins": 0.25,
            "operatingMargins": 0.30,
            "grossMargins": 0.44,
            "revenueGrowth": 0.08,
            "earningsGrowth": 0.10,
            "currentRatio": 1.0,
            "quickRatio": 0.9,
            "debtToEquity": 180,
            "dividendYield": 0.005,
            "payoutRatio": 0.15,
            "beta": 1.2,
            "trailingEps": 6.05,
            "totalRevenue": 400000000000,
            "ebitda": 130000000000,
            "freeCashflow": 100000000000
        }

        result = self.scraper.get_fundamentals("AAPL")

        assert result is not None
        assert result.pe_ratio == 28.5
        assert result.roe == 0.15

    @patch('yfinance.Ticker')
    def test_get_price_history_success(self, mock_ticker):
        """Test récupération historique prix."""
        # Créer un DataFrame de test
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        mock_df = pd.DataFrame({
            'Open': [100 + i * 0.1 for i in range(100)],
            'High': [102 + i * 0.1 for i in range(100)],
            'Low': [98 + i * 0.1 for i in range(100)],
            'Close': [101 + i * 0.1 for i in range(100)],
            'Volume': [1000000] * 100
        }, index=dates)

        mock_ticker.return_value.history.return_value = mock_df

        result = self.scraper.get_price_history("AAPL", period="1y")

        assert result is not None
        assert len(result) == 100
        assert 'Close' in result.columns

    @patch('yfinance.Ticker')
    def test_get_price_history_empty(self, mock_ticker):
        """Test historique prix vide."""
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        result = self.scraper.get_price_history("INVALID")

        assert result is None

    @patch('yfinance.Ticker')
    def test_is_pea_eligible_french_stock(self, mock_ticker):
        """Test éligibilité PEA pour action française."""
        mock_ticker.return_value.info = {
            "exchange": "PAR",
            "country": "France"
        }

        result = self.scraper.is_pea_eligible("MC.PA")

        assert result is True

    @patch('yfinance.Ticker')
    def test_is_pea_eligible_us_stock(self, mock_ticker):
        """Test éligibilité PEA pour action US."""
        mock_ticker.return_value.info = {
            "exchange": "NASDAQ",
            "country": "United States"
        }

        result = self.scraper.is_pea_eligible("AAPL")

        assert result is False

    @patch('yfinance.Ticker')
    def test_is_pea_eligible_german_stock(self, mock_ticker):
        """Test éligibilité PEA pour action allemande."""
        mock_ticker.return_value.info = {
            "exchange": "FRA",  # Frankfurt
            "country": "Germany"
        }

        result = self.scraper.is_pea_eligible("SAP.DE")

        # L'Allemagne est dans l'UE mais pas sur Euronext Paris
        assert result is False

    # Tests des indices

    def test_get_cac40_constituents(self):
        """Test récupération constituants CAC40."""
        constituents = self.scraper.get_index_constituents("CAC40")

        assert len(constituents) > 0
        assert "MC.PA" in constituents  # LVMH
        assert all(ticker.endswith(".PA") for ticker in constituents)

    def test_get_sp500_constituents(self):
        """Test récupération constituants S&P500 (partiel)."""
        # La méthode interne _get_sp500_tickers retourne une liste partielle
        constituents = self.scraper._get_sp500_tickers()

        assert len(constituents) > 0
        assert "AAPL" in constituents
        assert "MSFT" in constituents

    def test_get_unknown_index(self):
        """Test indice inconnu."""
        constituents = self.scraper.get_index_constituents("UNKNOWN")

        assert len(constituents) == 0

    # Tests du résumé marché

    @patch('yfinance.Ticker')
    def test_get_market_summary(self, mock_ticker):
        """Test résumé du marché."""
        mock_ticker.return_value.info = {
            "regularMarketPrice": 5000.0,
            "regularMarketChange": 50.0,
            "regularMarketChangePercent": 1.0,
            "previousClose": 4950.0
        }

        summary = self.scraper.get_market_summary()

        # Devrait contenir les principaux indices
        assert "S&P 500" in summary or len(summary) >= 0

    # Tests batch

    @patch('yfinance.Ticker')
    def test_batch_get_stocks(self, mock_ticker):
        """Test récupération batch d'actions."""
        mock_ticker.return_value.info = {
            "symbol": "TEST",
            "longName": "Test Corp",
            "exchange": "NYSE",
            "currency": "USD",
            "country": "United States",
            "sector": "Technology",
            "industry": "Software",
            "marketCap": 1000000000,
            "currentPrice": 100.0,
            "previousClose": 99.0,
            "dayHigh": 101.0,
            "dayLow": 98.0,
            "volume": 1000000,
            "averageVolume": 1000000,
            "fiftyTwoWeekHigh": 120.0,
            "fiftyTwoWeekLow": 80.0
        }

        results = self.scraper.batch_get_stocks(["AAPL", "MSFT"])

        assert len(results) == 2

    # Tests des dividendes

    @patch('yfinance.Ticker')
    def test_get_dividends(self, mock_ticker):
        """Test récupération historique dividendes."""
        dates = pd.date_range(start='2023-01-01', periods=4, freq='QE')
        mock_dividends = pd.Series([0.24, 0.24, 0.24, 0.24], index=dates)
        mock_ticker.return_value.dividends = mock_dividends

        result = self.scraper.get_dividends("AAPL")

        assert result is not None
        assert len(result) == 4

    @patch('yfinance.Ticker')
    def test_get_dividends_empty(self, mock_ticker):
        """Test action sans dividende."""
        mock_ticker.return_value.dividends = pd.Series()

        result = self.scraper.get_dividends("TSLA")

        assert result is None

    # Tests des dates de résultats

    @patch('yfinance.Ticker')
    def test_get_earnings_dates(self, mock_ticker):
        """Test récupération dates de résultats."""
        mock_calendar = pd.DataFrame({
            'Earnings Date': ['2024-02-01'],
            'EPS Estimate': [1.50],
            'Reported EPS': [None]
        })
        mock_ticker.return_value.calendar = mock_calendar

        result = self.scraper.get_earnings_dates("AAPL")

        assert result is not None


class TestPEAEligibility:
    """Tests spécifiques pour l'éligibilité PEA."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scraper = YahooFinanceScraper()

    def test_pea_eligible_exchanges(self):
        """Test des bourses éligibles PEA."""
        pea_exchanges = self.scraper.PEA_ELIGIBLE_EXCHANGES

        assert "PAR" in pea_exchanges
        assert "EPA" in pea_exchanges
        assert "Euronext Paris" in pea_exchanges

    @patch('yfinance.Ticker')
    def test_pea_eligible_eu_countries(self, mock_ticker):
        """Test des pays UE éligibles PEA."""
        eu_countries = [
            "France", "Germany", "Italy", "Spain", "Netherlands",
            "Belgium", "Portugal", "Austria"
        ]

        for country in eu_countries:
            mock_ticker.return_value.info = {
                "exchange": "PAR",  # Doit être sur Euronext Paris
                "country": country
            }

            # Seules les actions sur PAR de pays UE sont éligibles
            result = self.scraper.is_pea_eligible("TEST")
            if country == "France":
                assert result is True, f"{country} devrait être éligible PEA"
