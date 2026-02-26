"""
Dividend Tracker - Suivi des dividendes à venir
Récupère les dates ex-dividende, montants et calendrier
"""

import os
import sys
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

import yfinance as yf
import pandas as pd


def to_naive_datetime(dt) -> Optional[datetime]:
    """Convertit un datetime timezone-aware en naive datetime."""
    if dt is None:
        return None
    if isinstance(dt, pd.Timestamp):
        dt = dt.to_pydatetime()
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


@dataclass
class DividendInfo:
    """Information sur un dividende."""
    ticker: str
    name: str
    ex_date: Optional[datetime]  # Date ex-dividende
    payment_date: Optional[datetime]  # Date de paiement
    amount: float  # Montant par action
    currency: str
    frequency: str  # annual, semi-annual, quarterly, monthly
    dividend_yield: float  # Rendement en %
    payout_ratio: Optional[float]  # Ratio de distribution


@dataclass
class UpcomingDividend:
    """Dividende à venir pour une position."""
    ticker: str
    name: str
    ex_date: datetime
    payment_date: Optional[datetime]
    amount_per_share: float
    shares_held: float
    expected_amount: float  # Montant attendu
    currency: str
    days_until_ex: int


@dataclass
class DividendHistory:
    """Historique d'un dividende."""
    date: datetime
    amount: float
    currency: str


