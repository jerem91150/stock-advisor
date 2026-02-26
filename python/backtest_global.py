"""
BACKTEST GLOBAL COMPLET
=======================
- Actions mondiales (US, EU, Japon, etc.)
- 4 composantes: Technique + Fondamental + Sentiment + Smart Money
- Mode PEA (EU uniquement) ou CTO (monde entier)
- Investissement DCA mensuel realiste
"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from src.scrapers.yahoo_finance import YahooFinanceScraper
from src.analysis.technical import TechnicalAnalyzer
from src.analysis.fundamental import FundamentalAnalyzer

# Configuration
MONTHLY_INVESTMENT = 100.0
MIN_SCORE = 55  # Score minimum pour acheter
MAX_POSITION_PCT = 0.30  # Max 30% par position
SELL_THRESHOLD = 40  # Vendre si score < 40

# Actions par marche
STOCKS_US = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
    'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS', 'NFLX', 'ADBE',
    'CRM', 'INTC', 'AMD', 'PYPL', 'NKE', 'KO', 'PEP', 'MRK', 'PFE'
]

STOCKS_EU = [
    # France (PEA eligible)
    'MC.PA', 'OR.PA', 'SAN.PA', 'AI.PA', 'SU.PA', 'BNP.PA', 'GLE.PA',
    'CAP.PA', 'ACA.PA', 'VIV.PA', 'KER.PA', 'RMS.PA', 'TTE.PA',
    # Allemagne (PEA eligible)
    'SAP.DE', 'SIE.DE', 'ALV.DE', 'DTE.DE', 'BAS.DE', 'BMW.DE',
    # Pays-Bas (PEA eligible)
    'ASML.AS', 'PHIA.AS', 'UNA.AS',
    # Italie (PEA eligible)
    'ENEL.MI', 'ENI.MI', 'ISP.MI'
]

STOCKS_ASIA = [
    # Japon
    '7203.T', '6758.T', '9984.T', '6861.T', '8306.T',
    # Chine/HK
    'BABA', 'JD', 'PDD', 'BIDU', 'NIO'
]

# Initialisation des analyseurs
scraper = YahooFinanceScraper()
technical_analyzer = TechnicalAnalyzer()
fundamental_analyzer = FundamentalAnalyzer()


def get_stock_universe(mode: str) -> List[str]:
    """Retourne la liste des actions selon le mode."""
    if mode == 'PEA':
        return STOCKS_EU  # Uniquement actions EU
    else:  # CTO
        return STOCKS_US + STOCKS_EU + STOCKS_ASIA


def load_stock_data(ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
    """Charge les donnees historiques d'une action."""
    try:
        df = yf.download(
            ticker,
            start=start_date - timedelta(days=400),
            end=end_date + timedelta(days=5),
            progress=False
        )
        if not df.empty and len(df) > 100:
            return df
    except:
        pass
    return None


