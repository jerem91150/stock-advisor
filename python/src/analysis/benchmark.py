"""
Module de comparaison avec les benchmarks.
Compare la performance du portefeuille vs indices de référence.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# Benchmarks disponibles
BENCHMARKS = {
    'S&P 500': '^GSPC',
    'CAC 40': '^FCHI',
    'MSCI World': 'URTH',  # ETF iShares MSCI World
    'NASDAQ 100': '^NDX',
    'Euro Stoxx 50': '^STOXX50E',
    'DAX': '^GDAXI',
    'FTSE 100': '^FTSE',
    'Nikkei 225': '^N225',
}


@dataclass
class BenchmarkComparison:
    """Résultat de comparaison avec un benchmark."""
    benchmark_name: str
    benchmark_ticker: str
    period: str
    portfolio_return: float
    benchmark_return: float
    alpha: float  # Surperformance vs benchmark
    beta: float   # Volatilité relative
    sharpe_ratio: float
    tracking_error: float
    information_ratio: float
    max_drawdown_portfolio: float
    max_drawdown_benchmark: float
    correlation: float
    win_rate: float  # % de jours où portfolio > benchmark


class BenchmarkAnalyzer:
    """Analyseur de performance vs benchmarks."""

    def __init__(self, risk_free_rate: float = 0.03):
        """
        Initialise l'analyseur.

        Args:
            risk_free_rate: Taux sans risque annuel (default 3%)
        """
        self.risk_free_rate = risk_free_rate
        self._cache = {}

    def get_benchmark_data(self, ticker: str, period: str = '1y') -> pd.DataFrame:
        """Récupère les données d'un benchmark."""
        cache_key = f"{ticker}_{period}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            data = yf.download(ticker, period=period, progress=False)
            if not data.empty:
                self._cache[cache_key] = data
            return data
        except Exception as e:
            print(f"Erreur récupération {ticker}: {e}")
            return pd.DataFrame()

    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calcule les rendements journaliers."""
        return prices.pct_change().dropna()

    def calculate_cumulative_returns(self, returns: pd.Series) -> pd.Series:
        """Calcule les rendements cumulés."""
        return (1 + returns).cumprod() - 1

    def calculate_max_drawdown(self, prices: pd.Series) -> float:
        """Calcule le drawdown maximum."""
        peak = prices.expanding(min_periods=1).max()
        drawdown = (prices - peak) / peak
        return drawdown.min()

    def calculate_sharpe_ratio(self, returns: pd.Series, periods_per_year: int = 252) -> float:
        """Calcule le ratio de Sharpe."""
        if returns.std() == 0:
            return 0
        excess_returns = returns.mean() - self.risk_free_rate / periods_per_year
        return (excess_returns / returns.std()) * np.sqrt(periods_per_year)

    def calculate_beta(self, portfolio_returns: pd.Series,
                       benchmark_returns: pd.Series) -> float:
        """Calcule le beta du portefeuille vs benchmark."""
        # Aligner les séries
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 1.0

        portfolio_aligned = aligned.iloc[:, 0]
        benchmark_aligned = aligned.iloc[:, 1]

        covariance = np.cov(portfolio_aligned, benchmark_aligned)[0][1]
        variance = np.var(benchmark_aligned)

        return covariance / variance if variance != 0 else 1.0

    def calculate_alpha(self, portfolio_return: float, benchmark_return: float,
                        beta: float) -> float:
        """Calcule l'alpha (surperformance ajustée au risque)."""
        # Alpha de Jensen: Rp - [Rf + β(Rm - Rf)]
        expected_return = self.risk_free_rate + beta * (benchmark_return - self.risk_free_rate)
        return portfolio_return - expected_return

    def calculate_tracking_error(self, portfolio_returns: pd.Series,
                                  benchmark_returns: pd.Series) -> float:
        """Calcule l'erreur de suivi (tracking error)."""
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0

        diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        return diff.std() * np.sqrt(252)

    def calculate_information_ratio(self, portfolio_returns: pd.Series,
                                     benchmark_returns: pd.Series) -> float:
        """Calcule le ratio d'information."""
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < 2:
            return 0

        excess_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        tracking_error = excess_returns.std()

        if tracking_error == 0:
            return 0

        return (excess_returns.mean() * 252) / (tracking_error * np.sqrt(252))

    def compare_portfolio(self, portfolio_values: pd.Series,
                          benchmark_name: str = 'S&P 500',
                          period: str = '1y') -> Optional[BenchmarkComparison]:
        """
        Compare la performance du portefeuille avec un benchmark.

        Args:
            portfolio_values: Série des valeurs du portefeuille (indexée par date)
            benchmark_name: Nom du benchmark (ex: 'S&P 500', 'CAC 40')
            period: Période de comparaison

        Returns:
            BenchmarkComparison avec toutes les métriques
        """
        if benchmark_name not in BENCHMARKS:
            print(f"Benchmark inconnu: {benchmark_name}")
            return None

        benchmark_ticker = BENCHMARKS[benchmark_name]

        # Récupérer les données du benchmark
        benchmark_data = self.get_benchmark_data(benchmark_ticker, period)
        if benchmark_data.empty:
            return None

        # S'assurer que les index sont en datetime naïf
        if hasattr(portfolio_values.index, 'tz') and portfolio_values.index.tz is not None:
            portfolio_values = portfolio_values.copy()
            portfolio_values.index = portfolio_values.index.tz_localize(None)

        benchmark_prices = benchmark_data['Close']
        if hasattr(benchmark_prices.index, 'tz') and benchmark_prices.index.tz is not None:
            benchmark_prices = benchmark_prices.copy()
            benchmark_prices.index = benchmark_prices.index.tz_localize(None)

        # Aligner les dates
        common_dates = portfolio_values.index.intersection(benchmark_prices.index)
        if len(common_dates) < 10:
            # Essayer un resampling
            portfolio_values = portfolio_values.resample('D').last().ffill()
            benchmark_prices = benchmark_prices.resample('D').last().ffill()
            common_dates = portfolio_values.index.intersection(benchmark_prices.index)

        if len(common_dates) < 10:
            print("Pas assez de données communes")
            return None

        portfolio_aligned = portfolio_values.loc[common_dates]
        benchmark_aligned = benchmark_prices.loc[common_dates]

        # Calculer les rendements
        portfolio_returns = self.calculate_returns(portfolio_aligned)
        benchmark_returns = self.calculate_returns(benchmark_aligned)

        # Rendements totaux
        portfolio_total_return = (portfolio_aligned.iloc[-1] / portfolio_aligned.iloc[0] - 1) * 100
        benchmark_total_return = (benchmark_aligned.iloc[-1] / benchmark_aligned.iloc[0] - 1) * 100

        # Métriques
        beta = self.calculate_beta(portfolio_returns, benchmark_returns)
        alpha = self.calculate_alpha(portfolio_total_return / 100,
                                      benchmark_total_return / 100, beta)

        # Corrélation
        correlation = portfolio_returns.corr(benchmark_returns)

        # Win rate
        daily_comparison = portfolio_returns > benchmark_returns
        win_rate = daily_comparison.sum() / len(daily_comparison) * 100

        return BenchmarkComparison(
            benchmark_name=benchmark_name,
            benchmark_ticker=benchmark_ticker,
            period=period,
            portfolio_return=portfolio_total_return,
            benchmark_return=benchmark_total_return,
            alpha=alpha * 100,  # En pourcentage
            beta=beta,
            sharpe_ratio=self.calculate_sharpe_ratio(portfolio_returns),
            tracking_error=self.calculate_tracking_error(portfolio_returns, benchmark_returns),
            information_ratio=self.calculate_information_ratio(portfolio_returns, benchmark_returns),
            max_drawdown_portfolio=self.calculate_max_drawdown(portfolio_aligned) * 100,
            max_drawdown_benchmark=self.calculate_max_drawdown(benchmark_aligned) * 100,
            correlation=correlation,
            win_rate=win_rate
        )

    def compare_all_benchmarks(self, portfolio_values: pd.Series,
                                period: str = '1y') -> Dict[str, BenchmarkComparison]:
        """Compare le portefeuille avec tous les benchmarks."""
        results = {}

        for name in BENCHMARKS:
            comparison = self.compare_portfolio(portfolio_values, name, period)
            if comparison:
                results[name] = comparison

        return results

    def get_comparison_chart_data(self, portfolio_values: pd.Series,
                                   benchmark_name: str = 'S&P 500',
                                   period: str = '1y') -> Optional[pd.DataFrame]:
        """
        Prépare les données pour un graphique de comparaison.

        Returns:
            DataFrame avec colonnes: date, portfolio_cumret, benchmark_cumret
        """
        if benchmark_name not in BENCHMARKS:
            return None

        benchmark_ticker = BENCHMARKS[benchmark_name]
        benchmark_data = self.get_benchmark_data(benchmark_ticker, period)

        if benchmark_data.empty:
            return None

        # Aligner et normaliser à 100
        benchmark_prices = benchmark_data['Close']

        # Gérer les timezones
        if hasattr(portfolio_values.index, 'tz') and portfolio_values.index.tz is not None:
            portfolio_values = portfolio_values.copy()
            portfolio_values.index = portfolio_values.index.tz_localize(None)

        if hasattr(benchmark_prices.index, 'tz') and benchmark_prices.index.tz is not None:
            benchmark_prices = benchmark_prices.copy()
            benchmark_prices.index = benchmark_prices.index.tz_localize(None)

        # Resampling daily
        portfolio_daily = portfolio_values.resample('D').last().ffill()
        benchmark_daily = benchmark_prices.resample('D').last().ffill()

        common_dates = portfolio_daily.index.intersection(benchmark_daily.index)
        if len(common_dates) < 2:
            return None

        portfolio_aligned = portfolio_daily.loc[common_dates]
        benchmark_aligned = benchmark_daily.loc[common_dates]

        # Normaliser à 100
        portfolio_normalized = (portfolio_aligned / portfolio_aligned.iloc[0]) * 100
        benchmark_normalized = (benchmark_aligned / benchmark_aligned.iloc[0]) * 100

        return pd.DataFrame({
            'date': common_dates,
            'Portfolio': portfolio_normalized.values,
            benchmark_name: benchmark_normalized.values
        })

    def get_monthly_comparison(self, portfolio_values: pd.Series,
                                benchmark_name: str = 'S&P 500') -> Optional[pd.DataFrame]:
        """
        Compare les performances mensuelles.

        Returns:
            DataFrame avec les rendements mensuels du portfolio et du benchmark
        """
        if benchmark_name not in BENCHMARKS:
            return None

        benchmark_ticker = BENCHMARKS[benchmark_name]
        benchmark_data = self.get_benchmark_data(benchmark_ticker, '2y')

        if benchmark_data.empty:
            return None

        benchmark_prices = benchmark_data['Close']

        # Gérer les timezones
        if hasattr(portfolio_values.index, 'tz') and portfolio_values.index.tz is not None:
            portfolio_values = portfolio_values.copy()
            portfolio_values.index = portfolio_values.index.tz_localize(None)

        if hasattr(benchmark_prices.index, 'tz') and benchmark_prices.index.tz is not None:
            benchmark_prices = benchmark_prices.copy()
            benchmark_prices.index = benchmark_prices.index.tz_localize(None)

        # Rendements mensuels
        portfolio_monthly = portfolio_values.resample('M').last().pct_change().dropna() * 100
        benchmark_monthly = benchmark_prices.resample('M').last().pct_change().dropna() * 100

        # Aligner
        common_months = portfolio_monthly.index.intersection(benchmark_monthly.index)
        if len(common_months) < 2:
            return None

        return pd.DataFrame({
            'Mois': [d.strftime('%Y-%m') for d in common_months],
            'Portfolio (%)': portfolio_monthly.loc[common_months].values,
            f'{benchmark_name} (%)': benchmark_monthly.loc[common_months].values
        })


