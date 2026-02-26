"""
ETF Analyzer - Screener et Comparateur d'ETF
Analyse des frais, performance, composition
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def make_tz_naive(dt):
    """Convertit un datetime timezone-aware en naive."""
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def filter_by_date(df: pd.DataFrame, start_date: datetime) -> pd.DataFrame:
    """Filtre un DataFrame par date en gérant les timezones."""
    if df.empty:
        return df
    try:
        # Convertir l'index en naive datetime pour la comparaison
        naive_index = df.index.tz_localize(None) if df.index.tz else df.index
        mask = naive_index >= start_date
        return df[mask]
    except Exception:
        return df


# ETF populaires par catégorie
ETF_UNIVERSE = {
    # World
    'WORLD': [
        ('IWDA.AS', 'iShares Core MSCI World', 'World'),
        ('VWCE.DE', 'Vanguard FTSE All-World', 'World'),
        ('CW8.PA', 'Amundi MSCI World', 'World'),
        ('SWDA.L', 'iShares Core MSCI World', 'World'),
    ],
    # S&P 500
    'SP500': [
        ('SPY', 'SPDR S&P 500', 'USA'),
        ('VOO', 'Vanguard S&P 500', 'USA'),
        ('IVV', 'iShares Core S&P 500', 'USA'),
        ('ESE.PA', 'BNP Paribas Easy S&P 500', 'USA'),
        ('500.PA', 'Amundi S&P 500', 'USA'),
    ],
    # NASDAQ
    'NASDAQ': [
        ('QQQ', 'Invesco QQQ Trust', 'USA Tech'),
        ('EQQQ.DE', 'Invesco EQQQ NASDAQ-100', 'USA Tech'),
        ('UST.PA', 'Lyxor Nasdaq-100', 'USA Tech'),
    ],
    # Europe
    'EUROPE': [
        ('VEUR.AS', 'Vanguard FTSE Developed Europe', 'Europe'),
        ('MEUD.PA', 'Amundi MSCI Europe', 'Europe'),
        ('IEUR.AS', 'iShares Core MSCI Europe', 'Europe'),
        ('C6E.PA', 'Amundi Euro Stoxx 50', 'Europe'),
    ],
    # Emerging Markets
    'EMERGING': [
        ('VWO', 'Vanguard FTSE Emerging Markets', 'Emerging'),
        ('IEMG', 'iShares Core MSCI Emerging', 'Emerging'),
        ('AEEM.PA', 'Amundi MSCI Emerging Markets', 'Emerging'),
    ],
    # Dividendes
    'DIVIDENDS': [
        ('VYM', 'Vanguard High Dividend Yield', 'USA Dividends'),
        ('SCHD', 'Schwab US Dividend Equity', 'USA Dividends'),
        ('VHYL.AS', 'Vanguard FTSE All-World High Dividend', 'World Dividends'),
    ],
    # Bonds
    'BONDS': [
        ('BND', 'Vanguard Total Bond Market', 'US Bonds'),
        ('AGG', 'iShares Core US Aggregate Bond', 'US Bonds'),
        ('VAGF.L', 'Vanguard Global Aggregate Bond', 'World Bonds'),
    ],
    # Thématiques
    'TECH': [
        ('VGT', 'Vanguard Information Technology', 'Tech'),
        ('XLK', 'Technology Select Sector SPDR', 'Tech'),
    ],
    'CLEAN_ENERGY': [
        ('ICLN', 'iShares Global Clean Energy', 'Clean Energy'),
        ('QCLN', 'First Trust NASDAQ Clean Edge', 'Clean Energy'),
    ],
}


@dataclass
class ETFInfo:
    """Informations sur un ETF."""
    ticker: str
    name: str
    category: str

    # Frais
    expense_ratio: float  # TER en %
    aum: float  # Assets Under Management en millions

    # Performance
    perf_1y: float
    perf_3y: float
    perf_5y: float
    perf_ytd: float

    # Caractéristiques
    dividend_yield: float
    tracking_error: float
    currency: str
    exchange: str

    # Réplication
    replication_method: str  # Physical, Synthetic
    distribution: str  # Accumulating, Distributing

    # PEA
    pea_eligible: bool


@dataclass
class ETFComparison:
    """Comparaison entre ETFs."""
    etfs: List[ETFInfo]
    best_fees: str
    best_performance_1y: str
    best_performance_5y: str
    best_aum: str
    recommendation: str
    analysis: List[str]


@dataclass
class FeeAnalysis:
    """Analyse des frais d'un portefeuille."""
    total_value: float
    weighted_ter: float
    annual_fees: float
    fees_over_10y: float
    fees_over_20y: float

    # Détail par position
    position_fees: List[Dict]

    # Alternatives moins chères
    alternatives: List[Dict]

    # Économies potentielles
    potential_savings_10y: float
    potential_savings_20y: float