def calculate_full_score(ticker: str, date: datetime, hist_data: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Calcule le score complet (4 composantes).
    Pour le backtest, on simplifie sentiment et smart_money.
    """
    details = {
        'technical': 50,
        'fundamental': 50,
        'sentiment': 50,  # Neutre par defaut
        'smart_money': 50,  # Neutre par defaut
        'price': 0,
        'currency': 'USD'
    }

    # Filtrer les donnees jusqu'a la date
    mask = hist_data.index <= pd.Timestamp(date)
    if not mask.any():
        return 50, details

    recent = hist_data.loc[mask].tail(250)
    if len(recent) < 50:
        return 50, details

    # Prix actuel
    current_price = recent['Close'].iloc[-1]
    if hasattr(current_price, 'iloc'):
        current_price = float(current_price.iloc[0])
    else:
        current_price = float(current_price)
    details['price'] = current_price

    # 1. SCORE TECHNIQUE
    tech_score = 50

    # MA50 et MA200
    ma50 = float(recent['Close'].tail(50).mean())
    ma200 = float(recent['Close'].tail(200).mean()) if len(recent) >= 200 else ma50

    # Prix vs MA50 (court terme)
    if current_price > ma50 * 1.02:
        tech_score += 10
    elif current_price > ma50:
        tech_score += 5
    elif current_price < ma50 * 0.98:
        tech_score -= 10

    # MA50 vs MA200 (moyen terme)
    if ma50 > ma200 * 1.03:
        tech_score += 15
    elif ma50 > ma200:
        tech_score += 5
    elif ma50 < ma200 * 0.97:
        tech_score -= 15
    else:
        tech_score -= 5

    # Momentum 1 mois
    if len(recent) >= 21:
        price_1m = float(recent['Close'].iloc[-21])
        if hasattr(price_1m, 'Series'):
            price_1m = float(price_1m.iloc[0])
        mom_1m = (current_price / price_1m - 1) * 100
        if mom_1m > 5:
            tech_score += 10
        elif mom_1m > 0:
            tech_score += 3
        elif mom_1m < -5:
            tech_score -= 10

    # Momentum 3 mois
    if len(recent) >= 63:
        price_3m = float(recent['Close'].iloc[-63])
        if hasattr(price_3m, 'Series'):
            price_3m = float(price_3m.iloc[0])
        mom_3m = (current_price / price_3m - 1) * 100
        if mom_3m > 10:
            tech_score += 10
        elif mom_3m > 0:
            tech_score += 3
        elif mom_3m < -10:
            tech_score -= 10

    # RSI simplifie
    delta = recent['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if len(rsi.dropna()) > 0:
        current_rsi = float(rsi.iloc[-1])
        if hasattr(current_rsi, 'iloc'):
            current_rsi = float(current_rsi.iloc[0])
        if 30 < current_rsi < 70:
            tech_score += 5  # Zone neutre = bon
        elif current_rsi <= 30:
            tech_score += 10  # Survendu = opportunite
        elif current_rsi >= 70:
            tech_score -= 5  # Surachete = attention

    details['technical'] = max(0, min(100, tech_score))

    # 2. SCORE FONDAMENTAL (simplifie pour backtest)
    # On utilise des donnees actuelles comme proxy
    fund_score = 50

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # P/E
        pe = info.get('trailingPE') or info.get('forwardPE')
        if pe:
            if pe < 15:
                fund_score += 15
            elif pe < 25:
                fund_score += 5
            elif pe > 40:
                fund_score -= 10

        # ROE
        roe = info.get('returnOnEquity')
        if roe:
            if roe > 0.20:
                fund_score += 10
            elif roe > 0.10:
                fund_score += 5
            elif roe < 0:
                fund_score -= 10

        # Croissance revenus
        rev_growth = info.get('revenueGrowth')
        if rev_growth:
            if rev_growth > 0.15:
                fund_score += 10
            elif rev_growth > 0.05:
                fund_score += 5
            elif rev_growth < 0:
                fund_score -= 5

        # Dette
        debt_equity = info.get('debtToEquity')
        if debt_equity:
            if debt_equity < 50:
                fund_score += 5
            elif debt_equity > 150:
                fund_score -= 10

    except:
        pass

    details['fundamental'] = max(0, min(100, fund_score))

    # 3. SCORE SENTIMENT (simplifie - base sur momentum recent)
    # Plus le momentum court terme est fort, meilleur est le sentiment
    sent_score = 50
    if len(recent) >= 5:
        price_5d = float(recent['Close'].iloc[-5])
        if hasattr(price_5d, 'iloc'):
            price_5d = float(price_5d.iloc[0])
        mom_5d = (current_price / price_5d - 1) * 100
        if mom_5d > 3:
            sent_score = 70
        elif mom_5d > 0:
            sent_score = 60
        elif mom_5d < -3:
            sent_score = 30
        else:
            sent_score = 45
    details['sentiment'] = sent_score

    # 4. SCORE SMART MONEY (simplifie - base sur volume)
    # Volume eleve + hausse = smart money achete
    sm_score = 50
    if len(recent) >= 20:
        avg_vol = float(recent['Volume'].tail(20).mean())
        recent_vol = float(recent['Volume'].iloc[-1])
        if hasattr(recent_vol, 'iloc'):
            recent_vol = float(recent_vol.iloc[0])

        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1

        if len(recent) >= 5:
            price_change = (current_price / price_5d - 1) * 100
            if vol_ratio > 1.5 and price_change > 0:
                sm_score = 75  # Volume eleve + hausse
            elif vol_ratio > 1.5 and price_change < 0:
                sm_score = 35  # Volume eleve + baisse (distribution)
            elif vol_ratio < 0.7:
                sm_score = 45  # Volume faible
    details['smart_money'] = sm_score

    # SCORE GLOBAL (moyenne ponderee)
    global_score = (
        details['technical'] * 0.30 +      # 30% technique
        details['fundamental'] * 0.30 +    # 30% fondamental
        details['sentiment'] * 0.20 +      # 20% sentiment
        details['smart_money'] * 0.20      # 20% smart money
    )

    return global_score, details


def run_global_backtest(
    mode: str = 'CTO',
    years: int = 3,
    monthly_investment: float = 100.0
):
    """
    Execute le backtest global.

    Args:
        mode: 'PEA' (EU uniquement) ou 'CTO' (monde entier)
        years: Nombre d'annees de backtest
        monthly_investment: Investissement mensuel en EUR
    """
    end_date = datetime.now()
    start_date = end_date - relativedelta(years=years)

    print('='*100)
    print('BACKTEST GLOBAL COMPLET')
    print('='*100)
    print('Mode: {} ({})'.format(mode, 'Actions EU uniquement' if mode == 'PEA' else 'Actions mondiales'))
    print('Periode: {} -> {} ({} ans)'.format(
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d'),
        years
    ))
    print('Investissement: {} EUR/mois'.format(monthly_investment))
    print('Score minimum: {}/100'.format(MIN_SCORE))
    print('Seuil de vente: {}/100'.format(SELL_THRESHOLD))
    print('='*100)

    # Charger l'univers d'actions
    universe = get_stock_universe(mode)
    print('\nChargement des donnees pour {} actions...'.format(len(universe)))

    stock_data = {}
    for i, ticker in enumerate(universe):
        df = load_stock_data(ticker, start_date, end_date)
        if df is not None:
            stock_data[ticker] = df
            print('  [{}/{}] {} OK ({} jours)'.format(i+1, len(universe), ticker, len(df)))
        else:
            print('  [{}/{}] {} SKIP (pas de donnees)'.format(i+1, len(universe), ticker))

    print('\n{} actions chargees avec succes'.format(len(stock_data)))

    if len(stock_data) < 5:
        print('ERREUR: Pas assez de donnees pour le backtest')
        return

    # Simulation
    cash = 0.0
    positions = {}  # {ticker: {'shares': x, 'avg_cost': y, 'currency': z}}
    total_invested = 0.0
    transactions = []
    monthly_values = []

    current_date = start_date.replace(day=1)
    month_num = 0

    print('\n' + '='*100)
    print('SIMULATION')
    print('='*100)

    while current_date <= end_date:
        month_num += 1

        # Ajouter investissement mensuel
        cash += monthly_investment
        total_invested += monthly_investment

        # Calculer les scores de toutes les actions
        scores = []
        for ticker, df in stock_data.items():
            score, details = calculate_full_score(ticker, current_date, df)
            if details['price'] > 0:
                scores.append({
                    'ticker': ticker,
                    'score': score,
                    'price': details['price'],
                    'technical': details['technical'],
                    'fundamental': details['fundamental'],
                    'sentiment': details['sentiment'],
                    'smart_money': details['smart_money']
                })

        # Trier par score
        scores.sort(key=lambda x: x['score'], reverse=True)

        # Calculer valeur portefeuille
        portfolio_value = cash
        for ticker, pos in positions.items():
            if ticker in stock_data:
                _, details = calculate_full_score(ticker, current_date, stock_data[ticker])
                if details['price'] > 0:
                    portfolio_value += pos['shares'] * details['price']

        # VENDRE les positions sous le seuil
        for ticker in list(positions.keys()):
            ticker_score = next((s['score'] for s in scores if s['ticker'] == ticker), 0)
            if ticker_score < SELL_THRESHOLD:
                pos = positions[ticker]
                _, details = calculate_full_score(ticker, current_date, stock_data[ticker])
                if details['price'] > 0:
                    sell_value = pos['shares'] * details['price']
                    cash += sell_value
                    transactions.append({
                        'date': current_date,
                        'action': 'SELL',
                        'ticker': ticker,
                        'shares': pos['shares'],
                        'price': details['price'],
                        'reason': 'Score {} < {}'.format(int(ticker_score), SELL_THRESHOLD)
                    })
                    del positions[ticker]

        # ACHETER la meilleure action abordable
        bought = False
        for candidate in scores:
            if candidate['score'] < MIN_SCORE:
                break

            ticker = candidate['ticker']
            price = candidate['price']

            if price > cash:
                continue

            # Verifier concentration
            current_weight = 0
            if ticker in positions:
                pos_value = positions[ticker]['shares'] * price
                current_weight = pos_value / portfolio_value if portfolio_value > 0 else 0

            if current_weight > MAX_POSITION_PCT:
                continue  # Trop concentre

            # Acheter
            shares_to_buy = int(cash / price)
            if shares_to_buy > 0:
                cost = shares_to_buy * price
                cash -= cost

                if ticker in positions:
                    old = positions[ticker]
                    total_shares = old['shares'] + shares_to_buy
                    avg = ((old['shares'] * old['avg_cost']) + cost) / total_shares
                    positions[ticker] = {'shares': total_shares, 'avg_cost': avg}
                else:
                    positions[ticker] = {'shares': shares_to_buy, 'avg_cost': price}

                transactions.append({
                    'date': current_date,
                    'action': 'BUY',
                    'ticker': ticker,
                    'shares': shares_to_buy,
                    'price': price,
                    'reason': 'Score {}/100 (T:{} F:{} S:{} SM:{})'.format(
                        int(candidate['score']),
                        int(candidate['technical']),
                        int(candidate['fundamental']),
                        int(candidate['sentiment']),
                        int(candidate['smart_money'])
                    )
                })
                bought = True
                break

        # Recalculer valeur finale du mois
        portfolio_value = cash
        for ticker, pos in positions.items():
            if ticker in stock_data:
                _, details = calculate_full_score(ticker, current_date, stock_data[ticker])
                if details['price'] > 0:
                    portfolio_value += pos['shares'] * details['price']

        perf = ((portfolio_value / total_invested) - 1) * 100 if total_invested > 0 else 0
        monthly_values.append({
            'date': current_date,
            'value': portfolio_value,
            'invested': total_invested,
            'perf': perf
        })

        # Affichage periodique
        if month_num % 6 == 0 or month_num == 1:
            print('Mois {:3d} ({}) | Investi: {:8.0f} EUR | Valeur: {:8.0f} EUR | Perf: {:+6.1f}%'.format(
                month_num, current_date.strftime('%Y-%m'), total_invested, portfolio_value, perf
            ))

        current_date += relativedelta(months=1)

    # Resultats finaux
    final_value = cash
    print('\n' + '='*100)
    print('RESULTATS FINAUX')
    print('='*100)

    print('\nPositions finales:')
    for ticker, pos in sorted(positions.items(), key=lambda x: x[1]['shares'] * 100, reverse=True):
        if ticker in stock_data:
            _, details = calculate_full_score(ticker, end_date, stock_data[ticker])
            if details['price'] > 0:
                value = pos['shares'] * details['price']
                gain = ((details['price'] / pos['avg_cost']) - 1) * 100
                final_value += value
                print('  {:<10} {:>6} actions | PRU: {:>8.2f} | Prix: {:>8.2f} | Valeur: {:>10.2f} | {:+.1f}%'.format(
                    ticker, pos['shares'], pos['avg_cost'], details['price'], value, gain
                ))

    print('\n  Cash restant: {:.2f} EUR'.format(cash))

    total_gain = final_value - total_invested
    total_gain_pct = (total_gain / total_invested) * 100 if total_invested > 0 else 0
    annualized = ((final_value / total_invested) ** (1 / years) - 1) * 100 if years > 0 else 0

    print('\n' + '-'*50)
    print('PERFORMANCE GLOBALE')
    print('-'*50)
    print('  Total investi:      {:>12.2f} EUR'.format(total_invested))
    print('  Valeur finale:      {:>12.2f} EUR'.format(final_value))
    print('  Gain/Perte:         {:>+12.2f} EUR'.format(total_gain))
    print('  Performance totale: {:>+12.1f}%'.format(total_gain_pct))
    print('  Rendement annuel:   {:>+12.1f}%'.format(annualized))

    # Transactions
    print('\n' + '-'*50)
    print('TRANSACTIONS ({} total)'.format(len(transactions)))
    print('-'*50)
    buys = [t for t in transactions if t['action'] == 'BUY']
    sells = [t for t in transactions if t['action'] == 'SELL']
    print('  Achats: {}'.format(len(buys)))
    print('  Ventes: {}'.format(len(sells)))

    print('\nDernieres transactions:')
    for tx in transactions[-10:]:
        print('  {} | {:4} | {:<10} | {:>5} x {:>8.2f} | {}'.format(
            tx['date'].strftime('%Y-%m'),
            tx['action'],
            tx['ticker'],
            tx['shares'],
            tx['price'],
            tx['reason']
        ))

    return {
        'total_invested': total_invested,
        'final_value': final_value,
        'gain': total_gain,
        'gain_pct': total_gain_pct,
        'annualized': annualized,
        'positions': positions,
        'transactions': transactions,
        'monthly_values': monthly_values
    }


if __name__ == '__main__':
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else 'CTO'
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    print('\n' + '#'*100)
    print('# LANCEMENT BACKTEST GLOBAL')
    print('# Mode: {} | Duree: {} ans'.format(mode, years))
    print('#'*100 + '\n')

    result = run_global_backtest(mode=mode, years=years, monthly_investment=100.0)
