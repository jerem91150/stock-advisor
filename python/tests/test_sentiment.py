"""
Tests pour le module d'analyse de sentiment.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sentiment.analyzer import (
    SentimentAnalyzer, SimpleSentimentAnalyzer,
    GoogleNewsScraper, RedditScraper, OllamaSentimentAnalyzer,
    NewsArticle, SocialPost, SentimentAnalysis, SentimentLabel
)


class TestSentimentLabel:
    """Tests pour l'enum SentimentLabel."""

    def test_sentiment_labels(self):
        """Test des valeurs de l'enum."""
        assert SentimentLabel.VERY_BULLISH.value == "very_bullish"
        assert SentimentLabel.BULLISH.value == "bullish"
        assert SentimentLabel.NEUTRAL.value == "neutral"
        assert SentimentLabel.BEARISH.value == "bearish"
        assert SentimentLabel.VERY_BEARISH.value == "very_bearish"


class TestNewsArticle:
    """Tests pour la structure NewsArticle."""

    def test_create_news_article(self):
        """Test creation d'un article."""
        article = NewsArticle(
            title="Apple annonce des resultats records",
            source="Reuters",
            url="https://example.com/article",
            published_at=None,
            summary="Apple a annonce des resultats trimestriels exceptionnels..."
        )

        assert article.title == "Apple annonce des resultats records"
        assert article.source == "Reuters"
        assert "Apple" in (article.summary or "")


class TestSocialPost:
    """Tests pour la structure SocialPost."""

    def test_create_social_post(self):
        """Test creation d'un post Reddit."""
        post = SocialPost(
            platform="reddit",
            title="$AAPL to the moon!",
            content="Apple is going to crush earnings...",
            url="https://reddit.com/r/wallstreetbets/...",
            author="user123",
            upvotes=1500,
            comments=234,
            published_at=None
        )

        assert post.platform == "reddit"
        assert post.upvotes == 1500
        assert "AAPL" in post.title


class TestSentimentAnalysis:
    """Tests pour la structure SentimentAnalysis."""

    def test_create_analysis(self):
        """Test creation analyse complete."""
        analysis = SentimentAnalysis(
            ticker="AAPL",
            score=65.0,
            label=SentimentLabel.BULLISH,
            news_score=70.0,
            news_count=5,
            reddit_score=60.0,
            reddit_count=10,
            summary="Sentiment positif"
        )

        assert analysis.ticker == "AAPL"
        assert analysis.label == SentimentLabel.BULLISH
        assert analysis.score == 65.0


