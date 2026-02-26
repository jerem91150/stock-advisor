"""
Smart Money Tracker - Suivi des positions des grands investisseurs.

Ce module permet de :
- Scraper les filings 13F de la SEC (positions institutionnelles US)
- Suivre les positions des superinvestisseurs via DataRoma
- Analyser les mouvements des "gourous" (Buffett, Dalio, Burry, etc.)
- Calculer un score Smart Money
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import time
import re

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PositionChange(Enum):
    """Type de changement de position."""
    NEW = "new"           # Nouvelle position
    INCREASED = "increased"  # Position augmentee
    DECREASED = "decreased"  # Position reduite
    SOLD = "sold"         # Position vendue
    UNCHANGED = "unchanged"  # Inchange


@dataclass
class GuruPosition:
    """Position d'un gourou sur une action."""
    guru_name: str
    ticker: str
    company_name: str
    shares: int
    value_usd: float
    portfolio_percent: float
    change: PositionChange
    change_percent: Optional[float] = None
    quarter: str = ""  # ex: "Q4 2024"
    filing_date: Optional[datetime] = None


@dataclass
class GuruProfile:
    """Profil d'un gourou/investisseur."""
    name: str
    fund_name: str
    portfolio_value: float
    num_holdings: int
    top_holdings: list = field(default_factory=list)
    last_update: Optional[datetime] = None


@dataclass
class SmartMoneyAnalysis:
    """Resultat de l'analyse Smart Money pour une action."""
    ticker: str
    guru_positions: list  # Liste de GuruPosition
    total_gurus_holding: int
    recent_buyers: list  # Gourous qui ont augmente
    recent_sellers: list  # Gourous qui ont reduit
    avg_portfolio_weight: float
    conviction_score: float  # Score 0-100
    signal: str  # "strong_buy", "buy", "neutral", "sell"
    summary: str


