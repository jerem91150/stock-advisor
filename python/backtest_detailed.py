"""
Backtest detaille avec affichage de chaque decision.
"""
import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Configuration
MONTHLY_INVESTMENT = 100.0
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)

STOCKS = ['MC.PA', 'BNP.PA', 'GLE.PA', 'TTE.PA', 'SAN.PA', 'OR.PA', 'ACA.PA']

print('='*100)
print('BACKTEST DETAILLE - VERIFICATION MOIS PAR MOIS')
print('Periode: {} -> {}'.format(START_DATE.strftime("%Y-%m-%d"), END_DATE.strftime("%Y-%m-%d")))
print('Investissement mensuel: {} EUR'.format(MONTHLY_INVESTMENT))
print('='*100)

print('\n[1] CHARGEMENT DES DONNEES HISTORIQUES...')
data = {}
for ticker in STOCKS:
    try:
        df = yf.download(ticker, start=START_DATE - timedelta(days=250), end=END_DATE + timedelta(days=5), progress=False)
        if not df.empty:
            data[ticker] = df
            print('  {}: {} jours de donnees'.format(ticker, len(df)))
    except Exception as e:
        print('  {}: ERREUR - {}'.format(ticker, e))

def get_price(ticker, date, data):
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

def calculate_score(ticker, date, data):
    if ticker not in data:
        return 50, {}

    df = data[ticker]
    mask = df.index <= pd.Timestamp(date)
    if not mask.any() or mask.sum() < 50:
        return 50, {}

    recent = df.loc[mask].tail(200)
    if len(recent) < 50:
        return 50, {}

    details = {}
    score = 50  # Score de base

    # Prix actuel
    current = recent['Close'].iloc[-1]
    if hasattr(current, 'iloc'):
        current = float(current.iloc[0])
    else:
        current = float(current)
    details['prix'] = current

    # MA50
    ma50 = float(recent['Close'].tail(50).mean())
    if hasattr(ma50, 'iloc'):
        ma50 = float(ma50.iloc[0])
    details['ma50'] = ma50

    # Signal tendance: Prix vs MA50
    if current > ma50:
        score += 15
        details['tendance'] = 'HAUSSIERE (+15 pts)'
    else:
        score -= 10
        details['tendance'] = 'BAISSIERE (-10 pts)'

    # Momentum 3 mois
    if len(recent) >= 63:
        price_3m = recent['Close'].iloc[-63]
        if hasattr(price_3m, 'iloc'):
            price_3m = float(price_3m.iloc[0])
        else:
            price_3m = float(price_3m)
        momentum = float((current / price_3m - 1) * 100)
        details['momentum_3m'] = '{:.1f}%'.format(momentum)

        if momentum > 10:
            score += 15
            details['signal_momentum'] = 'FORT (+15 pts)'
        elif momentum > 0:
            score += 5
            details['signal_momentum'] = 'POSITIF (+5 pts)'
        elif momentum < -10:
            score -= 15
            details['signal_momentum'] = 'NEGATIF (-15 pts)'
        else:
            details['signal_momentum'] = 'NEUTRE (0 pts)'

    # Volatilite annualisee
    returns = recent['Close'].pct_change().dropna()
    vol = float(returns.std() * np.sqrt(252) * 100)
    details['volatilite'] = '{:.1f}%'.format(vol)

    if vol < 20:
        score += 10
        details['signal_vol'] = 'FAIBLE (+10 pts)'
    elif vol > 40:
        score -= 10
        details['signal_vol'] = 'ELEVEE (-10 pts)'
    else:
        details['signal_vol'] = 'NORMALE (0 pts)'

    return max(0, min(100, score)), details


print('\n' + '='*100)
print('[2] SIMULATION MOIS PAR MOIS')
print('='*100)

cash = 0.0
positions = {}
total_invested = 0.0

current_date = START_DATE.replace(day=1)
month_num = 0

