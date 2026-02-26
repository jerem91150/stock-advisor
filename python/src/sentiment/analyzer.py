"""
Phase 3 : Module d'Analyse de Sentiment

Sources:
- Google News (scraping)
- Reddit (API PRAW)
- Analyse via LLM local (Ollama)

Le score de sentiment représente 25% du score global.
"""

import re
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import requests
from bs4 import BeautifulSoup
from loguru import logger

# Optional imports
try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("PRAW non installé. Reddit API désactivée.")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama non installé. Analyse LLM désactivée.")


class SentimentLabel(Enum):
    """Labels de sentiment."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class NewsArticle:
    """Article de news."""
    title: str
    source: str
    url: str
    published_at: Optional[datetime]
    summary: Optional[str] = None
    sentiment_score: Optional[float] = None  # -1 à +1
    sentiment_label: Optional[SentimentLabel] = None


@dataclass
class SocialPost:
    """Post de réseau social (Reddit, etc.)."""
    platform: str
    title: str
    content: str
    url: str
    author: str
    upvotes: int
    comments: int
    published_at: Optional[datetime]
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None


@dataclass
class SentimentAnalysis:
    """Résultat de l'analyse de sentiment."""
    ticker: str
    score: float  # 0-100
    label: SentimentLabel

    # Détails par source
    news_score: Optional[float] = None
    news_count: int = 0
    reddit_score: Optional[float] = None
    reddit_count: int = 0

    # Articles et posts analysés
    news_articles: list[NewsArticle] = field(default_factory=list)
    social_posts: list[SocialPost] = field(default_factory=list)

    # Métadonnées
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    llm_used: bool = False

    # Résumé
    summary: str = ""
    key_themes: list[str] = field(default_factory=list)


class GoogleNewsScraper:
    """Scraper pour Google News."""

    BASE_URL = "https://news.google.com/search"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def search(self, query: str, max_results: int = 10) -> list[NewsArticle]:
        """
        Recherche des articles sur Google News.

        Args:
            query: Terme de recherche (ex: "LVMH stock")
            max_results: Nombre max d'articles

        Returns:
            Liste d'articles
        """
        articles = []

        try:
            params = {
                'q': query,
                'hl': 'fr',
                'gl': 'FR',
                'ceid': 'FR:fr'
            }

            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parser les articles (structure Google News)
            article_elements = soup.find_all('article')[:max_results]

            for elem in article_elements:
                try:
                    # Titre
                    title_elem = elem.find('a', class_='JtKRv')
                    if not title_elem:
                        title_elem = elem.find('h3') or elem.find('h4')

                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)

                    # URL
                    link = title_elem.get('href', '')
                    if link.startswith('./'):
                        link = f"https://news.google.com{link[1:]}"

                    # Source
                    source_elem = elem.find('a', {'data-n-tid': True})
                    source = source_elem.get_text(strip=True) if source_elem else "Unknown"

                    # Date (approximative)
                    time_elem = elem.find('time')
                    published_at = None
                    if time_elem and time_elem.get('datetime'):
                        try:
                            published_at = datetime.fromisoformat(
                                time_elem['datetime'].replace('Z', '+00:00')
                            )
                        except Exception:
                            pass

                    articles.append(NewsArticle(
                        title=title,
                        source=source,
                        url=link,
                        published_at=published_at
                    ))

                except Exception as e:
                    logger.debug(f"Erreur parsing article: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erreur Google News: {e}")

        return articles

    def get_stock_news(self, ticker: str, company_name: str, max_results: int = 10) -> list[NewsArticle]:
        """Recherche des news pour une action spécifique."""
        # Rechercher avec le nom de l'entreprise et le ticker
        query = f"{company_name} stock OR {ticker}"
        return self.search(query, max_results)