def get_benchmark_names() -> List[str]:
    """Retourne la liste des benchmarks disponibles."""
    return list(BENCHMARKS.keys())


def quick_compare(portfolio_values: pd.Series,
                  benchmark: str = 'S&P 500') -> Dict:
    """
    Comparaison rapide avec un benchmark.

    Returns:
        Dict avec les métriques clés
    """
    analyzer = BenchmarkAnalyzer()
    result = analyzer.compare_portfolio(portfolio_values, benchmark)

    if result is None:
        return {}

    return {
        'benchmark': result.benchmark_name,
        'portfolio_return': f"{result.portfolio_return:.1f}%",
        'benchmark_return': f"{result.benchmark_return:.1f}%",
        'alpha': f"{result.alpha:.1f}%",
        'beta': f"{result.beta:.2f}",
        'sharpe': f"{result.sharpe_ratio:.2f}",
        'correlation': f"{result.correlation:.2f}",
        'outperformance': result.portfolio_return > result.benchmark_return
    }


# Test
if __name__ == "__main__":
    print("=== Test Benchmark Analyzer ===\n")

    # Simuler un portefeuille
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.01, len(dates))
    values = 10000 * (1 + pd.Series(returns)).cumprod()
    portfolio = pd.Series(values.values, index=dates)

    analyzer = BenchmarkAnalyzer()

    # Comparer avec S&P 500
    print("Comparaison avec S&P 500:")
    result = analyzer.compare_portfolio(portfolio, 'S&P 500', '1y')

    if result:
        print(f"  Portfolio: {result.portfolio_return:.1f}%")
        print(f"  S&P 500: {result.benchmark_return:.1f}%")
        print(f"  Alpha: {result.alpha:.1f}%")
        print(f"  Beta: {result.beta:.2f}")
        print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"  Corrélation: {result.correlation:.2f}")
        print(f"  Win Rate: {result.win_rate:.1f}%")

    print("\n✅ Test terminé")
