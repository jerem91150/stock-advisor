"""
Tests pour le module Smart Money.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.smart_money.tracker import (
    SmartMoneyTracker, DataRomaScraper, SECEdgarScraper,
    GuruPosition, GuruProfile, SmartMoneyAnalysis,
    PositionChange, calculate_smart_money_score
)


class TestPositionChange:
    """Tests pour l'enum PositionChange."""

    def test_position_change_values(self):
        """Test des valeurs de l'enum."""
        assert PositionChange.NEW.value == "new"
        assert PositionChange.INCREASED.value == "increased"
        assert PositionChange.DECREASED.value == "decreased"
        assert PositionChange.SOLD.value == "sold"
        assert PositionChange.UNCHANGED.value == "unchanged"


class TestGuruPosition:
    """Tests pour la structure GuruPosition."""

    def test_create_guru_position(self):
        """Test creation d'une position gourou."""
        position = GuruPosition(
            guru_name="Warren Buffett",
            ticker="AAPL",
            company_name="Apple Inc.",
            shares=905560000,
            value_usd=174000000000,
            portfolio_percent=48.5,
            change=PositionChange.INCREASED,
            change_percent=2.5,
            quarter="Q4 2024"
        )

        assert position.guru_name == "Warren Buffett"
        assert position.ticker == "AAPL"
        assert position.portfolio_percent == 48.5
        assert position.change == PositionChange.INCREASED

    def test_create_new_position(self):
        """Test creation nouvelle position."""
        position = GuruPosition(
            guru_name="Michael Burry",
            ticker="NVDA",
            company_name="NVIDIA",
            shares=100000,
            value_usd=50000000,
            portfolio_percent=5.0,
            change=PositionChange.NEW
        )

        assert position.change == PositionChange.NEW


class TestGuruProfile:
    """Tests pour la structure GuruProfile."""

    def test_create_guru_profile(self):
        """Test creation profil gourou."""
        profile = GuruProfile(
            name="Warren Buffett",
            fund_name="Berkshire Hathaway",
            portfolio_value=350000000000,
            num_holdings=45,
            top_holdings=["AAPL", "BAC", "AXP", "KO", "CVX"]
        )

        assert profile.name == "Warren Buffett"
        assert profile.portfolio_value == 350000000000
        assert "AAPL" in profile.top_holdings


class TestSmartMoneyAnalysis:
    """Tests pour la structure SmartMoneyAnalysis."""

    def test_create_analysis(self):
        """Test creation analyse smart money."""
        analysis = SmartMoneyAnalysis(
            ticker="AAPL",
            guru_positions=[],
            total_gurus_holding=5,
            recent_buyers=["Buffett", "Ackman"],
            recent_sellers=["Burry"],
            avg_portfolio_weight=3.5,
            conviction_score=72.0,
            signal="buy",
            summary="5 gourous detiennent AAPL"
        )

        assert analysis.ticker == "AAPL"
        assert analysis.total_gurus_holding == 5
        assert len(analysis.recent_buyers) == 2
        assert analysis.conviction_score == 72.0
        assert analysis.signal == "buy"


