"""
Module de Backtesting Réaliste

Simule un investisseur qui:
- Investit X EUR le 1er de chaque mois (jour de paye)
- Utilise l'algorithme d'analyse pour choisir ses actions
- Réinvestit les dividendes
- Peut vendre si le score devient négatif
- Compare à un benchmark (ETF CAC40, S&P500, ou simple épargne)

Périodes testées: 1 an, 5 ans, 10 ans, 15 ans, 20 ans
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')


class Strategy(Enum):
    """Stratégies de backtest."""
    ALGO_SCORE = "algo_score"  # Notre algorithme
    BUY_AND_HOLD_ETF = "etf"   # ETF CAC40
    RANDOM = "random"          # Achat aléatoire
    SAVINGS_ACCOUNT = "livret" # Livret A (comparaison)


@dataclass
class Position:
    """Position dans le portefeuille."""
    ticker: str
    shares: float
    avg_cost: float
    purchase_date: datetime
    current_price: float = 0.0

    @property
    def value(self) -> float:
        return self.shares * self.current_price

    @property
    def gain_pct(self) -> float:
        if self.avg_cost == 0:
            return 0
        return ((self.current_price / self.avg_cost) - 1) * 100


@dataclass
class Transaction:
    """Transaction (achat/vente)."""
    date: datetime
    ticker: str
    action: str  # "BUY" or "SELL"
    shares: float
    price: float
    total: float
    reason: str


@dataclass
class DividendPayment:
    """Paiement de dividende."""
    date: datetime
    ticker: str
    amount_per_share: float
    shares_held: float
    total: float
    reinvested: bool


@dataclass
class MonthlySnapshot:
    """État du portefeuille à une date donnée."""
    date: datetime
    cash: float
    positions_value: float
    total_value: float
    total_invested: float
    gain_pct: float
    positions: Dict[str, Position]
    dividends_received: float
    benchmark_value: float


@dataclass
class BacktestResult:
    """Résultat complet du backtest."""
    strategy: Strategy
    start_date: datetime
    end_date: datetime
    months: int

    # Investissement
    monthly_investment: float
    total_invested: float

    # Performance finale
    final_value: float
    total_gain: float
    total_gain_pct: float
    annualized_return: float

    # Dividendes
    total_dividends: float
    dividends_reinvested: float

    # Comparaison
    benchmark_final: float
    benchmark_gain_pct: float
    outperformance: float  # vs benchmark

    # Risque
    max_drawdown: float
    volatility: float
    sharpe_ratio: float

    # Détails
    transactions: List[Transaction]
    dividends: List[DividendPayment]
    monthly_snapshots: List[MonthlySnapshot]

    # Positions finales
    final_positions: Dict[str, Position]


class BacktestSimulator:
    """
    Simulateur de backtest réaliste.
    """

    # ETF de référence
    BENCHMARK_ETF = "CAC.PA"  # Lyxor CAC 40
    BACKUP_BENCHMARK = "^FCHI"  # Indice CAC 40

    # Taux Livret A historiques (simplifiés)
    LIVRET_A_RATES = {
        2005: 2.25, 2006: 2.75, 2007: 3.0, 2008: 4.0, 2009: 1.75,
        2010: 1.75, 2011: 2.25, 2012: 2.25, 2013: 1.75, 2014: 1.25,
        2015: 1.0, 2016: 0.75, 2017: 0.75, 2018: 0.75, 2019: 0.75,
        2020: 0.5, 2021: 0.5, 2022: 1.0, 2023: 3.0, 2024: 3.0, 2025: 3.0
    }

    # Actions éligibles PEA (CAC40 simplifié, hors État français)
    ELIGIBLE_STOCKS = [
        'ACA.PA', 'BNP.PA', 'GLE.PA',  # Banques
        'SAN.PA', 'CS.PA',              # Banques/Assurance
        'MC.PA', 'KER.PA', 'RMS.PA',   # Luxe
        'OR.PA', 'RI.PA',               # Consommation
        'SU.PA', 'AI.PA', 'BN.PA',     # Industriels
        'CAP.PA', 'ATO.PA',             # Tech/Services
        'TTE.PA', 'EN.PA',              # Energie/Construction
        'DG.PA', 'SGO.PA',              # Construction/Matériaux
        'VIV.PA', 'PUB.PA',             # Média
    ]

    def __init__(self, monthly_investment: float = 100.0):
        self.monthly_investment = monthly_investment
        self._price_cache = {}
        self._dividend_cache = {}

    def run_backtest(
        self,
        years: int = 5,
        strategy: Strategy = Strategy.ALGO_SCORE,
        end_date: datetime = None,
        sell_threshold: float = 35.0,  # Score sous lequel vendre
        reinvest_dividends: bool = True
    ) -> BacktestResult:
        """
        Lance un backtest complet.

        Args:
            years: Nombre d'années de backtest
            strategy: Stratégie à tester
            end_date: Date de fin (défaut: aujourd'hui)
            sell_threshold: Score sous lequel vendre une position
            reinvest_dividends: Réinvestir les dividendes

        Returns:
            BacktestResult avec tous les détails
        """
        if end_date is None:
            end_date = datetime.now()

        start_date = end_date - relativedelta(years=years)

        print(f"\n{'='*60}")
        print(f"BACKTEST: {strategy.value.upper()}")
        print(f"Periode: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}")
        print(f"Investissement: {self.monthly_investment} EUR/mois")
        print(f"{'='*60}")

        if strategy == Strategy.SAVINGS_ACCOUNT:
            return self._backtest_savings(start_date, end_date, years)
        elif strategy == Strategy.BUY_AND_HOLD_ETF:
            return self._backtest_etf(start_date, end_date, years)
        else:
            return self._backtest_algo(start_date, end_date, years,
                                       sell_threshold, reinvest_dividends)

    def _backtest_algo(
        self,
        start_date: datetime,
        end_date: datetime,
        years: int,
        sell_threshold: float,
        reinvest_dividends: bool
    ) -> BacktestResult:
        """Backtest avec notre algorithme."""

        cash = 0.0
        positions: Dict[str, Position] = {}
        transactions: List[Transaction] = []
        dividends: List[DividendPayment] = []
        snapshots: List[MonthlySnapshot] = []
        total_invested = 0.0
        total_dividends = 0.0

        # Charger les données historiques
        print("Chargement des donnees historiques...")
        historical_data = self._load_historical_data(start_date, end_date)
        benchmark_data = self._load_benchmark_data(start_date, end_date)

        # Simuler mois par mois
        current_date = start_date.replace(day=1)
        month_count = 0

        while current_date <= end_date:
            month_count += 1

            # 1. Ajouter l'investissement mensuel
            cash += self.monthly_investment
            total_invested += self.monthly_investment

            # 2. Collecter les dividendes du mois précédent
            div_received = self._collect_dividends(
                positions, current_date, historical_data, reinvest_dividends
            )
            for div in div_received:
                dividends.append(div)
                total_dividends += div.total
                if reinvest_dividends:
                    cash += div.total

            # 3. Mettre à jour les prix
            self._update_positions_prices(positions, current_date, historical_data)

            # 4. Analyser et décider (vendre les mauvais, acheter les bons)
            # Vendre les positions sous le seuil
            for ticker in list(positions.keys()):
                score = self._calculate_historical_score(ticker, current_date, historical_data)
                if score < sell_threshold and positions[ticker].shares > 0:
                    # Vendre
                    pos = positions[ticker]
                    sell_value = pos.value
                    cash += sell_value
                    transactions.append(Transaction(
                        date=current_date,
                        ticker=ticker,
                        action="SELL",
                        shares=pos.shares,
                        price=pos.current_price,
                        total=sell_value,
                        reason=f"Score {score:.0f} < {sell_threshold}"
                    ))
                    del positions[ticker]

            # 5. Choisir la meilleure action à acheter
            if cash >= 10:  # Minimum pour acheter
                best_ticker, best_score = self._find_best_stock(
                    current_date, historical_data, list(positions.keys())
                )

                if best_ticker and best_score >= 50:
                    price = self._get_price_at_date(best_ticker, current_date, historical_data)
                    if price and price > 0:
                        shares_to_buy = int(cash / price)
                        if shares_to_buy > 0:
                            cost = shares_to_buy * price
                            cash -= cost

                            if best_ticker in positions:
                                # Moyenne à la hausse
                                old_pos = positions[best_ticker]
                                total_shares = old_pos.shares + shares_to_buy
                                avg_cost = ((old_pos.shares * old_pos.avg_cost) + cost) / total_shares
                                positions[best_ticker] = Position(
                                    ticker=best_ticker,
                                    shares=total_shares,
                                    avg_cost=avg_cost,
                                    purchase_date=old_pos.purchase_date,
                                    current_price=price
                                )
                            else:
                                positions[best_ticker] = Position(
                                    ticker=best_ticker,
                                    shares=shares_to_buy,
                                    avg_cost=price,
                                    purchase_date=current_date,
                                    current_price=price
                                )

                            transactions.append(Transaction(
                                date=current_date,
                                ticker=best_ticker,
                                action="BUY",
                                shares=shares_to_buy,
                                price=price,
                                total=cost,
                                reason=f"Score {best_score:.0f}"
                            ))

            # 6. Snapshot mensuel
            positions_value = sum(p.value for p in positions.values())
            total_value = cash + positions_value
            benchmark_value = self._get_benchmark_value(
                current_date, start_date, benchmark_data, total_invested
            )

            snapshots.append(MonthlySnapshot(
                date=current_date,
                cash=cash,
                positions_value=positions_value,
                total_value=total_value,
                total_invested=total_invested,
                gain_pct=((total_value / total_invested) - 1) * 100 if total_invested > 0 else 0,
                positions=dict(positions),
                dividends_received=sum(d.total for d in div_received),
                benchmark_value=benchmark_value
            ))

            if month_count % 12 == 0:
                print(f"  Annee {month_count//12}: Portefeuille = {total_value:.2f} EUR (+{((total_value/total_invested)-1)*100:.1f}%)")

            # Mois suivant
            current_date += relativedelta(months=1)

        # Calculs finaux
        final_value = cash + sum(p.value for p in positions.values())
        total_gain = final_value - total_invested
        total_gain_pct = (total_gain / total_invested) * 100 if total_invested > 0 else 0

        # Rendement annualisé
        if years > 0:
            annualized = ((final_value / total_invested) ** (1 / years) - 1) * 100
        else:
            annualized = 0

        # Benchmark final
        benchmark_final = self._get_benchmark_value(
            end_date, start_date, benchmark_data, total_invested
        )
        benchmark_gain_pct = ((benchmark_final / total_invested) - 1) * 100 if total_invested > 0 else 0

        # Risque
        values = [s.total_value for s in snapshots]
        max_drawdown = self._calculate_max_drawdown(values)
        volatility = self._calculate_volatility(values)
        sharpe = self._calculate_sharpe(values, years)

        return BacktestResult(
            strategy=Strategy.ALGO_SCORE,
            start_date=start_date,
            end_date=end_date,
            months=month_count,
            monthly_investment=self.monthly_investment,
            total_invested=total_invested,
            final_value=final_value,
            total_gain=total_gain,
            total_gain_pct=total_gain_pct,
            annualized_return=annualized,
            total_dividends=total_dividends,
            dividends_reinvested=total_dividends if reinvest_dividends else 0,
            benchmark_final=benchmark_final,
            benchmark_gain_pct=benchmark_gain_pct,
            outperformance=total_gain_pct - benchmark_gain_pct,
            max_drawdown=max_drawdown,
            volatility=volatility,
            sharpe_ratio=sharpe,
            transactions=transactions,
            dividends=dividends,
            monthly_snapshots=snapshots,
            final_positions=positions
        )

    def _backtest_etf(
        self,
        start_date: datetime,
        end_date: datetime,
        years: int
    ) -> BacktestResult:
        """Backtest simple: DCA sur ETF CAC40."""

        benchmark_data = self._load_benchmark_data(start_date, end_date)

        cash = 0.0
        shares = 0.0
        avg_cost = 0.0
        total_invested = 0.0
        snapshots = []
        transactions = []

        current_date = start_date.replace(day=1)
        month_count = 0

        while current_date <= end_date:
            month_count += 1
            cash += self.monthly_investment
            total_invested += self.monthly_investment

            # Prix de l'ETF
            price = self._get_benchmark_price(current_date, benchmark_data)

            if price and price > 0:
                shares_to_buy = cash / price
                if shares > 0:
                    avg_cost = ((shares * avg_cost) + (shares_to_buy * price)) / (shares + shares_to_buy)
                else:
                    avg_cost = price
                shares += shares_to_buy
                cash = 0

                transactions.append(Transaction(
                    date=current_date,
                    ticker="ETF_CAC40",
                    action="BUY",
                    shares=shares_to_buy,
                    price=price,
                    total=shares_to_buy * price,
                    reason="DCA mensuel"
                ))

            total_value = shares * price if price else shares * avg_cost

            snapshots.append(MonthlySnapshot(
                date=current_date,
                cash=0,
                positions_value=total_value,
                total_value=total_value,
                total_invested=total_invested,
                gain_pct=((total_value / total_invested) - 1) * 100 if total_invested > 0 else 0,
                positions={},
                dividends_received=0,
                benchmark_value=total_value
            ))

            current_date += relativedelta(months=1)

        final_price = self._get_benchmark_price(end_date, benchmark_data)
        final_value = shares * final_price if final_price else shares * avg_cost
        total_gain = final_value - total_invested
        total_gain_pct = (total_gain / total_invested) * 100 if total_invested > 0 else 0
        annualized = ((final_value / total_invested) ** (1 / years) - 1) * 100 if years > 0 else 0

        values = [s.total_value for s in snapshots]

        return BacktestResult(
            strategy=Strategy.BUY_AND_HOLD_ETF,
            start_date=start_date,
            end_date=end_date,
            months=month_count,
            monthly_investment=self.monthly_investment,
            total_invested=total_invested,
            final_value=final_value,
            total_gain=total_gain,
            total_gain_pct=total_gain_pct,
            annualized_return=annualized,
            total_dividends=0,
            dividends_reinvested=0,
            benchmark_final=final_value,
            benchmark_gain_pct=total_gain_pct,
            outperformance=0,
            max_drawdown=self._calculate_max_drawdown(values),
            volatility=self._calculate_volatility(values),
            sharpe_ratio=self._calculate_sharpe(values, years),
            transactions=transactions,
            dividends=[],
            monthly_snapshots=snapshots,
            final_positions={}
        )

    def _backtest_savings(
        self,
        start_date: datetime,
        end_date: datetime,
        years: int
    ) -> BacktestResult:
        """Backtest Livret A (épargne sans risque)."""

        total = 0.0
        total_invested = 0.0
        snapshots = []

        current_date = start_date.replace(day=1)
        month_count = 0

        while current_date <= end_date:
            month_count += 1

            # Ajouter investissement mensuel
            total += self.monthly_investment
            total_invested += self.monthly_investment

            # Appliquer intérêts mensuels
            year = current_date.year
            annual_rate = self.LIVRET_A_RATES.get(year, 2.0)
            monthly_rate = annual_rate / 100 / 12
            total *= (1 + monthly_rate)

            snapshots.append(MonthlySnapshot(
                date=current_date,
                cash=total,
                positions_value=0,
                total_value=total,
                total_invested=total_invested,
                gain_pct=((total / total_invested) - 1) * 100,
                positions={},
                dividends_received=0,
                benchmark_value=total
            ))

            current_date += relativedelta(months=1)

        total_gain = total - total_invested
        total_gain_pct = (total_gain / total_invested) * 100
        annualized = ((total / total_invested) ** (1 / years) - 1) * 100 if years > 0 else 0

        return BacktestResult(
            strategy=Strategy.SAVINGS_ACCOUNT,
            start_date=start_date,
            end_date=end_date,
            months=month_count,
            monthly_investment=self.monthly_investment,
            total_invested=total_invested,
            final_value=total,
            total_gain=total_gain,
            total_gain_pct=total_gain_pct,
            annualized_return=annualized,
            total_dividends=0,
            dividends_reinvested=0,
            benchmark_final=total,
            benchmark_gain_pct=total_gain_pct,
            outperformance=0,
            max_drawdown=0,
            volatility=0,
            sharpe_ratio=0,
            transactions=[],
            dividends=[],
            monthly_snapshots=snapshots,
            final_positions={}
        )

    def _load_historical_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Charge les données historiques pour toutes les actions."""
        data = {}

        for ticker in self.ELIGIBLE_STOCKS:
            try:
                df = yf.download(
                    ticker,
                    start=start_date - timedelta(days=30),
                    end=end_date + timedelta(days=5),
                    progress=False
                )
                if not df.empty:
                    data[ticker] = df
            except Exception:
                pass

        print(f"  Donnees chargees pour {len(data)} actions")
        return data

    def _load_benchmark_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Charge les données du benchmark."""
        try:
            df = yf.download(
                self.BENCHMARK_ETF,
                start=start_date - timedelta(days=30),
                end=end_date + timedelta(days=5),
                progress=False
            )
            if df.empty:
                df = yf.download(
                    self.BACKUP_BENCHMARK,
                    start=start_date - timedelta(days=30),
                    end=end_date + timedelta(days=5),
                    progress=False
                )
            return df
        except Exception:
            return pd.DataFrame()

    def _get_price_at_date(
        self,
        ticker: str,
        date: datetime,
        data: Dict[str, pd.DataFrame]
    ) -> Optional[float]:
        """Récupère le prix à une date donnée."""
        if ticker not in data:
            return None

        df = data[ticker]
        # Trouver la date la plus proche
        mask = df.index <= pd.Timestamp(date)
        if mask.any():
            close = df.loc[mask, 'Close'].iloc[-1]
            # Handle both scalar and Series
            if hasattr(close, 'iloc'):
                return float(close.iloc[0])
            return float(close)
        return None

    def _get_benchmark_price(
        self,
        date: datetime,
        data: pd.DataFrame
    ) -> Optional[float]:
        """Récupère le prix du benchmark."""
        if data.empty:
            return None
        mask = data.index <= pd.Timestamp(date)
        if mask.any():
            close = data.loc[mask, 'Close'].iloc[-1]
            if hasattr(close, 'iloc'):
                return float(close.iloc[0])
            return float(close)
        return None

    def _get_benchmark_value(
        self,
        current_date: datetime,
        start_date: datetime,
        data: pd.DataFrame,
        total_invested: float
    ) -> float:
        """Calcule la valeur si on avait investi dans le benchmark."""
        if data.empty:
            return total_invested

        start_price = self._get_benchmark_price(start_date, data)
        current_price = self._get_benchmark_price(current_date, data)

        if start_price and current_price:
            # Simplifié: croissance proportionnelle
            growth = current_price / start_price
            return total_invested * growth

        return total_invested

    def _calculate_historical_score(
        self,
        ticker: str,
        date: datetime,
        data: Dict[str, pd.DataFrame]
    ) -> float:
        """Calcule un score simplifié basé sur les données historiques."""
        if ticker not in data:
            return 50

        df = data[ticker]
        mask = df.index <= pd.Timestamp(date)
        if not mask.any() or mask.sum() < 50:
            return 50

        recent = df.loc[mask].tail(200)
        if len(recent) < 50:
            return 50

        score = 50

        # Tendance (prix vs MA50)
        current = recent['Close'].iloc[-1]
        if hasattr(current, 'iloc'):
            current = float(current.iloc[0])
        else:
            current = float(current)
        ma50 = recent['Close'].tail(50).mean()
        if hasattr(ma50, 'iloc'):
            ma50 = float(ma50.iloc[0])
        else:
            ma50 = float(ma50)

        if current > ma50:
            score += 15
        else:
            score -= 10

        # Momentum (variation 3 mois)
        if len(recent) >= 63:
            price_3m = recent['Close'].iloc[-63]
            if hasattr(price_3m, 'iloc'):
                price_3m = float(price_3m.iloc[0])
            else:
                price_3m = float(price_3m)
            momentum = float((current / price_3m - 1) * 100)
            if momentum > 10:
                score += 15
            elif momentum > 0:
                score += 5
            elif momentum < -10:
                score -= 15

        # Volatilité
        returns = recent['Close'].pct_change().dropna()
        vol_value = returns.std() * np.sqrt(252) * 100
        if hasattr(vol_value, 'iloc'):
            vol_value = float(vol_value.iloc[0])
        else:
            vol_value = float(vol_value)
        if vol_value < 20:
            score += 10
        elif vol_value > 40:
            score -= 10

        return max(0, min(100, score))

    def _find_best_stock(
        self,
        date: datetime,
        data: Dict[str, pd.DataFrame],
        exclude: List[str]
    ) -> Tuple[Optional[str], float]:
        """Trouve la meilleure action à acheter."""
        best_ticker = None
        best_score = 0

        for ticker in self.ELIGIBLE_STOCKS:
            if ticker in exclude or ticker not in data:
                continue

            score = self._calculate_historical_score(ticker, date, data)
            if score > best_score:
                best_score = score
                best_ticker = ticker

        return best_ticker, best_score

    def _update_positions_prices(
        self,
        positions: Dict[str, Position],
        date: datetime,
        data: Dict[str, pd.DataFrame]
    ):
        """Met à jour les prix des positions."""
        for ticker, pos in positions.items():
            price = self._get_price_at_date(ticker, date, data)
            if price:
                pos.current_price = price

    def _collect_dividends(
        self,
        positions: Dict[str, Position],
        date: datetime,
        data: Dict[str, pd.DataFrame],
        reinvest: bool
    ) -> List[DividendPayment]:
        """Collecte les dividendes du mois."""
        dividends = []

        for ticker, pos in positions.items():
            # Estimation simplifiée: ~3% de rendement annuel, versé une fois par an
            # On simule un versement au mois de mai
            if date.month == 5:
                # Rendement estimé basé sur le secteur
                if 'BNP' in ticker or 'ACA' in ticker or 'GLE' in ticker:
                    yield_rate = 0.06  # 6% pour banques
                elif 'TTE' in ticker:
                    yield_rate = 0.05  # 5% énergie
                else:
                    yield_rate = 0.025  # 2.5% par défaut

                div_per_share = pos.current_price * yield_rate
                total = div_per_share * pos.shares

                if total > 0:
                    dividends.append(DividendPayment(
                        date=date,
                        ticker=ticker,
                        amount_per_share=div_per_share,
                        shares_held=pos.shares,
                        total=total,
                        reinvested=reinvest
                    ))

        return dividends

    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """Calcule le drawdown maximum."""
        if not values:
            return 0

        peak = values[0]
        max_dd = 0

        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_volatility(self, values: List[float]) -> float:
        """Calcule la volatilité annualisée."""
        if len(values) < 2:
            return 0

        returns = []
        for i in range(1, len(values)):
            if values[i-1] > 0:
                returns.append((values[i] / values[i-1]) - 1)

        if not returns:
            return 0

        return np.std(returns) * np.sqrt(12) * 100  # Annualisé

    def _calculate_sharpe(self, values: List[float], years: int) -> float:
        """Calcule le ratio de Sharpe."""
        if len(values) < 2 or years == 0:
            return 0

        total_return = (values[-1] / values[0]) - 1
        annual_return = (1 + total_return) ** (1 / years) - 1

        vol = self._calculate_volatility(values) / 100

        if vol == 0:
            return 0

        risk_free = 0.02  # ~2%
        return (annual_return - risk_free) / vol


def print_backtest_result(result: BacktestResult):
    """Affiche les résultats du backtest."""
    print(f"\n{'='*70}")
    print(f"RESULTAT BACKTEST: {result.strategy.value.upper()}")
    print(f"{'='*70}")

    print(f"\nPeriode: {result.start_date.strftime('%Y-%m')} -> {result.end_date.strftime('%Y-%m')} ({result.months} mois)")
    print(f"Investissement mensuel: {result.monthly_investment:.2f} EUR")
    print(f"Total investi: {result.total_invested:.2f} EUR")

    print(f"\n--- PERFORMANCE ---")
    print(f"Valeur finale:     {result.final_value:.2f} EUR")
    print(f"Gain total:        {result.total_gain:+.2f} EUR ({result.total_gain_pct:+.1f}%)")
    print(f"Rendement annuel:  {result.annualized_return:+.1f}%")

    if result.total_dividends > 0:
        print(f"\n--- DIVIDENDES ---")
        print(f"Total recu:        {result.total_dividends:.2f} EUR")
        if result.dividends_reinvested > 0:
            print(f"Reinvesti:         {result.dividends_reinvested:.2f} EUR")

    print(f"\n--- RISQUE ---")
    print(f"Max Drawdown:      {result.max_drawdown:.1f}%")
    print(f"Volatilite:        {result.volatility:.1f}%")
    print(f"Ratio Sharpe:      {result.sharpe_ratio:.2f}")

    if result.strategy != Strategy.BUY_AND_HOLD_ETF:
        print(f"\n--- VS BENCHMARK (ETF CAC40) ---")
        print(f"Benchmark final:   {result.benchmark_final:.2f} EUR ({result.benchmark_gain_pct:+.1f}%)")
        print(f"Surperformance:    {result.outperformance:+.1f}%")

    if result.final_positions:
        print(f"\n--- POSITIONS FINALES ---")
        for ticker, pos in sorted(result.final_positions.items(),
                                   key=lambda x: x[1].value, reverse=True)[:5]:
            print(f"  {ticker}: {pos.shares:.2f} actions @ {pos.current_price:.2f} EUR = {pos.value:.2f} EUR ({pos.gain_pct:+.1f}%)")


def run_full_comparison(monthly: float = 100):
    """Lance une comparaison complète sur plusieurs périodes."""

    simulator = BacktestSimulator(monthly_investment=monthly)

    periods = [1, 5, 10]  # 15 et 20 ans nécessitent plus de données

    all_results = {}

    for years in periods:
        print(f"\n{'#'*70}")
        print(f"# BACKTEST SUR {years} AN(S)")
        print(f"{'#'*70}")

        results = {}

        # Notre algorithme
        try:
            results['algo'] = simulator.run_backtest(years=years, strategy=Strategy.ALGO_SCORE)
            print_backtest_result(results['algo'])
        except Exception as e:
            print(f"Erreur algo: {e}")

        # ETF CAC40
        try:
            results['etf'] = simulator.run_backtest(years=years, strategy=Strategy.BUY_AND_HOLD_ETF)
            print_backtest_result(results['etf'])
        except Exception as e:
            print(f"Erreur ETF: {e}")

        # Livret A
        try:
            results['livret'] = simulator.run_backtest(years=years, strategy=Strategy.SAVINGS_ACCOUNT)
            print_backtest_result(results['livret'])
        except Exception as e:
            print(f"Erreur Livret: {e}")

        all_results[years] = results

        # Tableau comparatif
        print(f"\n{'='*70}")
        print(f"COMPARATIF {years} AN(S) - {monthly} EUR/mois")
        print(f"{'='*70}")
        print(f"{'Strategie':<20} {'Investi':>12} {'Final':>12} {'Gain':>12} {'%/an':>8}")
        print("-"*70)

        for name, res in results.items():
            print(f"{name:<20} {res.total_invested:>12.2f} {res.final_value:>12.2f} {res.total_gain:>+12.2f} {res.annualized_return:>+7.1f}%")

    return all_results


if __name__ == "__main__":
    run_full_comparison(100)