class ETFAnalyzer:
    """Analyseur d'ETF."""

    def __init__(self):
        self._cache: Dict[str, Tuple[ETFInfo, datetime]] = {}
        self._cache_duration = timedelta(hours=12)

    def get_etf_info(self, ticker: str) -> Optional[ETFInfo]:
        """Récupère les informations d'un ETF."""
        # Vérifier le cache
        now = datetime.now()
        if ticker in self._cache:
            info, timestamp = self._cache[ticker]
            if now - timestamp < self._cache_duration:
                return info

        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            hist = etf.history(period="5y")

            # Expense ratio (TER)
            expense_ratio = info.get('annualReportExpenseRatio')
            if expense_ratio is None:
                # Essayer d'autres champs ou estimer
                expense_ratio = info.get('totalExpenseRatio', 0.002)  # Défaut 0.2%

            expense_ratio = (expense_ratio or 0) * 100  # Convertir en %

            # AUM
            aum = info.get('totalAssets', 0) or 0
            aum = aum / 1e6  # En millions

            # Performance
            if not hist.empty and len(hist) > 0:
                current_price = hist['Close'].iloc[-1]

                # 1 an
                if len(hist) >= 252:
                    price_1y = hist['Close'].iloc[-252]
                    perf_1y = ((current_price / price_1y) - 1) * 100
                else:
                    perf_1y = 0

                # 3 ans
                if len(hist) >= 756:
                    price_3y = hist['Close'].iloc[-756]
                    perf_3y = (((current_price / price_3y) ** (1/3)) - 1) * 100
                else:
                    perf_3y = 0

                # 5 ans
                if len(hist) >= 1260:
                    price_5y = hist['Close'].iloc[0]
                    perf_5y = (((current_price / price_5y) ** (1/5)) - 1) * 100
                else:
                    perf_5y = 0

                # YTD
                year_start = datetime(datetime.now().year, 1, 1)
                ytd_hist = filter_by_date(hist, year_start)
                if len(ytd_hist) > 0:
                    price_ytd_start = ytd_hist['Close'].iloc[0]
                    perf_ytd = ((current_price / price_ytd_start) - 1) * 100
                else:
                    perf_ytd = 0
            else:
                perf_1y = perf_3y = perf_5y = perf_ytd = 0

            # Dividende
            dividend_yield = (info.get('yield', 0) or 0) * 100

            # Déterminer si PEA éligible (heuristique)
            exchange = info.get('exchange', '')
            currency = info.get('currency', 'USD')
            pea_eligible = any(x in ticker.upper() for x in ['.PA', '.AS', '.DE', '.MI', '.BR'])

            # Méthode de réplication (estimation)
            fund_type = info.get('quoteType', '')
            replication_method = "Physical"  # Défaut

            # Distribution
            if dividend_yield > 0.5:
                distribution = "Distributing"
            else:
                distribution = "Accumulating"

            etf_info = ETFInfo(
                ticker=ticker,
                name=info.get('shortName') or info.get('longName') or ticker,
                category=self._guess_category(ticker, info),
                expense_ratio=expense_ratio,
                aum=aum,
                perf_1y=perf_1y,
                perf_3y=perf_3y,
                perf_5y=perf_5y,
                perf_ytd=perf_ytd,
                dividend_yield=dividend_yield,
                tracking_error=0,  # Difficile à calculer
                currency=currency,
                exchange=exchange,
                replication_method=replication_method,
                distribution=distribution,
                pea_eligible=pea_eligible
            )

            self._cache[ticker] = (etf_info, now)
            return etf_info

        except Exception as e:
            print(f"Erreur récupération ETF {ticker}: {e}")
            return None

    def _guess_category(self, ticker: str, info: Dict) -> str:
        """Devine la catégorie d'un ETF."""
        name = (info.get('shortName') or '').upper()
        ticker = ticker.upper()

        if 'S&P 500' in name or '500' in ticker:
            return 'S&P 500'
        elif 'NASDAQ' in name or 'QQQ' in ticker:
            return 'NASDAQ'
        elif 'WORLD' in name or 'ACWI' in name:
            return 'World'
        elif 'EUROPE' in name or 'STOXX' in name:
            return 'Europe'
        elif 'EMERGING' in name or 'EM' in ticker:
            return 'Emerging Markets'
        elif 'DIVIDEND' in name:
            return 'Dividends'
        elif 'BOND' in name or 'AGG' in ticker or 'BND' in ticker:
            return 'Bonds'
        elif 'TECH' in name:
            return 'Technology'
        else:
            return 'Other'

    def compare_etfs(self, tickers: List[str]) -> Optional[ETFComparison]:
        """Compare plusieurs ETFs."""
        etfs = []
        for ticker in tickers:
            info = self.get_etf_info(ticker)
            if info:
                etfs.append(info)

        if len(etfs) < 2:
            return None

        analysis = []

        # Meilleur frais
        best_fees_etf = min(etfs, key=lambda x: x.expense_ratio)
        best_fees = best_fees_etf.ticker
        analysis.append(f"Frais les plus bas: {best_fees} ({best_fees_etf.expense_ratio:.2f}%)")

        # Meilleure performance 1Y
        best_perf_1y_etf = max(etfs, key=lambda x: x.perf_1y)
        best_performance_1y = best_perf_1y_etf.ticker
        analysis.append(f"Meilleure perf 1 an: {best_performance_1y} ({best_perf_1y_etf.perf_1y:+.1f}%)")

        # Meilleure performance 5Y
        etfs_with_5y = [e for e in etfs if e.perf_5y != 0]
        if etfs_with_5y:
            best_perf_5y_etf = max(etfs_with_5y, key=lambda x: x.perf_5y)
            best_performance_5y = best_perf_5y_etf.ticker
            analysis.append(f"Meilleure perf 5 ans: {best_performance_5y} ({best_perf_5y_etf.perf_5y:+.1f}%/an)")
        else:
            best_performance_5y = tickers[0]

        # Plus gros AUM (plus liquide)
        best_aum_etf = max(etfs, key=lambda x: x.aum)
        best_aum = best_aum_etf.ticker
        analysis.append(f"Plus gros encours: {best_aum} ({best_aum_etf.aum:,.0f}M)")

        # Recommandation
        # Score combiné: faibles frais + bonne perf + gros AUM
        scores = {}
        for etf in etfs:
            score = 0
            # Frais (inverse, max 40 points)
            max_ter = max(e.expense_ratio for e in etfs)
            score += (1 - etf.expense_ratio / max_ter) * 40 if max_ter > 0 else 20

            # Performance 5Y (max 40 points)
            max_perf = max(e.perf_5y for e in etfs)
            min_perf = min(e.perf_5y for e in etfs)
            if max_perf != min_perf:
                score += ((etf.perf_5y - min_perf) / (max_perf - min_perf)) * 40
            else:
                score += 20

            # AUM (max 20 points)
            max_aum = max(e.aum for e in etfs)
            score += (etf.aum / max_aum) * 20 if max_aum > 0 else 10

            scores[etf.ticker] = score

        recommendation = max(scores, key=scores.get)
        analysis.append(f"Recommandation: {recommendation}")

        return ETFComparison(
            etfs=etfs,
            best_fees=best_fees,
            best_performance_1y=best_performance_1y,
            best_performance_5y=best_performance_5y,
            best_aum=best_aum,
            recommendation=recommendation,
            analysis=analysis
        )

    def analyze_portfolio_fees(
        self,
        positions: List[Dict]  # [{'ticker': str, 'value': float}]
    ) -> FeeAnalysis:
        """Analyse les frais d'un portefeuille et suggère des alternatives."""
        total_value = sum(p.get('value', 0) for p in positions)
        position_fees = []
        total_weighted_ter = 0

        for pos in positions:
            ticker = pos.get('ticker', '')
            value = pos.get('value', 0)
            weight = value / total_value if total_value > 0 else 0

            info = self.get_etf_info(ticker)
            if info:
                ter = info.expense_ratio
            else:
                # Essayer de récupérer les frais via yfinance
                try:
                    stock = yf.Ticker(ticker)
                    ter = (stock.info.get('annualReportExpenseRatio', 0) or 0) * 100
                except:
                    ter = 0  # Actions = pas de TER

            annual_fee = value * (ter / 100)
            total_weighted_ter += weight * ter

            position_fees.append({
                'ticker': ticker,
                'value': value,
                'weight': weight * 100,
                'ter': ter,
                'annual_fee': annual_fee
            })

        annual_fees = total_value * (total_weighted_ter / 100)

        # Projection sur 10 et 20 ans (avec croissance 7%/an)
        fees_10y = sum(annual_fees * (1.07 ** i) for i in range(10))
        fees_20y = sum(annual_fees * (1.07 ** i) for i in range(20))

        # Trouver des alternatives moins chères
        alternatives = []
        for pos in position_fees:
            if pos['ter'] > 0.3:  # Si TER > 0.3%, chercher une alternative
                category = self._guess_category(pos['ticker'], {})
                cheaper = self._find_cheaper_alternative(pos['ticker'], category)
                if cheaper:
                    savings = pos['value'] * ((pos['ter'] - cheaper['ter']) / 100)
                    alternatives.append({
                        'current': pos['ticker'],
                        'current_ter': pos['ter'],
                        'alternative': cheaper['ticker'],
                        'alternative_ter': cheaper['ter'],
                        'annual_savings': savings
                    })

        # Calcul économies potentielles
        annual_savings = sum(a.get('annual_savings', 0) for a in alternatives)
        potential_savings_10y = sum(annual_savings * (1.07 ** i) for i in range(10))
        potential_savings_20y = sum(annual_savings * (1.07 ** i) for i in range(20))

        return FeeAnalysis(
            total_value=total_value,
            weighted_ter=total_weighted_ter,
            annual_fees=annual_fees,
            fees_over_10y=fees_10y,
            fees_over_20y=fees_20y,
            position_fees=position_fees,
            alternatives=alternatives,
            potential_savings_10y=potential_savings_10y,
            potential_savings_20y=potential_savings_20y
        )

    def _find_cheaper_alternative(self, ticker: str, category: str) -> Optional[Dict]:
        """Trouve une alternative moins chère pour un ETF."""
        # Liste d'ETF à faibles frais par catégorie
        low_cost_etfs = {
            'S&P 500': [('VOO', 0.03), ('IVV', 0.03), ('SPY', 0.09)],
            'World': [('VWCE.DE', 0.22), ('IWDA.AS', 0.20)],
            'Europe': [('VEUR.AS', 0.12)],
            'NASDAQ': [('QQQ', 0.20)],
            'Bonds': [('BND', 0.03), ('AGG', 0.03)],
        }

        if category in low_cost_etfs:
            alternatives = low_cost_etfs[category]
            # Retourner le moins cher qui n'est pas le ticker actuel
            for alt_ticker, alt_ter in alternatives:
                if alt_ticker.upper() != ticker.upper():
                    return {'ticker': alt_ticker, 'ter': alt_ter}

        return None

    def get_etf_screener(
        self,
        category: str = None,
        max_ter: float = None,
        min_aum: float = None,
        pea_only: bool = False,
        min_perf_1y: float = None
    ) -> List[ETFInfo]:
        """Screener d'ETF avec filtres."""
        results = []

        # Parcourir l'univers
        categories_to_search = [category] if category else ETF_UNIVERSE.keys()

        for cat in categories_to_search:
            if cat not in ETF_UNIVERSE:
                continue

            for ticker, name, cat_name in ETF_UNIVERSE[cat]:
                info = self.get_etf_info(ticker)
                if not info:
                    continue

                # Appliquer les filtres
                if max_ter is not None and info.expense_ratio > max_ter:
                    continue
                if min_aum is not None and info.aum < min_aum:
                    continue
                if pea_only and not info.pea_eligible:
                    continue
                if min_perf_1y is not None and info.perf_1y < min_perf_1y:
                    continue

                results.append(info)

        # Trier par TER croissant
        results.sort(key=lambda x: x.expense_ratio)

        return results


