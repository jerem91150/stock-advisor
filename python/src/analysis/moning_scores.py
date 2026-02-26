"""
Scores style Moning - Score Sûreté Dividende et Score Croissance
Notes sur 20 pour évaluer la qualité des dividendes et le potentiel de croissance
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


def filter_dividends_by_date(dividends: pd.Series, cutoff_date: datetime, after: bool = True) -> pd.Series:
    """Filtre les dividendes par date en gérant les timezones."""
    if dividends.empty:
        return dividends
    try:
        # Convertir l'index en naive datetime pour la comparaison
        naive_index = dividends.index.tz_localize(None) if dividends.index.tz else dividends.index
        if after:
            mask = naive_index >= cutoff_date
        else:
            mask = naive_index < cutoff_date
        return dividends[mask]
    except Exception:
        return dividends


@dataclass
class DividendSafetyScore:
    """Score de sûreté du dividende (0-20)."""
    total_score: float  # Score global 0-20

    # Composantes (chacune 0-4 points)
    payout_ratio_score: float  # Ratio de distribution
    consistency_score: float  # Régularité des versements
    growth_score: float  # Croissance du dividende
    coverage_score: float  # Couverture par les bénéfices
    history_score: float  # Historique de versement

    # Détails
    payout_ratio: Optional[float]
    years_of_dividends: int
    dividend_growth_5y: Optional[float]
    dividend_cuts: int  # Nombre de baisses

    # Interprétation
    rating: str  # Excellent, Bon, Moyen, Risqué, Dangereux
    analysis: List[str]


@dataclass
class GrowthScore:
    """Score de croissance (0-20)."""
    total_score: float  # Score global 0-20

    # Composantes (chacune 0-4 points)
    revenue_growth_score: float
    earnings_growth_score: float
    fcf_growth_score: float
    margin_trend_score: float
    reinvestment_score: float

    # Détails
    revenue_growth_3y: Optional[float]
    earnings_growth_3y: Optional[float]
    fcf_growth_3y: Optional[float]
    gross_margin_trend: str  # improving, stable, declining
    capex_ratio: Optional[float]

    # Interprétation
    rating: str
    analysis: List[str]


@dataclass
class ValuationIndicator:
    """Indicateur de sur/sous-évaluation."""
    current_price: float
    fair_value: float
    fair_value_low: float
    fair_value_high: float

    upside_potential: float  # % de potentiel
    margin_of_safety: float  # Marge de sécurité

    status: str  # SOUS-EVALUE, JUSTE_PRIX, SUREVALUE
    confidence: str  # Haute, Moyenne, Faible

    methods_used: List[str]
    analysis: List[str]


class MoningStyleScorer:
    """Calculateur de scores style Moning."""

    def __init__(self):
        self._cache: Dict[str, Tuple[any, datetime]] = {}
        self._cache_duration = timedelta(hours=4)

    def calculate_dividend_safety_score(self, ticker: str) -> Optional[DividendSafetyScore]:
        """Calcule le score de sûreté du dividende (0-20)."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Récupérer l'historique des dividendes
            dividends = stock.dividends

            analysis = []

            # 1. PAYOUT RATIO (0-4 points)
            payout_ratio = info.get('payoutRatio')
            if payout_ratio:
                payout_ratio = payout_ratio * 100
                if payout_ratio < 30:
                    payout_score = 4
                    analysis.append(f"Payout ratio très conservateur ({payout_ratio:.0f}%)")
                elif payout_ratio < 50:
                    payout_score = 3.5
                    analysis.append(f"Payout ratio sain ({payout_ratio:.0f}%)")
                elif payout_ratio < 70:
                    payout_score = 2.5
                    analysis.append(f"Payout ratio modéré ({payout_ratio:.0f}%)")
                elif payout_ratio < 90:
                    payout_score = 1.5
                    analysis.append(f"Payout ratio élevé ({payout_ratio:.0f}%) - attention")
                else:
                    payout_score = 0.5
                    analysis.append(f"Payout ratio dangereux ({payout_ratio:.0f}%)")
            else:
                payout_score = 2
                payout_ratio = None
                analysis.append("Payout ratio non disponible")

            # 2. CONSISTANCE DES VERSEMENTS (0-4 points)
            years_of_dividends = 0
            dividend_cuts = 0

            if not dividends.empty:
                # Analyser les 10 dernières années
                ten_years_ago = datetime.now() - timedelta(days=365*10)
                recent_divs = filter_dividends_by_date(dividends, ten_years_ago, after=True)

                if len(recent_divs) > 0:
                    # Compter les années avec dividendes
                    years_with_divs = recent_divs.groupby(recent_divs.index.year).sum()
                    years_of_dividends = len(years_with_divs)

                    # Détecter les baisses
                    annual_divs = years_with_divs.values
                    for i in range(1, len(annual_divs)):
                        if annual_divs[i] < annual_divs[i-1] * 0.95:  # Baisse > 5%
                            dividend_cuts += 1

                if years_of_dividends >= 10 and dividend_cuts == 0:
                    consistency_score = 4
                    analysis.append(f"Dividende versé depuis {years_of_dividends} ans sans interruption")
                elif years_of_dividends >= 7 and dividend_cuts <= 1:
                    consistency_score = 3
                    analysis.append(f"{years_of_dividends} ans de dividendes, {dividend_cuts} baisse(s)")
                elif years_of_dividends >= 5:
                    consistency_score = 2
                    analysis.append(f"{years_of_dividends} ans de dividendes")
                elif years_of_dividends >= 3:
                    consistency_score = 1
                    analysis.append(f"Historique court ({years_of_dividends} ans)")
                else:
                    consistency_score = 0.5
                    analysis.append("Historique de dividende insuffisant")
            else:
                consistency_score = 0
                analysis.append("Pas de dividende versé")

            # 3. CROISSANCE DU DIVIDENDE (0-4 points)
            dividend_growth_5y = None
            if not dividends.empty and len(dividends) >= 20:
                five_years_ago = datetime.now() - timedelta(days=365*5)
                old_divs = filter_dividends_by_date(dividends, five_years_ago, after=False)
                recent_divs = filter_dividends_by_date(dividends, five_years_ago, after=True)

                if len(old_divs) > 0 and len(recent_divs) > 0:
                    old_annual = old_divs.groupby(old_divs.index.year).sum().mean()
                    recent_annual = recent_divs.groupby(recent_divs.index.year).sum().mean()

                    if old_annual > 0:
                        dividend_growth_5y = ((recent_annual / old_annual) ** 0.2 - 1) * 100

                        if dividend_growth_5y >= 10:
                            growth_score = 4
                            analysis.append(f"Excellente croissance du dividende (+{dividend_growth_5y:.1f}%/an)")
                        elif dividend_growth_5y >= 5:
                            growth_score = 3
                            analysis.append(f"Bonne croissance du dividende (+{dividend_growth_5y:.1f}%/an)")
                        elif dividend_growth_5y >= 0:
                            growth_score = 2
                            analysis.append(f"Dividende stable (+{dividend_growth_5y:.1f}%/an)")
                        else:
                            growth_score = 1
                            analysis.append(f"Dividende en baisse ({dividend_growth_5y:.1f}%/an)")
                    else:
                        growth_score = 2
                else:
                    growth_score = 2
            else:
                growth_score = 2

            # 4. COUVERTURE PAR LES BÉNÉFICES (0-4 points)
            eps = info.get('trailingEps', 0) or 0
            dividend_rate = info.get('dividendRate', 0) or 0

            if eps > 0 and dividend_rate > 0:
                coverage = eps / dividend_rate
                if coverage >= 3:
                    coverage_score = 4
                    analysis.append(f"Excellente couverture ({coverage:.1f}x les bénéfices)")
                elif coverage >= 2:
                    coverage_score = 3
                    analysis.append(f"Bonne couverture ({coverage:.1f}x)")
                elif coverage >= 1.5:
                    coverage_score = 2
                    analysis.append(f"Couverture acceptable ({coverage:.1f}x)")
                elif coverage >= 1:
                    coverage_score = 1
                    analysis.append(f"Couverture limite ({coverage:.1f}x)")
                else:
                    coverage_score = 0
                    analysis.append(f"Dividende non couvert par les bénéfices!")
            else:
                coverage_score = 2

            # 5. HISTORIQUE ET RÉPUTATION (0-4 points)
            # Basé sur la market cap et l'ancienneté
            market_cap = info.get('marketCap', 0) or 0

            if market_cap >= 100e9 and years_of_dividends >= 10:  # Large cap, long history
                history_score = 4
                analysis.append("Dividend aristocrat potentiel")
            elif market_cap >= 10e9 and years_of_dividends >= 5:
                history_score = 3
                analysis.append("Entreprise établie avec historique solide")
            elif market_cap >= 1e9:
                history_score = 2
            else:
                history_score = 1

            # SCORE TOTAL
            total_score = payout_score + consistency_score + growth_score + coverage_score + history_score

            # RATING
            if total_score >= 17:
                rating = "Excellent"
            elif total_score >= 14:
                rating = "Bon"
            elif total_score >= 10:
                rating = "Moyen"
            elif total_score >= 6:
                rating = "Risqué"
            else:
                rating = "Dangereux"

            return DividendSafetyScore(
                total_score=total_score,
                payout_ratio_score=payout_score,
                consistency_score=consistency_score,
                growth_score=growth_score,
                coverage_score=coverage_score,
                history_score=history_score,
                payout_ratio=payout_ratio,
                years_of_dividends=years_of_dividends,
                dividend_growth_5y=dividend_growth_5y,
                dividend_cuts=dividend_cuts,
                rating=rating,
                analysis=analysis
            )

        except Exception as e:
            print(f"Erreur calcul dividend safety {ticker}: {e}")
            return None

    def calculate_growth_score(self, ticker: str) -> Optional[GrowthScore]:
        """Calcule le score de croissance (0-20)."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            analysis = []

            # Récupérer les financials
            try:
                financials = stock.financials
                quarterly = stock.quarterly_financials
            except:
                financials = pd.DataFrame()
                quarterly = pd.DataFrame()

            # 1. CROISSANCE DU CHIFFRE D'AFFAIRES (0-4 points)
            revenue_growth = info.get('revenueGrowth')
            revenue_growth_3y = None

            if revenue_growth:
                revenue_growth_3y = revenue_growth * 100
                if revenue_growth_3y >= 20:
                    revenue_score = 4
                    analysis.append(f"Croissance CA exceptionnelle (+{revenue_growth_3y:.1f}%)")
                elif revenue_growth_3y >= 10:
                    revenue_score = 3
                    analysis.append(f"Forte croissance CA (+{revenue_growth_3y:.1f}%)")
                elif revenue_growth_3y >= 5:
                    revenue_score = 2.5
                    analysis.append(f"Croissance CA modérée (+{revenue_growth_3y:.1f}%)")
                elif revenue_growth_3y >= 0:
                    revenue_score = 1.5
                    analysis.append(f"CA stable (+{revenue_growth_3y:.1f}%)")
                else:
                    revenue_score = 0.5
                    analysis.append(f"CA en déclin ({revenue_growth_3y:.1f}%)")
            else:
                revenue_score = 2
                analysis.append("Croissance CA non disponible")

            # 2. CROISSANCE DES BÉNÉFICES (0-4 points)
            earnings_growth = info.get('earningsGrowth')
            earnings_growth_3y = None

            if earnings_growth:
                earnings_growth_3y = earnings_growth * 100
                if earnings_growth_3y >= 25:
                    earnings_score = 4
                    analysis.append(f"Croissance bénéfices exceptionnelle (+{earnings_growth_3y:.1f}%)")
                elif earnings_growth_3y >= 15:
                    earnings_score = 3
                    analysis.append(f"Forte croissance bénéfices (+{earnings_growth_3y:.1f}%)")
                elif earnings_growth_3y >= 5:
                    earnings_score = 2
                    analysis.append(f"Croissance bénéfices modérée (+{earnings_growth_3y:.1f}%)")
                elif earnings_growth_3y >= 0:
                    earnings_score = 1.5
                    analysis.append(f"Bénéfices stables (+{earnings_growth_3y:.1f}%)")
                else:
                    earnings_score = 0.5
                    analysis.append(f"Bénéfices en déclin ({earnings_growth_3y:.1f}%)")
            else:
                earnings_score = 2

            # 3. FREE CASH FLOW (0-4 points)
            fcf = info.get('freeCashflow')
            operating_cf = info.get('operatingCashflow')
            fcf_growth_3y = None

            if fcf and fcf > 0:
                # Comparer au market cap pour le FCF yield
                market_cap = info.get('marketCap', 1)
                fcf_yield = (fcf / market_cap) * 100 if market_cap > 0 else 0

                if fcf_yield >= 8:
                    fcf_score = 4
                    analysis.append(f"FCF yield excellent ({fcf_yield:.1f}%)")
                elif fcf_yield >= 5:
                    fcf_score = 3
                    analysis.append(f"Bon FCF yield ({fcf_yield:.1f}%)")
                elif fcf_yield >= 3:
                    fcf_score = 2
                    analysis.append(f"FCF yield correct ({fcf_yield:.1f}%)")
                else:
                    fcf_score = 1.5
            elif fcf and fcf < 0:
                fcf_score = 0.5
                analysis.append("Free Cash Flow négatif")
            else:
                fcf_score = 2

            # 4. TENDANCE DES MARGES (0-4 points)
            gross_margin = info.get('grossMargins')
            operating_margin = info.get('operatingMargins')
            profit_margin = info.get('profitMargins')

            margin_trend = "stable"

            if gross_margin and operating_margin:
                # Score basé sur les marges absolues
                if operating_margin > 0.25:
                    margin_score = 4
                    analysis.append(f"Marges exceptionnelles (op: {operating_margin*100:.1f}%)")
                elif operating_margin > 0.15:
                    margin_score = 3
                    analysis.append(f"Bonnes marges (op: {operating_margin*100:.1f}%)")
                elif operating_margin > 0.08:
                    margin_score = 2
                    analysis.append(f"Marges correctes (op: {operating_margin*100:.1f}%)")
                elif operating_margin > 0:
                    margin_score = 1
                    analysis.append(f"Marges faibles (op: {operating_margin*100:.1f}%)")
                else:
                    margin_score = 0
                    analysis.append("Marges négatives")
            else:
                margin_score = 2

            # 5. RÉINVESTISSEMENT (0-4 points)
            # R&D, CapEx comme % du CA
            capex_ratio = None

            # Utiliser le payout ratio inverse comme proxy
            payout = info.get('payoutRatio', 0.5) or 0.5
            retention_rate = 1 - payout

            roe = info.get('returnOnEquity', 0) or 0

            # Sustainable growth rate = ROE * retention rate
            if roe > 0 and retention_rate > 0:
                sustainable_growth = roe * retention_rate * 100

                if sustainable_growth >= 15:
                    reinvest_score = 4
                    analysis.append(f"Fort potentiel de croissance interne ({sustainable_growth:.1f}%)")
                elif sustainable_growth >= 10:
                    reinvest_score = 3
                elif sustainable_growth >= 5:
                    reinvest_score = 2
                else:
                    reinvest_score = 1
            else:
                reinvest_score = 2

            # SCORE TOTAL
            total_score = revenue_score + earnings_score + fcf_score + margin_score + reinvest_score

            # RATING
            if total_score >= 17:
                rating = "Croissance exceptionnelle"
            elif total_score >= 14:
                rating = "Forte croissance"
            elif total_score >= 10:
                rating = "Croissance modérée"
            elif total_score >= 6:
                rating = "Croissance faible"
            else:
                rating = "En déclin"

            return GrowthScore(
                total_score=total_score,
                revenue_growth_score=revenue_score,
                earnings_growth_score=earnings_score,
                fcf_growth_score=fcf_score,
                margin_trend_score=margin_score,
                reinvestment_score=reinvest_score,
                revenue_growth_3y=revenue_growth_3y,
                earnings_growth_3y=earnings_growth_3y,
                fcf_growth_3y=fcf_growth_3y,
                gross_margin_trend=margin_trend,
                capex_ratio=capex_ratio,
                rating=rating,
                analysis=analysis
            )

        except Exception as e:
            print(f"Erreur calcul growth score {ticker}: {e}")
            return None

    def calculate_valuation_indicator(self, ticker: str) -> Optional[ValuationIndicator]:
        """Calcule l'indicateur de sur/sous-évaluation."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
            if not current_price:
                return None

            analysis = []
            methods_used = []
            fair_values = []

            # 1. MÉTHODE P/E (vs secteur)
            pe = info.get('trailingPE')
            forward_pe = info.get('forwardPE')
            sector_pe = info.get('sectorPE', 20)  # Défaut 20
            eps = info.get('trailingEps', 0)

            if pe and eps and eps > 0:
                # Fair value basée sur PE moyen du secteur
                fair_pe = min(pe * 0.8 + sector_pe * 0.2, 25)  # Plafonner à 25
                fv_pe = eps * fair_pe
                fair_values.append(fv_pe)
                methods_used.append(f"P/E ({fair_pe:.1f}x)")

                if pe < 15:
                    analysis.append(f"P/E attractif ({pe:.1f}x)")
                elif pe > 30:
                    analysis.append(f"P/E élevé ({pe:.1f}x)")

            # 2. MÉTHODE PEG
            peg = info.get('pegRatio')
            earnings_growth = info.get('earningsGrowth', 0.1) or 0.1

            if peg and peg > 0 and eps and eps > 0:
                # Fair PEG = 1
                fair_growth_pe = earnings_growth * 100 * 1  # PEG = 1
                fv_peg = eps * min(fair_growth_pe, 30)
                if fv_peg > 0:
                    fair_values.append(fv_peg)
                    methods_used.append("PEG")

                if peg < 1:
                    analysis.append(f"PEG attractif ({peg:.2f})")
                elif peg > 2:
                    analysis.append(f"PEG élevé ({peg:.2f})")

            # 3. MÉTHODE DCF SIMPLIFIÉ (FCF Yield)
            fcf = info.get('freeCashflow')
            shares = info.get('sharesOutstanding')

            if fcf and shares and fcf > 0:
                fcf_per_share = fcf / shares
                # Fair value si FCF yield = 5%
                fv_fcf = fcf_per_share / 0.05
                fair_values.append(fv_fcf)
                methods_used.append("DCF (FCF)")

            # 4. MÉTHODE BOOK VALUE
            book_value = info.get('bookValue')
            roe = info.get('returnOnEquity', 0) or 0

            if book_value and book_value > 0:
                # Multiplier BV par ROE relative
                pb_fair = max(1, min(roe * 10, 5)) if roe > 0 else 1
                fv_bv = book_value * pb_fair
                fair_values.append(fv_bv)
                methods_used.append(f"P/B ({pb_fair:.1f}x)")

            # CALCULER FAIR VALUE MOYENNE
            if not fair_values:
                return None

            fair_value = np.median(fair_values)
            fair_value_low = np.percentile(fair_values, 25) * 0.9
            fair_value_high = np.percentile(fair_values, 75) * 1.1

            # POTENTIEL ET MARGE DE SÉCURITÉ
            upside_potential = ((fair_value / current_price) - 1) * 100
            margin_of_safety = ((fair_value_low / current_price) - 1) * 100

            # STATUS
            if current_price < fair_value_low:
                status = "SOUS-EVALUE"
                analysis.append(f"Prix actuel {((fair_value/current_price)-1)*100:.0f}% sous la fair value")
            elif current_price > fair_value_high:
                status = "SUREVALUE"
                analysis.append(f"Prix actuel {((current_price/fair_value)-1)*100:.0f}% au-dessus de la fair value")
            else:
                status = "JUSTE_PRIX"
                analysis.append("Prix proche de la fair value")

            # CONFIANCE
            if len(methods_used) >= 3:
                confidence = "Haute"
            elif len(methods_used) >= 2:
                confidence = "Moyenne"
            else:
                confidence = "Faible"

            return ValuationIndicator(
                current_price=current_price,
                fair_value=fair_value,
                fair_value_low=fair_value_low,
                fair_value_high=fair_value_high,
                upside_potential=upside_potential,
                margin_of_safety=margin_of_safety,
                status=status,
                confidence=confidence,
                methods_used=methods_used,
                analysis=analysis
            )

        except Exception as e:
            print(f"Erreur calcul valuation {ticker}: {e}")
            return None

    def get_full_moning_analysis(self, ticker: str) -> Dict:
        """Retourne l'analyse complète style Moning."""
        dividend_score = self.calculate_dividend_safety_score(ticker)
        growth_score = self.calculate_growth_score(ticker)
        valuation = self.calculate_valuation_indicator(ticker)

        return {
            'ticker': ticker,
            'dividend_safety': dividend_score,
            'growth': growth_score,
            'valuation': valuation,
            'timestamp': datetime.now().isoformat()
        }