class RedditScraper:
    """Scraper pour Reddit via API PRAW ou scraping."""

    # Subreddits financiers pertinents
    FINANCE_SUBREDDITS = [
        "stocks",
        "investing",
        "wallstreetbets",
        "stockmarket",
        "vosfinances",  # Français
        "eupersonalfinance"
    ]

    def __init__(self, client_id: str = None, client_secret: str = None):
        self.reddit = None
        self.use_api = False

        if PRAW_AVAILABLE and client_id and client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent="StockAdvisor/1.0"
                )
                self.use_api = True
                logger.info("Reddit API initialisée")
            except Exception as e:
                logger.warning(f"Impossible d'initialiser Reddit API: {e}")

    def search(self, query: str, subreddits: list[str] = None, max_results: int = 20) -> list[SocialPost]:
        """
        Recherche sur Reddit.

        Args:
            query: Terme de recherche
            subreddits: Liste de subreddits (défaut: finance)
            max_results: Nombre max de posts

        Returns:
            Liste de posts
        """
        if subreddits is None:
            subreddits = self.FINANCE_SUBREDDITS

        posts = []

        if self.use_api and self.reddit:
            posts = self._search_api(query, subreddits, max_results)
        else:
            posts = self._search_scraping(query, subreddits, max_results)

        return posts

    def _search_api(self, query: str, subreddits: list[str], max_results: int) -> list[SocialPost]:
        """Recherche via API Reddit."""
        posts = []

        for subreddit_name in subreddits[:3]:  # Limiter à 3 subreddits
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                results = subreddit.search(query, limit=max_results // 3, time_filter='month')

                for submission in results:
                    posts.append(SocialPost(
                        platform="reddit",
                        title=submission.title,
                        content=submission.selftext[:500] if submission.selftext else "",
                        url=f"https://reddit.com{submission.permalink}",
                        author=str(submission.author),
                        upvotes=submission.score,
                        comments=submission.num_comments,
                        published_at=datetime.fromtimestamp(submission.created_utc)
                    ))

            except Exception as e:
                logger.debug(f"Erreur Reddit API {subreddit_name}: {e}")

        return posts

    def _search_scraping(self, query: str, subreddits: list[str], max_results: int) -> list[SocialPost]:
        """Recherche via scraping (fallback)."""
        posts = []

        # Utiliser l'API JSON publique de Reddit (sans auth)
        for subreddit_name in subreddits[:2]:
            try:
                url = f"https://www.reddit.com/r/{subreddit_name}/search.json"
                params = {
                    'q': query,
                    'restrict_sr': 'on',
                    't': 'month',
                    'limit': max_results // 2
                }
                headers = {'User-Agent': 'StockAdvisor/1.0'}

                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                for child in data.get('data', {}).get('children', []):
                    post_data = child.get('data', {})
                    posts.append(SocialPost(
                        platform="reddit",
                        title=post_data.get('title', ''),
                        content=post_data.get('selftext', '')[:500],
                        url=f"https://reddit.com{post_data.get('permalink', '')}",
                        author=post_data.get('author', 'unknown'),
                        upvotes=post_data.get('score', 0),
                        comments=post_data.get('num_comments', 0),
                        published_at=datetime.fromtimestamp(post_data.get('created_utc', 0))
                    ))

            except Exception as e:
                logger.debug(f"Erreur Reddit scraping {subreddit_name}: {e}")

        return posts

    def get_stock_mentions(self, ticker: str, company_name: str, max_results: int = 20) -> list[SocialPost]:
        """Recherche les mentions d'une action sur Reddit."""
        # Nettoyer le ticker (enlever .PA, etc.)
        clean_ticker = ticker.split('.')[0]
        query = f"{clean_ticker} OR {company_name}"
        return self.search(query, max_results=max_results)


class OllamaSentimentAnalyzer:
    """Analyseur de sentiment utilisant Ollama (LLM local)."""

    DEFAULT_MODEL = "llama3.2:3b"  # Modèle léger par défaut

    SENTIMENT_PROMPT = """Analyze the sentiment of the following text about the stock/company.
Respond with ONLY a JSON object in this exact format:
{{"sentiment": "positive" or "negative" or "neutral", "score": number between -1 and 1, "confidence": number between 0 and 1}}

Text to analyze:
{text}

JSON response:"""

    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL
        self.available = OLLAMA_AVAILABLE

        if self.available:
            # Vérifier si le modèle est disponible
            try:
                models = ollama.list()
                model_names = [m['name'] for m in models.get('models', [])]
                if self.model not in model_names:
                    logger.warning(f"Modèle {self.model} non trouvé. Modèles disponibles: {model_names}")
                    self.available = False
            except Exception as e:
                logger.warning(f"Ollama non accessible: {e}")
                self.available = False

    def analyze(self, text: str) -> tuple[float, SentimentLabel, float]:
        """
        Analyse le sentiment d'un texte.

        Args:
            text: Texte à analyser

        Returns:
            (score, label, confidence)
            score: -1 à +1
            label: SentimentLabel
            confidence: 0 à 1
        """
        if not self.available or not text:
            return 0, SentimentLabel.NEUTRAL, 0

        try:
            # Tronquer le texte si trop long
            text = text[:1000]

            response = ollama.generate(
                model=self.model,
                prompt=self.SENTIMENT_PROMPT.format(text=text),
                options={'temperature': 0.1}
            )

            # Parser la réponse JSON
            response_text = response['response'].strip()

            # Extraire le JSON
            json_match = re.search(r'\{[^}]+\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                score = float(result.get('score', 0))
                confidence = float(result.get('confidence', 0.5))

                # Convertir en label
                if score > 0.3:
                    label = SentimentLabel.BULLISH if score < 0.6 else SentimentLabel.VERY_BULLISH
                elif score < -0.3:
                    label = SentimentLabel.BEARISH if score > -0.6 else SentimentLabel.VERY_BEARISH
                else:
                    label = SentimentLabel.NEUTRAL

                return score, label, confidence

        except Exception as e:
            logger.debug(f"Erreur analyse LLM: {e}")

        return 0, SentimentLabel.NEUTRAL, 0

    def analyze_batch(self, texts: list[str]) -> list[tuple[float, SentimentLabel, float]]:
        """Analyse un batch de textes."""
        return [self.analyze(text) for text in texts]


class SimpleSentimentAnalyzer:
    """Analyseur de sentiment simple basé sur des mots-clés (fallback sans LLM)."""

    POSITIVE_WORDS = {
        'buy', 'bullish', 'growth', 'profit', 'gain', 'up', 'rise', 'surge',
        'strong', 'beat', 'exceed', 'outperform', 'upgrade', 'positive',
        'achat', 'hausse', 'croissance', 'bénéfice', 'progression',
        'recommandation', 'objectif', 'potentiel', 'opportunité'
    }

    NEGATIVE_WORDS = {
        'sell', 'bearish', 'loss', 'decline', 'down', 'fall', 'drop', 'crash',
        'weak', 'miss', 'underperform', 'downgrade', 'negative', 'risk',
        'vente', 'baisse', 'perte', 'chute', 'risque', 'dette', 'inquiétude'
    }

    def analyze(self, text: str) -> tuple[float, SentimentLabel]:
        """Analyse simple par comptage de mots."""
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))

        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)

        total = positive_count + negative_count
        if total == 0:
            return 0, SentimentLabel.NEUTRAL

        score = (positive_count - negative_count) / total

        if score > 0.3:
            label = SentimentLabel.BULLISH
        elif score < -0.3:
            label = SentimentLabel.BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        return score, label


