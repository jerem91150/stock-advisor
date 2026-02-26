"""
Backtest MODE BUY & HOLD - Jamais de vente
Compare avec le mode avec ventes automatiques
"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
MONTHLY_INVESTMENT = 100.0
MIN_SCORE = 55
MAX_POSITION_PCT = 0.30

# Actions globales
STOCKS_US = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'JPM', 'V',
             'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS', 'NFLX', 'ADBE', 'CRM', 'INTC',
             'AMD', 'PYPL', 'NKE', 'KO', 'PEP', 'MRK', 'PFE']
STOCKS_EU = ['MC.PA', 'OR.PA', 'SAN.PA', 'AI.PA', 'SU.PA', 'BNP.PA', 'GLE.PA', 'CAP.PA',
             'ACA.PA', 'VIV.PA', 'KER.PA', 'RMS.PA', 'TTE.PA', 'SAP.DE', 'SIE.DE', 'ALV.DE',
             'DTE.DE', 'BAS.DE', 'BMW.DE', 'ASML.AS', 'PHIA.AS', 'UNA.AS', 'ENEL.MI', 'ENI.MI', 'ISP.MI']
STOCKS_ASIA = ['7203.T', '6758.T', '9984.T', '6861.T', '8306.T', 'BABA', 'JD', 'PDD', 'BIDU', 'NIO']

def run_backtest(mode, years, allow_sell=True, monthly_investment=100):
    """
    Backtest avec ou sans ventes
    allow_sell=True : vend quand score < 40
    allow_sell=False : ne vend jamais (buy & hold)
    """
    end_date = datetime(2026, 1, 30)
    start_date = end_date - relativedelta(years=years)

    if mode == 'CTO':
        stocks = STOCKS_US + STOCKS_EU + STOCKS_ASIA
    else:  # PEA
        stocks = STOCKS_EU

    # Charger les donnees
    print(f"  Chargement des donnees pour {len(stocks)} actions...")
    data = {}
    for ticker in stocks:
        try:
            df = yf.download(ticker, start=start_date - timedelta(days=250), end=end_date + timedelta(days=5), progress=False)
            if not df.empty and len(df) > 50:
                data[ticker] = df
        except:
            pass

    print(f"  {len(data)} actions chargees")

    if len(data) < 5:
        return None

    def get_price(ticker, date):
        if ticker not in data:
            return None
        df = data[ticker]
        mask = df.index <= pd.Timestamp(date)
        if mask.any():
            close = df.loc[mask, 'Close'].iloc[-1]
            if hasattr(close, 'iloc'):
                return float(close.iloc[0])
            return float(close)
        return None

    def calculate_score(ticker, date):
        if ticker not in data:
            return 50
        df = data[ticker]
        mask = df.index <= pd.Timestamp(date)
        if not mask.any() or mask.sum() < 50:
            return 50
        recent = df.loc[mask].tail(200)
        if len(recent) < 50:
            return 50

        current = float(recent['Close'].iloc[-1].iloc[0]) if hasattr(recent['Close'].iloc[-1], 'iloc') else float(recent['Close'].iloc[-1])
        ma50 = float(recent['Close'].tail(50).mean())
        ma200 = float(recent['Close'].mean()) if len(recent) >= 200 else ma50

        # Score technique
        score = 50
        if current > ma50: score += 15
        if ma50 > ma200: score += 10

        if len(recent) >= 21:
            price_1m = float(recent['Close'].iloc[-21].iloc[0]) if hasattr(recent['Close'].iloc[-21], 'iloc') else float(recent['Close'].iloc[-21])
            mom = (current / price_1m - 1) * 100
            if mom > 5: score += 10
            elif mom > 0: score += 5
            elif mom < -5: score -= 10

        returns = recent['Close'].pct_change().dropna()
        vol = float(returns.std() * np.sqrt(252) * 100)
        if vol < 20: score += 5
        elif vol > 35: score -= 10

        return max(0, min(100, score))

    def select_best_stock(date, cash, positions):
        candidates = []
        portfolio_value = cash
        for ticker, pos in positions.items():
            price = get_price(ticker, date)
            if price:
                portfolio_value += pos['shares'] * price

        for ticker in data.keys():
            price = get_price(ticker, date)
            if not price or price <= 0 or price > cash:
                continue

            score = calculate_score(ticker, date)
            if score < MIN_SCORE:
                continue

            current_weight = 0
            if ticker in positions:
                pos_value = positions[ticker]['shares'] * price
                current_weight = pos_value / portfolio_value if portfolio_value > 0 else 0

            # Bonus diversification
            if current_weight < 0.10:
                adj_score = score + 10
            elif current_weight < 0.20:
                adj_score = score + 5
            elif current_weight > MAX_POSITION_PCT:
                adj_score = score - 20
            else:
                adj_score = score

            candidates.append({'ticker': ticker, 'price': price, 'score': score, 'adj_score': adj_score})

        if not candidates:
            return None
        candidates.sort(key=lambda x: x['adj_score'], reverse=True)
        return candidates[0]

    # Simulation
    cash = 0.0
    positions = {}
    total_invested = 0.0
    nb_achats = 0
    nb_ventes = 0

    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        cash += monthly_investment
        total_invested += monthly_investment

        # Ventes si autorisees et score < 40
        if allow_sell:
            positions_to_sell = []
            for ticker, pos in positions.items():
                score = calculate_score(ticker, current_date)
                if score < 40:
                    positions_to_sell.append(ticker)

            for ticker in positions_to_sell:
                price = get_price(ticker, current_date)
                if price:
                    cash += positions[ticker]['shares'] * price
                    del positions[ticker]
                    nb_ventes += 1

        # Achats
        best = select_best_stock(current_date, cash, positions)
        if best:
            shares = int(cash / best['price'])
            if shares > 0:
                cost = shares * best['price']
                cash -= cost
                ticker = best['ticker']
                if ticker in positions:
                    old = positions[ticker]
                    total_shares = old['shares'] + shares
                    avg = ((old['shares'] * old['avg_cost']) + cost) / total_shares
                    positions[ticker] = {'shares': total_shares, 'avg_cost': avg}
                else:
                    positions[ticker] = {'shares': shares, 'avg_cost': best['price']}
                nb_achats += 1

        current_date += relativedelta(months=1)

    # Valeur finale
    final_value = cash
    for ticker, pos in positions.items():
        price = get_price(ticker, end_date)
        if price:
            final_value += pos['shares'] * price

    gain = final_value - total_invested
    perf_total = (final_value / total_invested - 1) * 100
    perf_annual = ((final_value / total_invested) ** (1/years) - 1) * 100

    return {
        'invested': total_invested,
        'final_value': final_value,
        'gain': gain,
        'perf_total': perf_total,
        'perf_annual': perf_annual,
        'nb_positions': len(positions),
        'nb_achats': nb_achats,
        'nb_ventes': nb_ventes
    }


if __name__ == "__main__":
    print('='*100)
    print('COMPARAISON: BUY & HOLD vs AVEC VENTES AUTOMATIQUES')
    print('='*100)

    results_hold = {}
    results_sell = {}

    # 3 ans et 5 ans
    for years in [3, 5]:
        for mode in ['CTO', 'PEA']:
            key = f'{mode}_{years}ans'

            print(f'\n--- {key} ---')

            # Buy & Hold
            print(f'  Mode BUY & HOLD...')
            r_hold = run_backtest(mode, years, allow_sell=False)
            if r_hold:
                results_hold[key] = r_hold

            # Avec ventes
            print(f'  Mode AVEC VENTES...')
            r_sell = run_backtest(mode, years, allow_sell=True)
            if r_sell:
                results_sell[key] = r_sell

    # 10 ans CTO seulement
    print(f'\n--- CTO_10ans ---')
    print(f'  Mode BUY & HOLD...')
    r_hold = run_backtest('CTO', 10, allow_sell=False)
    if r_hold:
        results_hold['CTO_10ans'] = r_hold

    print(f'  Mode AVEC VENTES...')
    r_sell = run_backtest('CTO', 10, allow_sell=True)
    if r_sell:
        results_sell['CTO_10ans'] = r_sell

    # Affichage
    print('\n' + '='*100)
    print('RESULTATS BUY & HOLD (jamais de vente)')
    print('='*100)
    print(f'{"Config":<15} {"Investi":>10} {"Valeur":>12} {"Gain":>12} {"Rend/an":>10} {"Positions":>10}')
    print('-'*75)
    for key in ['CTO_3ans', 'PEA_3ans', 'CTO_5ans', 'PEA_5ans', 'CTO_10ans']:
        if key in results_hold:
            r = results_hold[key]
            print(f'{key:<15} {r["invested"]:>10.0f} EUR {r["final_value"]:>10.0f} EUR {r["gain"]:>+10.0f} EUR {r["perf_annual"]:>+9.1f}% {r["nb_positions"]:>10}')

    print('\n' + '='*100)
    print('RESULTATS AVEC VENTES (vend si score < 40)')
    print('='*100)
    print(f'{"Config":<15} {"Investi":>10} {"Valeur":>12} {"Gain":>12} {"Rend/an":>10} {"Ventes":>10}')
    print('-'*75)
    for key in ['CTO_3ans', 'PEA_3ans', 'CTO_5ans', 'PEA_5ans', 'CTO_10ans']:
        if key in results_sell:
            r = results_sell[key]
            print(f'{key:<15} {r["invested"]:>10.0f} EUR {r["final_value"]:>10.0f} EUR {r["gain"]:>+10.0f} EUR {r["perf_annual"]:>+9.1f}% {r["nb_ventes"]:>10}')

    print('\n' + '='*100)
    print('COMPARAISON DIRECTE')
    print('='*100)
    print(f'{"Config":<15} {"Buy&Hold":>12} {"Avec Ventes":>12} {"Difference":>12} {"Meilleur":>15}')
    print('-'*70)
    for key in ['CTO_3ans', 'PEA_3ans', 'CTO_5ans', 'PEA_5ans', 'CTO_10ans']:
        if key in results_hold and key in results_sell:
            rh = results_hold[key]
            rs = results_sell[key]
            diff = rh['perf_annual'] - rs['perf_annual']
            winner = "BUY & HOLD" if diff > 0 else "AVEC VENTES" if diff < 0 else "EGAL"
            print(f'{key:<15} {rh["perf_annual"]:>+11.1f}% {rs["perf_annual"]:>+11.1f}% {diff:>+11.1f} pts {winner:>15}')