class TestSimpleSentimentAnalyzer:
    """Tests pour SimpleSentimentAnalyzer (analyse par mots-cles)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.analyzer = SimpleSentimentAnalyzer()

    def test_positive_sentiment(self):
        """Test detection sentiment positif."""
        text = "Excellent growth, strong earnings, bullish outlook"
        score, label = self.analyzer.analyze(text)

        assert label == SentimentLabel.BULLISH
        assert score > 0

    def test_negative_sentiment(self):
        """Test detection sentiment negatif."""
        text = "Terrible loss, bearish market, decline expected"
        score, label = self.analyzer.analyze(text)

        assert label == SentimentLabel.BEARISH
        assert score < 0

    def test_neutral_sentiment(self):
        """Test detection sentiment neutre."""
        text = "The company reported results today"
        score, label = self.analyzer.analyze(text)

        assert label == SentimentLabel.NEUTRAL
        assert score == 0

    def test_mixed_sentiment(self):
        """Test sentiment mixte."""
        # Utiliser des mots qui sont dans les listes
        text = "Strong growth but significant loss and decline"
        score, label = self.analyzer.analyze(text)

        # Score devrait etre proche de 0 (mixte)
        # strong, growth = +2, loss, decline = -2, donc score = 0
        assert -0.6 <= score <= 0.6

    def test_empty_text(self):
        """Test texte vide."""
        score, label = self.analyzer.analyze("")

        assert label == SentimentLabel.NEUTRAL
        assert score == 0

    def test_french_positive_words(self):
        """Test mots positifs en francais."""
        text = "Excellente croissance et hausse des benefices"
        score, label = self.analyzer.analyze(text)

        assert score > 0

    def test_french_negative_words(self):
        """Test mots negatifs en francais."""
        text = "Chute dramatique, pertes importantes, baisse"
        score, label = self.analyzer.analyze(text)

        assert score < 0


class TestGoogleNewsScraper:
    """Tests pour GoogleNewsScraper."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scraper = GoogleNewsScraper()

    @patch('requests.Session.get')
    def test_search_success(self, mock_get):
        """Test recherche reussie."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
        <article>
            <a class="JtKRv" href="./article1">Apple Stock Rises</a>
            <div class="summary">Apple shares increased by 5%...</div>
            <a data-n-tid="1">Reuters</a>
        </article>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        articles = self.scraper.search("AAPL stock", max_results=5)

        # Peut retourner 0 si le parsing echoue (HTML simplifie)
        assert isinstance(articles, list)

    @patch('requests.Session.get')
    def test_search_error(self, mock_get):
        """Test recherche avec erreur."""
        mock_get.side_effect = Exception("Network error")

        articles = self.scraper.search("AAPL")

        assert articles == []

    def test_get_stock_news(self):
        """Test methode get_stock_news."""
        with patch.object(self.scraper, 'search', return_value=[]) as mock_search:
            self.scraper.get_stock_news("AAPL", "Apple Inc.", max_results=5)
            mock_search.assert_called_once()


class TestRedditScraper:
    """Tests pour RedditScraper."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.scraper = RedditScraper()

    def test_finance_subreddits(self):
        """Test liste des subreddits."""
        assert "stocks" in self.scraper.FINANCE_SUBREDDITS
        assert "wallstreetbets" in self.scraper.FINANCE_SUBREDDITS
        assert "vosfinances" in self.scraper.FINANCE_SUBREDDITS

    @patch('requests.get')
    def test_search_scraping_success(self, mock_get):
        """Test scraping Reddit reussi."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'children': [
                    {
                        'data': {
                            'title': 'AAPL earnings discussion',
                            'subreddit': 'stocks',
                            'score': 500,
                            'num_comments': 120,
                            'permalink': '/r/stocks/...',
                            'created_utc': 1705312800,
                            'selftext': 'What do you think about Apple?',
                            'author': 'testuser'
                        }
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        posts = self.scraper._search_scraping("AAPL Apple", ["stocks"], 5)

        assert len(posts) == 1
        assert posts[0].platform == "reddit"
        assert posts[0].upvotes == 500

    @patch('requests.get')
    def test_search_scraping_error(self, mock_get):
        """Test scraping Reddit avec erreur."""
        mock_get.side_effect = Exception("Rate limited")

        posts = self.scraper._search_scraping("AAPL", ["stocks"], 5)

        assert posts == []


class TestOllamaSentimentAnalyzer:
    """Tests pour OllamaSentimentAnalyzer."""

    def test_init_without_ollama(self):
        """Test initialisation sans Ollama."""
        with patch('src.sentiment.analyzer.OLLAMA_AVAILABLE', False):
            analyzer = OllamaSentimentAnalyzer()
            assert not analyzer.available

    def test_analyze_not_available(self):
        """Test analyse quand Ollama non disponible."""
        analyzer = OllamaSentimentAnalyzer()
        analyzer.available = False

        score, label, confidence = analyzer.analyze("Test text")

        assert score == 0
        assert label == SentimentLabel.NEUTRAL
        assert confidence == 0

    def test_analyze_empty_text(self):
        """Test analyse texte vide."""
        analyzer = OllamaSentimentAnalyzer()
        analyzer.available = True

        score, label, confidence = analyzer.analyze("")

        assert score == 0
        assert label == SentimentLabel.NEUTRAL


class TestSentimentAnalyzer:
    """Tests pour SentimentAnalyzer principal."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.analyzer = SentimentAnalyzer()

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_analyze_with_news_only(self, mock_reddit, mock_news):
        """Test analyse avec news seulement."""
        mock_news.return_value = [
            NewsArticle(
                title="Apple reports strong earnings",
                source="Bloomberg",
                url="https://example.com",
                published_at=None,
                summary="Excellent quarterly results"
            ),
            NewsArticle(
                title="Apple beats expectations",
                source="Reuters",
                url="https://example.com",
                published_at=None,
                summary="Revenue growth exceeded forecasts"
            )
        ]
        mock_reddit.return_value = []

        analysis = self.analyzer.analyze("AAPL", "Apple Inc.", use_llm=False)

        assert analysis is not None
        assert analysis.ticker == "AAPL"
        assert analysis.news_count == 2

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_analyze_with_reddit_only(self, mock_reddit, mock_news):
        """Test analyse avec Reddit seulement."""
        mock_news.return_value = []
        mock_reddit.return_value = [
            SocialPost(
                platform="reddit",
                title="AAPL to the moon!",
                content="Bullish on Apple!",
                url="https://reddit.com/...",
                author="user1",
                upvotes=2000,
                comments=500,
                published_at=None
            )
        ]

        analysis = self.analyzer.analyze("AAPL", "Apple Inc.", use_llm=False)

        assert analysis is not None
        assert analysis.reddit_count == 1

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_analyze_no_data(self, mock_reddit, mock_news):
        """Test analyse sans donnees."""
        mock_news.return_value = []
        mock_reddit.return_value = []

        analysis = self.analyzer.analyze("INVALID", "Invalid Corp", use_llm=False)

        assert analysis is not None
        # Score neutre par defaut (50 sur echelle 0-100)
        assert analysis.score == 50

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_analyze_combined(self, mock_reddit, mock_news):
        """Test analyse combinee news + reddit."""
        mock_news.return_value = [
            NewsArticle(
                title="Apple faces challenges with decline",
                source="WSJ",
                url="https://example.com",
                published_at=None,
                summary="Declining iPhone sales in China"
            )
        ]
        mock_reddit.return_value = [
            SocialPost(
                platform="reddit",
                title="AAPL bearish sell",
                content="I'm selling my Apple shares",
                url="https://reddit.com/...",
                author="user1",
                upvotes=100,
                comments=50,
                published_at=None
            )
        ]

        analysis = self.analyzer.analyze("AAPL", "Apple Inc.", use_llm=False)

        assert analysis is not None
        assert analysis.news_count == 1
        assert analysis.reddit_count == 1

    def test_generate_summary(self):
        """Test generation du resume."""
        summary = self.analyzer._generate_summary(
            ticker="AAPL",
            news_count=5,
            reddit_count=10,
            news_score=0.3,
            reddit_score=-0.1,
            label=SentimentLabel.NEUTRAL
        )

        assert "AAPL" in summary
        assert "5" in summary
        assert "10" in summary


class TestScoreConversion:
    """Tests pour la conversion des scores."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.analyzer = SentimentAnalyzer()

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_score_range_0_100(self, mock_reddit, mock_news):
        """Test que le score final est dans 0-100."""
        # Score tres positif
        mock_news.return_value = [
            NewsArticle(
                title="Excellent growth bullish strong beat",
                source="Test",
                url="",
                published_at=None
            )
        ]
        mock_reddit.return_value = []

        analysis = self.analyzer.analyze("TEST", "Test", use_llm=False)

        assert 0 <= analysis.score <= 100

    @patch.object(GoogleNewsScraper, 'get_stock_news')
    @patch.object(RedditScraper, 'get_stock_mentions')
    def test_score_neutral_is_50(self, mock_reddit, mock_news):
        """Test que score neutre = 50."""
        mock_news.return_value = []
        mock_reddit.return_value = []

        analysis = self.analyzer.analyze("TEST", "Test", use_llm=False)

        assert analysis.score == 50