class DividendTracker:
    """Tracker des dividendes pour les positions."""

    def __init__(self):
        self._cache: Dict[str, Tuple[DividendInfo, datetime]] = {}
        self._cache_duration = timedelta(hours=6)

    def get_dividend_info(self, ticker: str) -> Optional[DividendInfo]:
        """Récupère les informations de dividende pour une action."""
        # Vérifier le cache
        now = datetime.now()
        if ticker in self._cache:
            info, timestamp = self._cache[ticker]
            if now - timestamp < self._cache_duration:
                return info

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Récupérer le calendrier
            try:
                calendar = stock.calendar
            except:
                calendar = {}

            # Date ex-dividende
            ex_date = None
            if isinstance(calendar, dict) and 'Ex-Dividend Date' in calendar:
                ex_date = calendar['Ex-Dividend Date']
                if isinstance(ex_date, pd.Timestamp):
                    ex_date = ex_date.to_pydatetime()
            elif hasattr(calendar, 'get'):
                ex_date = calendar.get('Ex-Dividend Date')

            # Chercher dans info aussi
            if not ex_date and 'exDividendDate' in info:
                ex_ts = info.get('exDividendDate')
                if ex_ts:
                    ex_date = datetime.fromtimestamp(ex_ts)

            # Montant du dividende
            dividend_rate = info.get('dividendRate', 0) or 0
            trailing_dividend = info.get('trailingAnnualDividendRate', 0) or 0
            amount = dividend_rate if dividend_rate > 0 else trailing_dividend

            # Rendement
            dividend_yield = (info.get('dividendYield', 0) or 0) * 100
            if dividend_yield == 0 and info.get('trailingAnnualDividendYield'):
                dividend_yield = (info.get('trailingAnnualDividendYield') or 0) * 100

            # Fréquence (estimation basée sur le nombre de dividendes par an)
            frequency = "quarterly"  # Par défaut
            if trailing_dividend > 0 and amount > 0:
                payments_per_year = trailing_dividend / amount
                if payments_per_year >= 11:
                    frequency = "monthly"
                elif payments_per_year >= 3:
                    frequency = "quarterly"
                elif payments_per_year >= 1.5:
                    frequency = "semi-annual"
                else:
                    frequency = "annual"

            # Payout ratio
            payout_ratio = info.get('payoutRatio')
            if payout_ratio:
                payout_ratio = payout_ratio * 100

            dividend_info = DividendInfo(
                ticker=ticker,
                name=info.get('shortName', ticker),
                ex_date=ex_date,
                payment_date=None,  # Pas toujours disponible
                amount=amount,
                currency=info.get('currency', 'USD'),
                frequency=frequency,
                dividend_yield=dividend_yield,
                payout_ratio=payout_ratio
            )

            # Mettre en cache
            self._cache[ticker] = (dividend_info, now)
            return dividend_info

        except Exception as e:
            print(f"Erreur récupération dividende {ticker}: {e}")
            return None

    def get_dividend_history(self, ticker: str, years: int = 5) -> List[DividendHistory]:
        """Récupère l'historique des dividendes."""
        try:
            stock = yf.Ticker(ticker)
            dividends = stock.dividends

            if dividends.empty:
                return []

            # Filtrer par période - convertir l'index en naive datetime pour la comparaison
            start_date = datetime.now() - timedelta(days=years * 365)

            history = []
            for dt, amount in dividends.items():
                div_date = to_naive_datetime(dt)
                if div_date and div_date >= start_date:
                    history.append(DividendHistory(
                        date=div_date,
                        amount=float(amount),
                        currency=stock.info.get('currency', 'USD')
                    ))

            return sorted(history, key=lambda x: x.date, reverse=True)

        except Exception as e:
            print(f"Erreur historique dividendes {ticker}: {e}")
            return []

    def get_upcoming_dividends(
        self,
        positions: List[Dict],  # [{'ticker': str, 'quantity': float, 'name': str}]
        days_ahead: int = 90
    ) -> List[UpcomingDividend]:
        """Récupère les dividendes à venir pour une liste de positions."""
        upcoming = []
        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)

        for pos in positions:
            ticker = pos['ticker']
            quantity = pos.get('quantity', 0)

            if quantity <= 0:
                continue

            info = self.get_dividend_info(ticker)
            if not info or not info.ex_date:
                continue

            # Convertir en naive datetime pour la comparaison
            ex_date_naive = to_naive_datetime(info.ex_date)
            if not ex_date_naive:
                continue

            # Vérifier si la date ex-dividende est dans la période
            if ex_date_naive < now:
                # Estimer la prochaine date basée sur la fréquence
                next_ex_date = self._estimate_next_ex_date(info)
                if not next_ex_date or next_ex_date > cutoff:
                    continue
                ex_date = next_ex_date
            elif ex_date_naive > cutoff:
                continue
            else:
                ex_date = ex_date_naive

            # Calculer le montant attendu
            # Pour les dividendes trimestriels, diviser le montant annuel par 4
            amount_per_payment = info.amount
            if info.frequency == "quarterly":
                amount_per_payment = info.amount / 4
            elif info.frequency == "semi-annual":
                amount_per_payment = info.amount / 2
            elif info.frequency == "monthly":
                amount_per_payment = info.amount / 12

            expected_amount = amount_per_payment * quantity
            days_until = (ex_date - now).days

            upcoming.append(UpcomingDividend(
                ticker=ticker,
                name=pos.get('name', info.name),
                ex_date=ex_date,
                payment_date=info.payment_date,
                amount_per_share=amount_per_payment,
                shares_held=quantity,
                expected_amount=expected_amount,
                currency=info.currency,
                days_until_ex=days_until
            ))

        # Trier par date
        return sorted(upcoming, key=lambda x: x.ex_date)

    def _estimate_next_ex_date(self, info: DividendInfo) -> Optional[datetime]:
        """Estime la prochaine date ex-dividende basée sur la fréquence."""
        if not info.ex_date:
            return None

        now = datetime.now()
        last_ex = info.ex_date

        # Calculer l'intervalle
        if info.frequency == "monthly":
            interval = timedelta(days=30)
        elif info.frequency == "quarterly":
            interval = timedelta(days=91)
        elif info.frequency == "semi-annual":
            interval = timedelta(days=182)
        else:  # annual
            interval = timedelta(days=365)

        # Trouver la prochaine date
        next_date = last_ex
        while next_date < now:
            next_date += interval

        return next_date

    def get_annual_dividend_estimate(
        self,
        positions: List[Dict]
    ) -> Dict:
        """Estime les dividendes annuels pour un portefeuille."""
        total_annual = 0
        by_ticker = {}
        by_month = {i: 0 for i in range(1, 13)}

        for pos in positions:
            ticker = pos['ticker']
            quantity = pos.get('quantity', 0)

            if quantity <= 0:
                continue

            info = self.get_dividend_info(ticker)
            if not info or info.amount <= 0:
                continue

            annual_amount = info.amount * quantity
            total_annual += annual_amount

            by_ticker[ticker] = {
                'name': info.name,
                'quantity': quantity,
                'dividend_per_share': info.amount,
                'annual_amount': annual_amount,
                'yield': info.dividend_yield,
                'frequency': info.frequency,
                'currency': info.currency
            }

            # Répartir par mois selon la fréquence
            monthly_amount = annual_amount / 12
            if info.frequency == "quarterly":
                # Paiements typiques: Mars, Juin, Sept, Dec
                for month in [3, 6, 9, 12]:
                    by_month[month] += annual_amount / 4
            elif info.frequency == "semi-annual":
                for month in [6, 12]:
                    by_month[month] += annual_amount / 2
            elif info.frequency == "monthly":
                for month in range(1, 13):
                    by_month[month] += monthly_amount
            else:  # annual
                by_month[6] += annual_amount  # Estimation mi-année

        return {
            'total_annual': total_annual,
            'monthly_average': total_annual / 12,
            'by_ticker': by_ticker,
            'by_month': by_month
        }

    def get_dividend_calendar(
        self,
        positions: List[Dict],
        year: int = None
    ) -> Dict[str, List[Dict]]:
        """Crée un calendrier des dividendes attendus."""
        if year is None:
            year = datetime.now().year

        calendar = {str(i).zfill(2): [] for i in range(1, 13)}

        # Récupérer l'historique pour estimer les dates
        for pos in positions:
            ticker = pos['ticker']
            quantity = pos.get('quantity', 0)

            if quantity <= 0:
                continue

            info = self.get_dividend_info(ticker)
            if not info or info.amount <= 0:
                continue

            history = self.get_dividend_history(ticker, years=2)

            if history:
                # Utiliser l'historique pour prédire les mois de paiement
                payment_months = set()
                for h in history:
                    payment_months.add(h.date.month)

                for month in payment_months:
                    monthly_div = info.amount / len(payment_months)
                    calendar[str(month).zfill(2)].append({
                        'ticker': ticker,
                        'name': info.name,
                        'amount_per_share': monthly_div,
                        'quantity': quantity,
                        'expected_amount': monthly_div * quantity,
                        'currency': info.currency,
                        'yield': info.dividend_yield
                    })
            else:
                # Estimation basée sur la fréquence
                if info.frequency == "quarterly":
                    months = [3, 6, 9, 12]
                elif info.frequency == "semi-annual":
                    months = [6, 12]
                elif info.frequency == "monthly":
                    months = list(range(1, 13))
                else:
                    months = [6]

                payment_per_period = info.amount / len(months)
                for month in months:
                    calendar[str(month).zfill(2)].append({
                        'ticker': ticker,
                        'name': info.name,
                        'amount_per_share': payment_per_period,
                        'quantity': quantity,
                        'expected_amount': payment_per_period * quantity,
                        'currency': info.currency,
                        'yield': info.dividend_yield
                    })

        return calendar