def get_etf_analyzer() -> ETFAnalyzer:
    """Factory function."""
    return ETFAnalyzer()


if __name__ == "__main__":
    analyzer = ETFAnalyzer()

    print("=" * 70)
    print("TEST SCREENER ETF")
    print("=" * 70)

    # Screener S&P 500
    print("\n📊 ETF S&P 500 (TER < 0.5%):")
    etfs = analyzer.get_etf_screener(category='SP500', max_ter=0.5)
    for etf in etfs[:5]:
        print(f"  {etf.ticker}: {etf.name[:30]} | TER: {etf.expense_ratio:.2f}% | Perf 1Y: {etf.perf_1y:+.1f}%")

    print("\n" + "=" * 70)
    print("TEST COMPARAISON")
    print("=" * 70)

    comparison = analyzer.compare_etfs(['SPY', 'VOO', 'IVV'])
    if comparison:
        print(f"\nComparaison SPY vs VOO vs IVV:")
        for etf in comparison.etfs:
            print(f"  {etf.ticker}: TER {etf.expense_ratio:.2f}% | 1Y: {etf.perf_1y:+.1f}% | AUM: {etf.aum:,.0f}M")
        print(f"\n  Recommandation: {comparison.recommendation}")
        for a in comparison.analysis:
            print(f"  → {a}")

    print("\n" + "=" * 70)
    print("TEST ANALYSE FRAIS PORTEFEUILLE")
    print("=" * 70)

    portfolio = [
        {'ticker': 'SPY', 'value': 10000},
        {'ticker': 'QQQ', 'value': 5000},
        {'ticker': 'VWO', 'value': 3000},
    ]

    fees = analyzer.analyze_portfolio_fees(portfolio)
    print(f"\nValeur totale: {fees.total_value:,.0f}€")
    print(f"TER moyen pondéré: {fees.weighted_ter:.2f}%")
    print(f"Frais annuels: {fees.annual_fees:,.0f}€")
    print(f"Frais sur 10 ans: {fees.fees_over_10y:,.0f}€")
    print(f"Frais sur 20 ans: {fees.fees_over_20y:,.0f}€")

    if fees.alternatives:
        print(f"\nAlternatives moins chères:")
        for alt in fees.alternatives:
            print(f"  {alt['current']} ({alt['current_ter']:.2f}%) → {alt['alternative']} ({alt['alternative_ter']:.2f}%)")
            print(f"    Économie: {alt['annual_savings']:.0f}€/an")