def get_moning_scorer() -> MoningStyleScorer:
    """Factory function."""
    return MoningStyleScorer()


if __name__ == "__main__":
    scorer = MoningStyleScorer()

    # Test sur quelques actions
    test_tickers = ["AAPL", "KO", "JNJ", "MSFT", "TTE.PA"]

    for ticker in test_tickers:
        print(f"\n{'='*60}")
        print(f"ANALYSE {ticker}")
        print('='*60)

        # Dividend Safety
        div_score = scorer.calculate_dividend_safety_score(ticker)
        if div_score:
            print(f"\n📊 SCORE SÛRETÉ DIVIDENDE: {div_score.total_score:.1f}/20 ({div_score.rating})")
            print(f"   - Payout ratio: {div_score.payout_ratio_score:.1f}/4")
            print(f"   - Consistance: {div_score.consistency_score:.1f}/4")
            print(f"   - Croissance div: {div_score.growth_score:.1f}/4")
            print(f"   - Couverture: {div_score.coverage_score:.1f}/4")
            print(f"   - Historique: {div_score.history_score:.1f}/4")
            for a in div_score.analysis[:3]:
                print(f"   → {a}")

        # Growth Score
        growth = scorer.calculate_growth_score(ticker)
        if growth:
            print(f"\n📈 SCORE CROISSANCE: {growth.total_score:.1f}/20 ({growth.rating})")
            print(f"   - CA: {growth.revenue_growth_score:.1f}/4")
            print(f"   - Bénéfices: {growth.earnings_growth_score:.1f}/4")
            print(f"   - FCF: {growth.fcf_growth_score:.1f}/4")
            print(f"   - Marges: {growth.margin_trend_score:.1f}/4")
            print(f"   - Réinvestissement: {growth.reinvestment_score:.1f}/4")

        # Valuation
        valuation = scorer.calculate_valuation_indicator(ticker)
        if valuation:
            print(f"\n💰 VALORISATION: {valuation.status}")
            print(f"   Prix actuel: {valuation.current_price:.2f}")
            print(f"   Fair value: {valuation.fair_value:.2f} [{valuation.fair_value_low:.2f} - {valuation.fair_value_high:.2f}]")
            print(f"   Potentiel: {valuation.upside_potential:+.1f}%")
            print(f"   Méthodes: {', '.join(valuation.methods_used)}")