class DataRomaScraper:
    """
    Scraper pour DataRoma - suivi des superinvestisseurs.
    DataRoma agrege les filings 13F des grands investisseurs.
    """

    BASE_URL = "https://www.dataroma.com/m"

    # Liste des gourous suivis avec leurs identifiants DataRoma
    GURUS = {
        "Warren Buffett": "BRK",
        "Ray Dalio": "BRIDGEWATER",
        "Michael Burry": "SCION",
        "Bill Ackman": "PSH",
        "Seth Klarman": "BAUPOST",
        "David Tepper": "APPALOOSA",
        "Carl Icahn": "ICAHN",
        "Howard Marks": "OAKTREE",
        "Joel Greenblatt": "GOTHAM",
        "Mohnish Pabrai": "PABRAI",
        "Guy Spier": "AQUAMARINE",
        "Li Lu": "HIMALAYA",
        "Chuck Akre": "AKRE",
        "Terry Smith": "FUNDSMITH",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_superinvestor_holdings(self, ticker: str) -> list:
        """
        Recupere tous les superinvestisseurs qui detiennent une action.

        Args:
            ticker: Symbole de l'action (ex: AAPL)

        Returns:
            Liste de GuruPosition
        """
        positions = []

        try:
            # Page des holdings par action
            url = f"{self.BASE_URL}/stock.php?sym={ticker}"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                logger.warning(f"DataRoma: erreur {response.status_code} pour {ticker}")
                return positions

            soup = BeautifulSoup(response.text, 'html.parser')

            # Trouver le tableau des holdings
            table = soup.find('table', {'id': 'grid'})
            if not table:
                # Essayer avec la classe
                table = soup.find('table', class_='t1')

            if not table:
                logger.debug(f"Pas de donnees DataRoma pour {ticker}")
                return positions

            rows = table.find_all('tr')[1:]  # Skip header

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    try:
                        guru_name = cols[0].get_text(strip=True)

                        # Extraire les valeurs
                        shares_text = cols[2].get_text(strip=True).replace(',', '')
                        shares = int(float(shares_text)) if shares_text else 0

                        value_text = cols[3].get_text(strip=True).replace('$', '').replace(',', '')
                        value = float(value_text) if value_text else 0

                        pct_text = cols[4].get_text(strip=True).replace('%', '')
                        portfolio_pct = float(pct_text) if pct_text else 0

                        # Determiner le changement
                        change_cell = cols[1] if len(cols) > 1 else None
                        change = self._parse_change(change_cell)

                        positions.append(GuruPosition(
                            guru_name=guru_name,
                            ticker=ticker,
                            company_name="",
                            shares=shares,
                            value_usd=value,
                            portfolio_percent=portfolio_pct,
                            change=change
                        ))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Erreur parsing ligne DataRoma: {e}")
                        continue

        except requests.RequestException as e:
            logger.error(f"Erreur connexion DataRoma: {e}")
        except Exception as e:
            logger.error(f"Erreur DataRoma pour {ticker}: {e}")

        return positions

    def get_guru_portfolio(self, guru_id: str) -> Optional[GuruProfile]:
        """
        Recupere le portefeuille complet d'un gourou.

        Args:
            guru_id: Identifiant DataRoma du gourou

        Returns:
            GuruProfile ou None
        """
        try:
            url = f"{self.BASE_URL}/holdings.php?m={guru_id}"
            response = self.session.get(url, timeout=15)

            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraire les infos du profil
            title = soup.find('h1')
            fund_name = title.get_text(strip=True) if title else guru_id

            # Trouver les stats
            stats_div = soup.find('div', class_='stats')
            portfolio_value = 0
            num_holdings = 0

            if stats_div:
                text = stats_div.get_text()
                # Parser les valeurs
                value_match = re.search(r'\$([0-9,.]+)\s*(B|M)', text)
                if value_match:
                    value = float(value_match.group(1).replace(',', ''))
                    multiplier = 1e9 if value_match.group(2) == 'B' else 1e6
                    portfolio_value = value * multiplier

            # Top holdings
            top_holdings = []
            table = soup.find('table', {'id': 'grid'})
            if table:
                rows = table.find_all('tr')[1:11]  # Top 10
                for row in rows:
                    cols = row.find_all('td')
                    if cols:
                        ticker_link = cols[0].find('a')
                        if ticker_link:
                            top_holdings.append(ticker_link.get_text(strip=True))
                num_holdings = len(table.find_all('tr')) - 1

            return GuruProfile(
                name=guru_id,
                fund_name=fund_name,
                portfolio_value=portfolio_value,
                num_holdings=num_holdings,
                top_holdings=top_holdings,
                last_update=datetime.now()
            )

        except Exception as e:
            logger.error(f"Erreur recuperation portfolio {guru_id}: {e}")
            return None

    def _parse_change(self, cell) -> PositionChange:
        """Parse le type de changement depuis une cellule."""
        if not cell:
            return PositionChange.UNCHANGED

        text = cell.get_text(strip=True).lower()

        if 'new' in text or 'add' in text:
            return PositionChange.NEW
        elif 'buy' in text or '+' in text or 'increase' in text:
            return PositionChange.INCREASED
        elif 'sell' in text or 'reduce' in text or '-' in text:
            return PositionChange.DECREASED
        elif 'sold' in text or 'exit' in text:
            return PositionChange.SOLD

        return PositionChange.UNCHANGED


class SECEdgarScraper:
    """
    Scraper pour les filings 13F de la SEC EDGAR.
    Les 13F sont des declarations trimestrielles obligatoires
    pour les gestionnaires gerant plus de 100M$.
    """

    BASE_URL = "https://www.sec.gov"
    EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"

    # CIK (Central Index Key) des principaux fonds
    FUND_CIKS = {
        "Berkshire Hathaway": "0001067983",
        "Bridgewater": "0001350694",
        "Scion Asset Management": "0001649339",
        "Pershing Square": "0001336528",
        "Baupost Group": "0001061768",
        "Appaloosa": "0001009207",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'StockAdvisor Research Tool contact@example.com',
            'Accept-Encoding': 'gzip, deflate',
        })

    def get_latest_13f(self, cik: str) -> Optional[dict]:
        """
        Recupere le dernier filing 13F d'un fonds.

        Args:
            cik: Central Index Key du fonds

        Returns:
            Dict avec les positions ou None
        """
        try:
            # Rechercher les filings 13F
            search_url = f"{self.BASE_URL}/cgi-bin/browse-edgar"
            params = {
                'action': 'getcompany',
                'CIK': cik,
                'type': '13F-HR',
                'dateb': '',
                'owner': 'include',
                'count': '10',
                'output': 'atom'
            }

            response = self.session.get(search_url, params=params, timeout=15)

            if response.status_code != 200:
                logger.warning(f"SEC EDGAR: erreur {response.status_code}")
                return None

            # Parser le flux Atom pour trouver le dernier filing
            soup = BeautifulSoup(response.text, 'xml')
            entries = soup.find_all('entry')

            if not entries:
                return None

            # Premier entry = plus recent
            latest = entries[0]
            filing_url = latest.find('link')['href'] if latest.find('link') else None

            if filing_url:
                # Recuperer les details du filing
                return self._parse_13f_filing(filing_url)

        except Exception as e:
            logger.error(f"Erreur SEC EDGAR pour CIK {cik}: {e}")

        return None

    def _parse_13f_filing(self, filing_url: str) -> Optional[dict]:
        """Parse un filing 13F complet."""
        try:
            response = self.session.get(filing_url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Trouver le fichier XML des holdings
            xml_link = None
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'infotable' in href.lower() or href.endswith('.xml'):
                    xml_link = self.BASE_URL + href if href.startswith('/') else href
                    break

            if xml_link:
                return self._parse_holdings_xml(xml_link)

        except Exception as e:
            logger.error(f"Erreur parsing filing: {e}")

        return None

    def _parse_holdings_xml(self, xml_url: str) -> Optional[dict]:
        """Parse le XML des holdings."""
        try:
            response = self.session.get(xml_url, timeout=15)
            soup = BeautifulSoup(response.text, 'xml')

            holdings = {}

            # Parser chaque position
            for info_table in soup.find_all('infoTable'):
                try:
                    name = info_table.find('nameOfIssuer')
                    cusip = info_table.find('cusip')
                    value = info_table.find('value')
                    shares = info_table.find('sshPrnamt')

                    if name and value:
                        ticker = self._cusip_to_ticker(cusip.text if cusip else "")
                        holdings[ticker or name.text] = {
                            'name': name.text,
                            'value': int(value.text) * 1000,  # En milliers
                            'shares': int(shares.text) if shares else 0
                        }
                except Exception:
                    continue

            return holdings

        except Exception as e:
            logger.error(f"Erreur parsing XML holdings: {e}")
            return None

    def _cusip_to_ticker(self, cusip: str) -> Optional[str]:
        """Convertit un CUSIP en ticker (simplifi')."""
        # Mapping basique des CUSIP connus
        # En production, utiliser un service comme OpenFIGI
        cusip_map = {
            "037833100": "AAPL",
            "594918104": "MSFT",
            "30303M102": "META",
            "02079K305": "GOOG",
            "023135106": "AMZN",
        }
        return cusip_map.get(cusip)


class SmartMoneyTracker:
    """
    Classe principale pour le tracking Smart Money.
    Combine les donnees de plusieurs sources.
    """

    def __init__(self):
        self.dataroma = DataRomaScraper()
        self.sec_edgar = SECEdgarScraper()

        # Cache pour eviter les requetes repetees
        self._cache = {}
        self._cache_duration = timedelta(hours=6)

    def analyze(self, ticker: str) -> SmartMoneyAnalysis:
        """
        Analyse complete Smart Money pour une action.

        Args:
            ticker: Symbole de l'action

        Returns:
            SmartMoneyAnalysis avec score et details
        """
        # Verifier le cache
        cache_key = f"smart_money_{ticker}"
        if cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_duration:
                return cached

        # Recuperer les positions des gourous
        guru_positions = self.dataroma.get_superinvestor_holdings(ticker)

        # Analyser les positions
        total_gurus = len(guru_positions)
        recent_buyers = []
        recent_sellers = []

        total_weight = 0

        for pos in guru_positions:
            if pos.change in [PositionChange.NEW, PositionChange.INCREASED]:
                recent_buyers.append(pos.guru_name)
            elif pos.change in [PositionChange.DECREASED, PositionChange.SOLD]:
                recent_sellers.append(pos.guru_name)

            total_weight += pos.portfolio_percent

        avg_weight = total_weight / total_gurus if total_gurus > 0 else 0

        # Calculer le score de conviction
        conviction_score = self._calculate_conviction_score(
            total_gurus, recent_buyers, recent_sellers, avg_weight
        )

        # Determiner le signal
        signal = self._determine_signal(conviction_score, recent_buyers, recent_sellers)

        # Generer le resume
        summary = self._generate_summary(
            ticker, total_gurus, recent_buyers, recent_sellers, conviction_score
        )

        analysis = SmartMoneyAnalysis(
            ticker=ticker,
            guru_positions=guru_positions,
            total_gurus_holding=total_gurus,
            recent_buyers=recent_buyers,
            recent_sellers=recent_sellers,
            avg_portfolio_weight=avg_weight,
            conviction_score=conviction_score,
            signal=signal,
            summary=summary
        )

        # Mettre en cache
        self._cache[cache_key] = (analysis, datetime.now())

        return analysis

    def _calculate_conviction_score(
        self,
        total_gurus: int,
        buyers: list,
        sellers: list,
        avg_weight: float
    ) -> float:
        """
        Calcule un score de conviction 0-100.

        Facteurs:
        - Nombre de gourous detenant l'action (max 30 pts)
        - Ratio acheteurs/vendeurs (max 40 pts)
        - Poids moyen dans les portefeuilles (max 30 pts)
        """
        score = 0

        # Score nombre de gourous (0-30)
        # 1 gourou = 5pts, max 30pts a 6+ gourous
        guru_score = min(30, total_gurus * 5)
        score += guru_score

        # Score momentum acheteurs/vendeurs (0-40)
        num_buyers = len(buyers)
        num_sellers = len(sellers)

        if num_buyers + num_sellers > 0:
            buyer_ratio = num_buyers / (num_buyers + num_sellers)
            momentum_score = buyer_ratio * 40
        else:
            momentum_score = 20  # Neutre si pas de changement
        score += momentum_score

        # Score poids moyen (0-30)
        # 1% = 10pts, max 30pts a 3%+
        weight_score = min(30, avg_weight * 10)
        score += weight_score

        return min(100, score)

    def _determine_signal(
        self,
        score: float,
        buyers: list,
        sellers: list
    ) -> str:
        """Determine le signal basé sur le score et les mouvements."""
        num_buyers = len(buyers)
        num_sellers = len(sellers)

        # Strong buy: score eleve + plus d'acheteurs que vendeurs
        if score >= 70 and num_buyers > num_sellers:
            return "strong_buy"

        # Buy: score correct + pas trop de vendeurs
        if score >= 50 and num_buyers >= num_sellers:
            return "buy"

        # Sell: beaucoup de vendeurs
        if num_sellers > num_buyers * 2:
            return "sell"

        return "neutral"

    def _generate_summary(
        self,
        ticker: str,
        total_gurus: int,
        buyers: list,
        sellers: list,
        score: float
    ) -> str:
        """Genere un resume textuel de l'analyse."""
        parts = []

        if total_gurus == 0:
            return f"Aucun superinvestisseur connu ne detient {ticker} actuellement."

        parts.append(f"{total_gurus} superinvestisseur(s) detiennent {ticker}.")

        if buyers:
            parts.append(f"Acheteurs recents: {', '.join(buyers[:3])}.")

        if sellers:
            parts.append(f"Vendeurs recents: {', '.join(sellers[:3])}.")

        if score >= 70:
            parts.append("Forte conviction du Smart Money.")
        elif score >= 50:
            parts.append("Conviction moderee du Smart Money.")
        else:
            parts.append("Faible interet du Smart Money.")

        return " ".join(parts)

    def get_most_held_stocks(self, top_n: int = 20) -> list:
        """
        Recupere les actions les plus detenues par les superinvestisseurs.

        Returns:
            Liste de tuples (ticker, nombre_de_gourous)
        """
        try:
            url = f"{self.dataroma.BASE_URL}/home.php"
            response = self.dataroma.session.get(url, timeout=15)

            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Trouver le tableau des stocks populaires
            results = []
            table = soup.find('table', {'id': 'grid'})

            if table:
                rows = table.find_all('tr')[1:top_n+1]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ticker_link = cols[0].find('a')
                        if ticker_link:
                            ticker = ticker_link.get_text(strip=True)
                            count_text = cols[1].get_text(strip=True)
                            try:
                                count = int(count_text)
                                results.append((ticker, count))
                            except ValueError:
                                continue

            return results

        except Exception as e:
            logger.error(f"Erreur recuperation stocks populaires: {e}")
            return []

    def get_guru_recent_moves(self, guru_name: str) -> list:
        """
        Recupere les mouvements recents d'un gourou specifique.

        Args:
            guru_name: Nom du gourou (doit etre dans GURUS)

        Returns:
            Liste des GuruPosition avec changements recents
        """
        if guru_name not in self.dataroma.GURUS:
            logger.warning(f"Gourou inconnu: {guru_name}")
            return []

        guru_id = self.dataroma.GURUS[guru_name]
        profile = self.dataroma.get_guru_portfolio(guru_id)

        if not profile:
            return []

        # Recuperer les positions avec changements
        positions = []
        for ticker in profile.top_holdings[:10]:
            pos_list = self.dataroma.get_superinvestor_holdings(ticker)
            for pos in pos_list:
                if guru_name.lower() in pos.guru_name.lower():
                    positions.append(pos)
            time.sleep(0.5)  # Rate limiting

        return positions


def calculate_smart_money_score(analysis: SmartMoneyAnalysis) -> float:
    """
    Calcule le score Smart Money normalise pour l'integration
    dans le score global de l'application.

    Returns:
        Score 0-100
    """
    return analysis.conviction_score


# Exemple d'utilisation
if __name__ == "__main__":
    tracker = SmartMoneyTracker()

    # Test sur Apple
    print("=== Analyse Smart Money AAPL ===")
    analysis = tracker.analyze("AAPL")

    print(f"Gourous detenant AAPL: {analysis.total_gurus_holding}")
    print(f"Acheteurs recents: {analysis.recent_buyers}")
    print(f"Vendeurs recents: {analysis.recent_sellers}")
    print(f"Score conviction: {analysis.conviction_score:.1f}/100")
    print(f"Signal: {analysis.signal}")
    print(f"Resume: {analysis.summary}")

    print("\n=== Stocks les plus detenus ===")
    popular = tracker.get_most_held_stocks(10)
    for ticker, count in popular:
        print(f"  {ticker}: {count} gourous")
