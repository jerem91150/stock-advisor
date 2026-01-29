"""
Scraper Yahoo Finance utilisant yfinance
"""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf
from dataclasses import dataclass
from loguru import logger


@dataclass
class StockData:
    """Données complètes d'une action."""
    ticker: str
    name: str
    exchange: str
    currency: str
    country: str
    sector: str
    industry: str
    market_cap: float
    employees: Optional[int]
    website: Optional[str]
    description: Optional[str]

    # Prix actuel
    current_price: float
    previous_close: float
    day_high: float
    day_low: float
    volume: int
    avg_volume: int

    # 52 semaines
    fifty_two_week_high: float
    fifty_two_week_low: float


@dataclass
class FundamentalData:
    """Données fondamentales."""
    ticker: str

    # Valorisation
    pe_ratio: Optional[float]
    forward_pe: Optional[float]
    peg_ratio: Optional[float]
    pb_ratio: Optional[float]
    ps_ratio: Optional[float]
    ev_ebitda: Optional[float]

    # Rentabilité
    roe: Optional[float]
    roa: Optional[float]
    profit_margin: Optional[float]
    operating_margin: Optional[float]
    gross_margin: Optional[float]

    # Croissance
    revenue_growth: Optional[float]
    earnings_growth: Optional[float]

    # Santé financière
    current_ratio: Optional[float]
    quick_ratio: Optional[float]
    debt_to_equity: Optional[float]

    # Dividendes
    dividend_yield: Optional[float]
    dividend_payout_ratio: Optional[float]

    # Autres
    beta: Optional[float]
    eps: Optional[float]
    revenue: Optional[float]
    ebitda: Optional[float]
    free_cash_flow: Optional[float]