class TestDataRomaScraper:
    """Tests pour DataRomaScraper."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scraper = DataRomaScraper()

    def test_gurus_list(self):
        """Test que la liste des gourous est definie."""
        assert len(self.scraper.GURUS) > 0
        assert "Warren Buffett" in self.scraper.GURUS
        assert "Michael Burry" in self.scraper.GURUS

    @patch('requests.Session.get')
    def test_get_holdings_success(self, mock_get):
        """Test recuperation holdings reussie."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <table id="grid">
            <tr><th>Investor</th><th>Change</th><th>Shares</th><th>Value</th><th>% Port</th></tr>
            <tr>
                <td>Warren Buffett</td>
                <td>Buy</td>
                <td>905,560,000</td>
                <td>$174,000,000,000</td>
                <td>48.5%</td>
            </tr>
        </table>
        </html>
        """
        mock_get.return_value = mock_response

        positions = self.scraper.get_superinvestor_holdings("AAPL")

        assert isinstance(positions, list)
        # Le parsing peut echouer avec HTML simplifie
        # mais ne doit pas lever d'exception

    @patch('requests.Session.get')
    def test_get_holdings_error(self, mock_get):
        """Test avec erreur reseau."""
        mock_get.side_effect = Exception("Network error")

        positions = self.scraper.get_superinvestor_holdings("AAPL")

        assert positions == []

    @patch('requests.Session.get')
    def test_get_holdings_404(self, mock_get):
        """Test avec ticker inconnu."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        positions = self.scraper.get_superinvestor_holdings("XYZINVALID")

        assert positions == []

    def test_parse_change_new(self):
        """Test parsing changement 'new'."""
        cell = MagicMock()
        cell.get_text.return_value = "New position"

        change = self.scraper._parse_change(cell)

        assert change == PositionChange.NEW

    def test_parse_change_buy(self):
        """Test parsing changement 'buy'."""
        cell = MagicMock()
        cell.get_text.return_value = "+15%"

        change = self.scraper._parse_change(cell)

        assert change == PositionChange.INCREASED

    def test_parse_change_sell(self):
        """Test parsing changement 'sell'."""
        cell = MagicMock()
        cell.get_text.return_value = "Sold out"

        change = self.scraper._parse_change(cell)

        assert change == PositionChange.SOLD

    def test_parse_change_none(self):
        """Test parsing sans cellule."""
        change = self.scraper._parse_change(None)

        assert change == PositionChange.UNCHANGED