class SentimentAnalyzer:
    """Orchestrateur d'analyse de sentiment."""

    def __init__(
        self,
        reddit_client_id: str = None,
        reddit_client_secret: str = None,
        ollama_model: str = None
    ):
        self.news_scraper = GoogleNewsScraper()
        self.reddit_scraper = RedditScraper(reddit_client_id, reddit_client_secret)
        self.llm_analyzer = OllamaSentimentAnalyzer(ollama_model)
        self.simple_analyzer = SimpleSentimentAnalyzer()

    def analyze(
        self,
        ticker: str,
        company_name: str,
        use_llm: bool = True,
        max_news: int = 10,
        max_reddit: int = 15
    ) -> SentimentAnalysis:
        """
        Analyse complète du sentiment pour une action.

        Args:
            ticker: Symbole de l'action
            company_name: Nom de l'entreprise
            use_llm: Utiliser le LLM pour l'analyse
            max_news: Nombre max d'articles
            max_reddit: Nombre max de posts Reddit

        Returns:
            SentimentAnalysis avec score et détails
        """
        news_articles = []
        social_posts = []
        news_scores = []
        reddit_scores = []

        # 1. Collecter les news
        try:
            news_articles = self.news_scraper.get_stock_news(
                ticker, company_name, max_news
            )
            logger.info(f"Collecté {len(news_articles)} articles pour {ticker}")
        except Exception as e:
            logger.error(f"Erreur collecte news: {e}")

        # 2. Collecter Reddit
        try:
            social_posts = self.reddit_scraper.get_stock_mentions(
                ticker, company_name, max_reddit
            )
            logger.info(f"Collecté {len(social_posts)} posts Reddit pour {ticker}")
        except Exception as e:
            logger.error(f"Erreur collecte Reddit: {e}")

        # 3. Analyser le sentiment des articles
        use_llm_actual = use_llm and self.llm_analyzer.available

        for article in news_articles:
            text = f"{article.title}. {article.summary or ''}"
            if use_llm_actual:
                score, label, _ = self.llm_analyzer.analyze(text)
            else:
                score, label = self.simple_analyzer.analyze(text)

            article.sentiment_score = score
            article.sentiment_label = label
            if score != 0:
                news_scores.append(score)

        # 4. Analyser le sentiment des posts Reddit
        for post in social_posts:
            text = f"{post.title}. {post.content}"
            if use_llm_actual:
                score, label, _ = self.llm_analyzer.analyze(text)
            else:
                score, label = self.simple_analyzer.analyze(text)

            post.sentiment_score = score
            post.sentiment_label = label
            if score != 0:
                # Pondérer par les upvotes (mais plafonner)
                weight = min(1 + (post.upvotes / 100), 3)
                reddit_scores.extend([score] * int(weight))

        # 5. Calculer les scores moyens
        news_score = sum(news_scores) / len(news_scores) if news_scores else 0
        reddit_score = sum(reddit_scores) / len(reddit_scores) if reddit_scores else 0

        # 6. Score global (news: 60%, reddit: 40%)
        if news_scores and reddit_scores:
            combined_score = news_score * 0.6 + reddit_score * 0.4
        elif news_scores:
            combined_score = news_score
        elif reddit_scores:
            combined_score = reddit_score
        else:
            combined_score = 0

        # Convertir en score 0-100
        score_0_100 = (combined_score + 1) * 50  # -1..+1 -> 0..100

        # Déterminer le label global
        if combined_score > 0.3:
            label = SentimentLabel.BULLISH if combined_score < 0.6 else SentimentLabel.VERY_BULLISH
        elif combined_score < -0.3:
            label = SentimentLabel.BEARISH if combined_score > -0.6 else SentimentLabel.VERY_BEARISH
        else:
            label = SentimentLabel.NEUTRAL

        # Générer le résumé
        summary = self._generate_summary(
            ticker, len(news_articles), len(social_posts),
            news_score, reddit_score, label
        )

        return SentimentAnalysis(
            ticker=ticker,
            score=score_0_100,
            label=label,
            news_score=(news_score + 1) * 50 if news_scores else None,
            news_count=len(news_articles),
            reddit_score=(reddit_score + 1) * 50 if reddit_scores else None,
            reddit_count=len(social_posts),
            news_articles=news_articles,
            social_posts=social_posts,
            llm_used=use_llm_actual,
            summary=summary
        )

    def _generate_summary(
        self,
        ticker: str,
        news_count: int,
        reddit_count: int,
        news_score: float,
        reddit_score: float,
        label: SentimentLabel
    ) -> str:
        """Génère un résumé de l'analyse de sentiment."""
        label_texts = {
            SentimentLabel.VERY_BULLISH: "très positif",
            SentimentLabel.BULLISH: "positif",
            SentimentLabel.NEUTRAL: "neutre",
            SentimentLabel.BEARISH: "négatif",
            SentimentLabel.VERY_BEARISH: "très négatif"
        }

        summary = f"Sentiment {label_texts[label]} pour {ticker}. "
        summary += f"Analysé {news_count} articles et {reddit_count} posts Reddit. "

        if news_count > 0:
            news_sentiment = "positif" if news_score > 0.1 else "négatif" if news_score < -0.1 else "neutre"
            summary += f"Presse: {news_sentiment}. "

        if reddit_count > 0:
            reddit_sentiment = "positif" if reddit_score > 0.1 else "négatif" if reddit_score < -0.1 else "neutre"
            summary += f"Reddit: {reddit_sentiment}."

        return summary


# Instance singleton
sentiment_analyzer = SentimentAnalyzer()


def main():
    """Test du module de sentiment."""
    print("="*60)
    print("TEST MODULE SENTIMENT")
    print("="*60)

    analyzer = SentimentAnalyzer()

    # Test sur une action
    result = analyzer.analyze("MC.PA", "LVMH", use_llm=False, max_news=5, max_reddit=5)

    print(f"\nTicker: {result.ticker}")
    print(f"Score: {result.score:.1f}/100")
    print(f"Label: {result.label.value}")
    print(f"\nNews: {result.news_count} articles (score: {result.news_score:.1f})" if result.news_score else "News: 0 articles")
    print(f"Reddit: {result.reddit_count} posts (score: {result.reddit_score:.1f})" if result.reddit_score else "Reddit: 0 posts")
    print(f"\nRésumé: {result.summary}")

    if result.news_articles:
        print("\n--- Articles ---")
        for article in result.news_articles[:3]:
            sentiment = "+" if article.sentiment_score and article.sentiment_score > 0 else "-" if article.sentiment_score and article.sentiment_score < 0 else "="
            print(f"[{sentiment}] {article.title[:60]}...")


if __name__ == "__main__":
    main()