class YahooFinanceScraper:
    """Scraper pour données Yahoo Finance via yfinance."""

    # Mapping des indices et leurs constituants
    INDICES = {
        "CAC40": [
            "AI.PA", "AIR.PA", "ALO.PA", "MT.PA", "CS.PA", "BNP.PA", "EN.PA",
            "CAP.PA", "CA.PA", "ACA.PA", "BN.PA", "DSY.PA", "ENGI.PA", "EL.PA",
            "ERF.PA", "RMS.PA", "KER.PA", "LR.PA", "OR.PA", "MC.PA", "ML.PA",
            "ORA.PA", "RI.PA", "PUB.PA", "RNO.PA", "SAF.PA", "SGO.PA", "SAN.PA",
            "SU.PA", "GLE.PA", "STLAP.PA", "STMPA.PA", "TEP.PA", "HO.PA",
            "TTE.PA", "URW.PA", "VIE.PA", "DG.PA", "VIV.PA", "WLN.PA"
        ],
        "SP500": [],  # Sera chargé dynamiquement
        "NASDAQ100": [],  # Sera chargé dynamiquement
    }

    # Actions éligibles PEA (simplification - Euronext Paris)
    PEA_ELIGIBLE_EXCHANGES = ["PAR", "EPA", "Euronext Paris", "Paris"]

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes

    def get_stock_info(self, ticker: str) -> Optional[StockData]:
        """
        Récupère les informations complètes d'une action.

        Args:
            ticker: Symbole de l'action (ex: "AAPL", "MC.PA")

        Returns:
            StockData ou None si erreur
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or "symbol" not in info:
                logger.warning(f"Pas de données pour {ticker}")
                return None

            return StockData(
                ticker=ticker,
                name=info.get("longName") or info.get("shortName", ticker),
                exchange=info.get("exchange", ""),
                currency=info.get("currency", "USD"),
                country=info.get("country", ""),
                sector=info.get("sector", ""),
                industry=info.get("industry", ""),
                market_cap=info.get("marketCap", 0) / 1e6 if info.get("marketCap") else 0,
                employees=info.get("fullTimeEmployees"),
                website=info.get("website"),
                description=info.get("longBusinessSummary"),
                current_price=info.get("currentPrice") or info.get("regularMarketPrice", 0),
                previous_close=info.get("previousClose", 0),
                day_high=info.get("dayHigh", 0),
                day_low=info.get("dayLow", 0),
                volume=info.get("volume", 0),
                avg_volume=info.get("averageVolume", 0),
                fifty_two_week_high=info.get("fiftyTwoWeekHigh", 0),
                fifty_two_week_low=info.get("fiftyTwoWeekLow", 0),
            )
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de {ticker}: {e}")
            return None

    def get_fundamentals(self, ticker: str) -> Optional[FundamentalData]:
        """
        Récupère les données fondamentales d'une action.

        Args:
            ticker: Symbole de l'action

        Returns:
            FundamentalData ou None si erreur
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                return None

            return FundamentalData(
                ticker=ticker,
                # Valorisation
                pe_ratio=info.get("trailingPE"),
                forward_pe=info.get("forwardPE"),
                peg_ratio=info.get("pegRatio"),
                pb_ratio=info.get("priceToBook"),
                ps_ratio=info.get("priceToSalesTrailing12Months"),
                ev_ebitda=info.get("enterpriseToEbitda"),
                # Rentabilité
                roe=info.get("returnOnEquity"),
                roa=info.get("returnOnAssets"),
                profit_margin=info.get("profitMargins"),
                operating_margin=info.get("operatingMargins"),
                gross_margin=info.get("grossMargins"),
                # Croissance
                revenue_growth=info.get("revenueGrowth"),
                earnings_growth=info.get("earningsGrowth"),
                # Santé financière
                current_ratio=info.get("currentRatio"),
                quick_ratio=info.get("quickRatio"),
                debt_to_equity=info.get("debtToEquity"),
                # Dividendes
                dividend_yield=info.get("dividendYield"),
                dividend_payout_ratio=info.get("payoutRatio"),
                # Autres
                beta=info.get("beta"),
                eps=info.get("trailingEps"),
                revenue=info.get("totalRevenue", 0) / 1e6 if info.get("totalRevenue") else None,
                ebitda=info.get("ebitda", 0) / 1e6 if info.get("ebitda") else None,
                free_cash_flow=info.get("freeCashflow", 0) / 1e6 if info.get("freeCashflow") else None,
            )
        except Exception as e:
            logger.error(f"Erreur fondamentaux pour {ticker}: {e}")
            return None

    def get_price_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Récupère l'historique des prix.

        Args:
            ticker: Symbole de l'action
            period: Période (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Intervalle (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame avec colonnes: Open, High, Low, Close, Adj Close, Volume
        """
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"Pas d'historique pour {ticker}")
                return None

            return df
        except Exception as e:
            logger.error(f"Erreur historique pour {ticker}: {e}")
            return None

    def get_dividends(self, ticker: str) -> Optional[pd.Series]:
        """Récupère l'historique des dividendes."""
        try:
            stock = yf.Ticker(ticker)
            dividends = stock.dividends

            if dividends.empty:
                return None

            return dividends
        except Exception as e:
            logger.error(f"Erreur dividendes pour {ticker}: {e}")
            return None

    def get_earnings_dates(self, ticker: str) -> Optional[pd.DataFrame]:
        """Récupère les dates de publication des résultats."""
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar

            if calendar is None or (isinstance(calendar, pd.DataFrame) and calendar.empty):
                return None

            return calendar
        except Exception as e:
            logger.error(f"Erreur calendrier pour {ticker}: {e}")
            return None

    def is_pea_eligible(self, ticker: str) -> bool:
        """
        Vérifie si une action est éligible au PEA.

        Règle simplifiée: Actions cotées sur Euronext Paris
        avec siège social dans l'UE/EEE.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            exchange = info.get("exchange", "")
            country = info.get("country", "")

            # Liste des pays éligibles PEA (UE/EEE + UK pour historique)
            pea_countries = [
                "France", "Germany", "Italy", "Spain", "Netherlands",
                "Belgium", "Portugal", "Austria", "Ireland", "Finland",
                "Luxembourg", "Greece", "Denmark", "Sweden", "Poland",
                "Czech Republic", "Hungary", "Norway", "Iceland"
            ]

            # Vérifier échange Euronext Paris
            is_euronext_paris = any(
                exc in exchange for exc in self.PEA_ELIGIBLE_EXCHANGES
            )

            # Vérifier pays du siège social
            is_eu_country = country in pea_countries

            return is_euronext_paris and is_eu_country
        except Exception:
            return False

    def search_stocks(self, query: str, limit: int = 10) -> list[dict]:
        """
        Recherche des actions par nom ou ticker.

        Note: yfinance ne supporte pas nativement la recherche.
        Cette méthode utilise une approche alternative.
        """
        results = []

        # Essayer le ticker directement
        try:
            stock = yf.Ticker(query.upper())
            info = stock.info

            if info and "symbol" in info:
                results.append({
                    "ticker": info.get("symbol"),
                    "name": info.get("longName") or info.get("shortName", ""),
                    "exchange": info.get("exchange", ""),
                    "type": info.get("quoteType", "")
                })
        except Exception:
            pass

        return results[:limit]

    def get_index_constituents(self, index_name: str) -> list[str]:
        """
        Retourne les constituants d'un indice.

        Args:
            index_name: Nom de l'indice (CAC40, SP500, NASDAQ100)

        Returns:
            Liste des tickers
        """
        if index_name.upper() in self.INDICES:
            return self.INDICES[index_name.upper()]

        # Pour S&P 500 et NASDAQ 100, on peut utiliser des ETF comme proxy
        if index_name.upper() == "SP500":
            # Utiliser SPY holdings ou Wikipedia scraping
            # Pour MVP, retourner une liste partielle
            return self._get_sp500_tickers()

        return []

    def _get_sp500_tickers(self) -> list[str]:
        """
        Récupère les tickers du S&P 500.

        Note: Liste partielle pour MVP, peut être enrichie via scraping Wikipedia.
        """
        # Top 50 du S&P 500 pour le MVP
        return [
            "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B",
            "UNH", "XOM", "JNJ", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK",
            "ABBV", "LLY", "PEP", "KO", "PFE", "COST", "AVGO", "TMO", "MCD",
            "WMT", "CSCO", "ACN", "ABT", "DHR", "BAC", "CRM", "ADBE", "NKE",
            "DIS", "CMCSA", "VZ", "NEE", "INTC", "PM", "WFC", "TXN", "RTX",
            "QCOM", "BMY", "UPS", "HON", "ORCL"
        ]

    def batch_get_stocks(self, tickers: list[str]) -> dict[str, StockData]:
        """
        Récupère les données de plusieurs actions en batch.

        Args:
            tickers: Liste de symboles

        Returns:
            Dict ticker -> StockData
        """
        results = {}

        for ticker in tickers:
            data = self.get_stock_info(ticker)
            if data:
                results[ticker] = data

        return results

    def get_market_summary(self) -> dict:
        """
        Récupère un résumé du marché (indices principaux).

        Returns:
            Dict avec les principaux indices
        """
        indices = {
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones",
            "^IXIC": "NASDAQ",
            "^FCHI": "CAC 40",
            "^GDAXI": "DAX",
            "^FTSE": "FTSE 100"
        }

        summary = {}
        for ticker, name in indices.items():
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                summary[name] = {
                    "price": info.get("regularMarketPrice", 0),
                    "change": info.get("regularMarketChange", 0),
                    "change_percent": info.get("regularMarketChangePercent", 0),
                    "previous_close": info.get("previousClose", 0)
                }
            except Exception as e:
                logger.debug(f"Erreur indice {name}: {e}")

        return summary


# Instance singleton pour utilisation globale
scraper = YahooFinanceScraper()


def main():
    """Test du scraper."""
    # Test avec une action française
    print("=== Test MC.PA (LVMH) ===")
    data = scraper.get_stock_info("MC.PA")
    if data:
        print(f"Nom: {data.name}")
        print(f"Prix: {data.current_price} {data.currency}")
        print(f"Market Cap: {data.market_cap:.2f}M")
        print(f"Secteur: {data.sector}")
        print(f"PEA éligible: {scraper.is_pea_eligible('MC.PA')}")

    print("\n=== Test AAPL (Apple) ===")
    data = scraper.get_stock_info("AAPL")
    if data:
        print(f"Nom: {data.name}")
        print(f"Prix: {data.current_price} {data.currency}")
        print(f"PEA éligible: {scraper.is_pea_eligible('AAPL')}")

    print("\n=== Fondamentaux AAPL ===")
    fundamentals = scraper.get_fundamentals("AAPL")
    if fundamentals:
        print(f"P/E: {fundamentals.pe_ratio}")
        print(f"PEG: {fundamentals.peg_ratio}")
        print(f"ROE: {fundamentals.roe}")

    print("\n=== Résumé du marché ===")
    summary = scraper.get_market_summary()
    for name, data in summary.items():
        print(f"{name}: {data['price']:.2f} ({data['change_percent']:.2f}%)")


if __name__ == "__main__":
    main()