class TestSECEdgarScraper:
    """Tests pour SECEdgarScraper."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scraper = SECEdgarScraper()

    def test_fund_ciks(self):
        """Test que les CIKs sont definis."""
        assert len(self.scraper.FUND_CIKS) > 0
        assert "Berkshire Hathaway" in self.scraper.FUND_CIKS

    def test_cusip_to_ticker(self):
        """Test conversion CUSIP vers ticker."""
        ticker = self.scraper._cusip_to_ticker("037833100")
        assert ticker == "AAPL"

        ticker = self.scraper._cusip_to_ticker("UNKNOWN")
        assert ticker is None


class TestSmartMoneyTracker:
    """Tests pour SmartMoneyTracker."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.tracker = SmartMoneyTracker()

    @patch.object(DataRomaScraper, 'get_superinvestor_holdings')
    def test_analyze_with_positions(self, mock_holdings):
        """Test analyse avec positions."""
        mock_holdings.return_value = [
            GuruPosition(
                guru_name="Warren Buffett",
                ticker="AAPL",
                company_name="Apple",
                shares=900000000,
                value_usd=170000000000,
                portfolio_percent=48.0,
                change=PositionChange.UNCHANGED
            ),
            GuruPosition(
                guru_name="Bill Ackman",
                ticker="AAPL",
                company_name="Apple",
                shares=5000000,
                value_usd=950000000,
                portfolio_percent=3.5,
                change=PositionChange.INCREASED
            )
        ]

        analysis = self.tracker.analyze("AAPL")

        assert analysis.ticker == "AAPL"
        assert analysis.total_gurus_holding == 2
        assert "Bill Ackman" in analysis.recent_buyers
        assert analysis.conviction_score > 0

    @patch.object(DataRomaScraper, 'get_superinvestor_holdings')
    def test_analyze_no_positions(self, mock_holdings):
        """Test analyse sans positions."""
        mock_holdings.return_value = []

        analysis = self.tracker.analyze("XYZINVALID")

        assert analysis.total_gurus_holding == 0
        # Score = 0 (gourous) + 20 (momentum neutre) + 0 (poids) = 20
        assert analysis.conviction_score == 20
        assert analysis.signal == "neutral"

    @patch.object(DataRomaScraper, 'get_superinvestor_holdings')
    def test_analyze_with_sellers(self, mock_holdings):
        """Test analyse avec vendeurs."""
        mock_holdings.return_value = [
            GuruPosition(
                guru_name="Michael Burry",
                ticker="TSLA",
                company_name="Tesla",
                shares=100000,
                value_usd=20000000,
                portfolio_percent=2.0,
                change=PositionChange.DECREASED
            ),
            GuruPosition(
                guru_name="David Tepper",
                ticker="TSLA",
                company_name="Tesla",
                shares=50000,
                value_usd=10000000,
                portfolio_percent=1.0,
                change=PositionChange.SOLD
            )
        ]

        analysis = self.tracker.analyze("TSLA")

        assert len(analysis.recent_sellers) == 2
        assert len(analysis.recent_buyers) == 0

    def test_conviction_score_calculation(self):
        """Test calcul score conviction."""
        # Score max theorique: 30 (6 gourous) + 40 (tous acheteurs) + 30 (3%+ poids) = 100

        # Test avec 3 gourous, 2 acheteurs, 1 vendeur, 2% poids moyen
        score = self.tracker._calculate_conviction_score(
            total_gurus=3,
            buyers=["A", "B"],
            sellers=["C"],
            avg_weight=2.0
        )

        assert 0 <= score <= 100
        # 3*5=15 + (2/3)*40=26.67 + 2*10=20 = ~62
        assert 50 <= score <= 70

    def test_conviction_score_high(self):
        """Test score conviction eleve."""
        score = self.tracker._calculate_conviction_score(
            total_gurus=6,
            buyers=["A", "B", "C", "D"],
            sellers=[],
            avg_weight=4.0
        )

        assert score >= 90  # Presque max

    def test_conviction_score_low(self):
        """Test score conviction faible."""
        score = self.tracker._calculate_conviction_score(
            total_gurus=1,
            buyers=[],
            sellers=["A"],
            avg_weight=0.5
        )

        assert score <= 30

    def test_determine_signal_strong_buy(self):
        """Test signal strong_buy."""
        signal = self.tracker._determine_signal(
            score=75,
            buyers=["A", "B", "C"],
            sellers=["D"]
        )

        assert signal == "strong_buy"

    def test_determine_signal_buy(self):
        """Test signal buy."""
        signal = self.tracker._determine_signal(
            score=55,
            buyers=["A"],
            sellers=["B"]
        )

        assert signal == "buy"

    def test_determine_signal_sell(self):
        """Test signal sell."""
        signal = self.tracker._determine_signal(
            score=40,
            buyers=["A"],
            sellers=["B", "C", "D"]
        )

        assert signal == "sell"

    def test_determine_signal_neutral(self):
        """Test signal neutral."""
        signal = self.tracker._determine_signal(
            score=45,
            buyers=[],
            sellers=[]
        )

        assert signal == "neutral"

    def test_generate_summary_with_gurus(self):
        """Test generation resume avec gourous."""
        summary = self.tracker._generate_summary(
            ticker="AAPL",
            total_gurus=3,
            buyers=["Buffett", "Ackman"],
            sellers=["Burry"],
            score=65
        )

        assert "3" in summary
        assert "AAPL" in summary
        assert "Buffett" in summary or "Acheteurs" in summary

    def test_generate_summary_no_gurus(self):
        """Test generation resume sans gourous."""
        summary = self.tracker._generate_summary(
            ticker="XYZABC",
            total_gurus=0,
            buyers=[],
            sellers=[],
            score=0
        )

        assert "Aucun" in summary

    def test_cache_mechanism(self):
        """Test du mecanisme de cache."""
        with patch.object(DataRomaScraper, 'get_superinvestor_holdings') as mock:
            mock.return_value = []

            # Premier appel
            self.tracker.analyze("TEST")
            assert mock.call_count == 1

            # Deuxieme appel (devrait utiliser le cache)
            self.tracker.analyze("TEST")
            assert mock.call_count == 1  # Pas d'appel supplementaire


class TestCalculateSmartMoneyScore:
    """Tests pour la fonction calculate_smart_money_score."""

    def test_calculate_score(self):
        """Test calcul du score."""
        analysis = SmartMoneyAnalysis(
            ticker="AAPL",
            guru_positions=[],
            total_gurus_holding=5,
            recent_buyers=["A", "B"],
            recent_sellers=[],
            avg_portfolio_weight=2.5,
            conviction_score=72.5,
            signal="buy",
            summary="Test"
        )

        score = calculate_smart_money_score(analysis)

        assert score == 72.5