while current_date <= END_DATE:
    month_num += 1
    print('\n' + '#'*100)
    print('MOIS {}: {}'.format(month_num, current_date.strftime("%B %Y").upper()))
    print('#'*100)

    # Etape 1: Ajout investissement
    cash += MONTHLY_INVESTMENT
    total_invested += MONTHLY_INVESTMENT
    print('\n>>> ETAPE 1: INVESTISSEMENT')
    print('    Ajout mensuel: +{} EUR'.format(MONTHLY_INVESTMENT))
    print('    Cash disponible: {:.2f} EUR'.format(cash))

    # Etape 2: Analyse des actions
    print('\n>>> ETAPE 2: ANALYSE DES ACTIONS')
    print('-'*100)

    scores = {}
    for ticker in STOCKS:
        if ticker in data:
            score, details = calculate_score(ticker, current_date, data)
            scores[ticker] = score

            print('\n  {}:'.format(ticker))
            print('    Prix actuel: {:.2f} EUR'.format(details.get('prix', 0)))
            print('    Moyenne Mobile 50j: {:.2f} EUR'.format(details.get('ma50', 0)))
            print('    -> Tendance: {}'.format(details.get('tendance', 'N/A')))
            print('    Variation 3 mois: {}'.format(details.get('momentum_3m', 'N/A')))
            print('    -> Momentum: {}'.format(details.get('signal_momentum', 'N/A')))
            print('    Volatilite annualisee: {}'.format(details.get('volatilite', 'N/A')))
            print('    -> Risque: {}'.format(details.get('signal_vol', 'N/A')))
            print('    =======> SCORE TOTAL: {}/100'.format(score))

    # Etape 3: Classement
    print('\n>>> ETAPE 3: CLASSEMENT')
    print('-'*50)
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for i, (ticker, score) in enumerate(sorted_scores, 1):
        price = get_price(ticker, current_date, data)
        marker = " <-- MEILLEUR" if i == 1 else ""
        print('  {}. {}: {}/100 (prix: {:.2f} EUR){}'.format(i, ticker, score, price if price else 0, marker))

    # Etape 4: Decision
    print('\n>>> ETAPE 4: DECISION')
    print('-'*50)

    best_ticker, best_score = sorted_scores[0]
    best_price = get_price(best_ticker, current_date, data)

    if best_score >= 50 and best_price and best_price > 0:
        shares_to_buy = int(cash / best_price)
        if shares_to_buy > 0:
            cost = shares_to_buy * best_price
            cash -= cost

            if best_ticker in positions:
                old = positions[best_ticker]
                total_shares = old['shares'] + shares_to_buy
                avg = ((old['shares'] * old['avg_cost']) + cost) / total_shares
                positions[best_ticker] = {'shares': total_shares, 'avg_cost': avg}
                print('  ACTION: ACHAT (renforcement)')
            else:
                positions[best_ticker] = {'shares': shares_to_buy, 'avg_cost': best_price}
                print('  ACTION: ACHAT (nouvelle position)')

            print('  Detail: {} x {} @ {:.2f} EUR = {:.2f} EUR'.format(shares_to_buy, best_ticker, best_price, cost))
            print('  Raison: Meilleur score ({}/100 >= 50)'.format(best_score))
            print('  Cash restant: {:.2f} EUR'.format(cash))
        else:
            print('  ACTION: AUCUNE')
            print('  Raison: Prix trop eleve ({:.2f} EUR > {:.2f} EUR cash)'.format(best_price, cash))
    else:
        print('  ACTION: AUCUNE')
        print('  Raison: Meilleur score insuffisant ({}/100 < 50)'.format(best_score))

    # Etape 5: Etat du portefeuille
    print('\n>>> ETAPE 5: ETAT DU PORTEFEUILLE')
    print('-'*50)
    print('  Cash: {:.2f} EUR'.format(cash))

    portfolio_value = cash
    if positions:
        print('  Positions:')
        for ticker, pos in positions.items():
            current_price = get_price(ticker, current_date, data)
            if current_price:
                value = pos['shares'] * current_price
                gain = ((current_price / pos['avg_cost']) - 1) * 100
                portfolio_value += value
                print('    - {}: {} actions x {:.2f} EUR = {:.2f} EUR ({:+.1f}%)'.format(
                    ticker, pos['shares'], current_price, value, gain))

    print('  ' + '='*40)
    print('  VALEUR TOTALE: {:.2f} EUR'.format(portfolio_value))
    print('  INVESTI: {:.2f} EUR'.format(total_invested))
    perf = ((portfolio_value/total_invested)-1)*100
    print('  PERFORMANCE: {:+.1f}%'.format(perf))

    current_date += relativedelta(months=1)

print('\n' + '='*100)
print('RESUME FINAL')
print('='*100)
print('Total investi: {:.2f} EUR'.format(total_invested))
print('Valeur finale: {:.2f} EUR'.format(portfolio_value))
print('Gain: {:+.2f} EUR ({:+.1f}%)'.format(portfolio_value - total_invested, perf))
print('\nPositions finales:')
for ticker, pos in positions.items():
    current_price = get_price(ticker, END_DATE, data)
    if current_price:
        value = pos['shares'] * current_price
        gain = ((current_price / pos['avg_cost']) - 1) * 100
        print('  - {}: {} actions, PRU {:.2f} EUR, valeur {:.2f} EUR ({:+.1f}%)'.format(
            ticker, pos['shares'], pos['avg_cost'], value, gain))