def get_dividend_tracker() -> DividendTracker:
    """Factory function."""
    return DividendTracker()


if __name__ == "__main__":
    # Test
    tracker = DividendTracker()

    print("=== Test Dividend Tracker ===\n")

    # Test sur quelques actions connues pour leurs dividendes
    test_tickers = ["AAPL", "KO", "JNJ", "MC.PA", "TTE.PA"]

    for ticker in test_tickers:
        info = tracker.get_dividend_info(ticker)
        if info:
            print(f"{ticker} ({info.name}):")
            print(f"  Rendement: {info.dividend_yield:.2f}%")
            print(f"  Montant annuel: {info.amount:.2f} {info.currency}")
            print(f"  Fréquence: {info.frequency}")
            print(f"  Prochaine ex-date: {info.ex_date}")
            print()

    # Test calendrier
    positions = [
        {'ticker': 'AAPL', 'quantity': 10, 'name': 'Apple'},
        {'ticker': 'KO', 'quantity': 20, 'name': 'Coca-Cola'},
        {'ticker': 'TTE.PA', 'quantity': 15, 'name': 'TotalEnergies'}
    ]

    print("\n=== Dividendes à venir (90 jours) ===")
    upcoming = tracker.get_upcoming_dividends(positions, days_ahead=90)
    for div in upcoming:
        print(f"  {div.ticker}: {div.ex_date.strftime('%Y-%m-%d')} - {div.expected_amount:.2f} {div.currency} ({div.days_until_ex}j)")

    print("\n=== Estimation annuelle ===")
    estimate = tracker.get_annual_dividend_estimate(positions)
    print(f"  Total annuel: {estimate['total_annual']:.2f}")
    print(f"  Moyenne mensuelle: {estimate['monthly_average']:.2f}")
