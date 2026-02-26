"""
Backtest INTELLIGENT avec logique de selection amelioree.

Criteres de selection:
1. Score qualite >= 50 (action valide)
2. Prix abordable (on peut acheter au moins 1 action)
3. Diversification (max 40% du portefeuille par action)
4. Score ajuste = Score * (1 + bonus diversification)
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
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2025, 1, 1)
MAX_POSITION_PCT = 0.40  # Max 40% du portefeuille par action
MIN_SCORE = 50  # Score minimum pour acheter

STOCKS = ['MC.PA', 'BNP.PA', 'GLE.PA', 'TTE.PA', 'SAN.PA', 'OR.PA', 'ACA.PA', 'CAP.PA', 'AI.PA']

print('='*100)
print('BACKTEST INTELLIGENT - SELECTION EQUILIBREE')
print('Periode: {} -> {}'.format(START_DATE.strftime("%Y-%m-%d"), END_DATE.strftime("%Y-%m-%d")))
print('Investissement mensuel: {} EUR'.format(MONTHLY_INVESTMENT))
print('Score minimum: {}/100'.format(MIN_SCORE))
print('Max par position: {}%'.format(int(MAX_POSITION_PCT * 100)))
print('='*100)

# Charger les donnees
print('\n[CHARGEMENT DES DONNEES]')
data = {}
for ticker in STOCKS:
    try:
        df = yf.download(ticker, start=START_DATE - timedelta(days=250), end=END_DATE + timedelta(days=5), progress=False)
        if not df.empty:
            data[ticker] = df
            print('  {} : {} jours'.format(ticker, len(df)))
    except:
        pass

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
    """Calcule le score technique d'une action."""
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
    score = 50

    # Prix actuel
    current = float(recent['Close'].iloc[-1].iloc[0]) if hasattr(recent['Close'].iloc[-1], 'iloc') else float(recent['Close'].iloc[-1])
    details['prix'] = current

    # MA50 et MA200
    ma50 = float(recent['Close'].tail(50).mean())
    ma200 = float(recent['Close'].mean()) if len(recent) >= 200 else ma50
    details['ma50'] = ma50
    details['ma200'] = ma200

    # Signal Court Terme: Prix vs MA50
    if current > ma50 * 1.02:  # 2% au-dessus
        score += 10
        details['ct'] = 'FORT (+10)'
    elif current > ma50:
        score += 5
        details['ct'] = 'POSITIF (+5)'
    elif current < ma50 * 0.98:  # 2% en-dessous
        score -= 10
        details['ct'] = 'FAIBLE (-10)'
    else:
        details['ct'] = 'NEUTRE (0)'

    # Signal Moyen Terme: MA50 vs MA200
    if ma50 > ma200 * 1.05:  # Golden cross fort
        score += 15
        details['mt'] = 'GOLDEN CROSS (+15)'
    elif ma50 > ma200:
        score += 5
        details['mt'] = 'HAUSSIER (+5)'
    elif ma50 < ma200 * 0.95:  # Death cross
        score -= 15
        details['mt'] = 'DEATH CROSS (-15)'
    else:
        score -= 5
        details['mt'] = 'BAISSIER (-5)'

    # Momentum 1 mois (court terme)
    if len(recent) >= 21:
        price_1m = float(recent['Close'].iloc[-21].iloc[0]) if hasattr(recent['Close'].iloc[-21], 'iloc') else float(recent['Close'].iloc[-21])
        mom_1m = (current / price_1m - 1) * 100
        details['mom_1m'] = '{:.1f}%'.format(mom_1m)
        if mom_1m > 5:
            score += 10
            details['sig_1m'] = 'FORT (+10)'
        elif mom_1m > 0:
            score += 5
            details['sig_1m'] = 'POSITIF (+5)'
        elif mom_1m < -5:
            score -= 10
            details['sig_1m'] = 'NEGATIF (-10)'
        else:
            details['sig_1m'] = 'NEUTRE (0)'

    # Momentum 3 mois (moyen terme)
    if len(recent) >= 63:
        price_3m = float(recent['Close'].iloc[-63].iloc[0]) if hasattr(recent['Close'].iloc[-63], 'iloc') else float(recent['Close'].iloc[-63])
        mom_3m = (current / price_3m - 1) * 100
        details['mom_3m'] = '{:.1f}%'.format(mom_3m)
        if mom_3m > 10:
            score += 10
            details['sig_3m'] = 'FORT (+10)'
        elif mom_3m > 0:
            score += 5
            details['sig_3m'] = 'POSITIF (+5)'
        elif mom_3m < -10:
            score -= 10
            details['sig_3m'] = 'NEGATIF (-10)'
        else:
            details['sig_3m'] = 'NEUTRE (0)'

    # Volatilite (risque)
    returns = recent['Close'].pct_change().dropna()
    vol = float(returns.std() * np.sqrt(252) * 100)
    details['vol'] = '{:.1f}%'.format(vol)
    if vol < 20:
        score += 5
        details['sig_vol'] = 'FAIBLE RISQUE (+5)'
    elif vol > 35:
        score -= 10
        details['sig_vol'] = 'RISQUE ELEVE (-10)'
    else:
        details['sig_vol'] = 'RISQUE NORMAL (0)'

    return max(0, min(100, score)), details


def select_best_stock(date, cash, positions):
    """
    Selectionne la meilleure action a acheter en tenant compte:
    1. Du score qualite
    2. De l'accessibilite (prix)
    3. De la diversification du portefeuille
    """
    candidates = []

    # Calculer la valeur totale du portefeuille
    portfolio_value = cash
    for ticker, pos in positions.items():
        price = get_price(ticker, date)
        if price:
            portfolio_value += pos['shares'] * price

    for ticker in STOCKS:
        if ticker not in data:
            continue

        price = get_price(ticker, date)
        if not price or price <= 0:
            continue

        # Verifier si on peut acheter au moins 1 action
        if price > cash:
            continue

        score, details = calculate_score(ticker, date)

        # Score minimum requis
        if score < MIN_SCORE:
            continue

        # Calculer le poids actuel de cette position
        current_weight = 0
        if ticker in positions:
            pos_value = positions[ticker]['shares'] * price
            current_weight = pos_value / portfolio_value if portfolio_value > 0 else 0

        # Bonus diversification: favoriser les actions sous-representees
        diversification_bonus = 0
        if current_weight < 0.10:  # Moins de 10%
            diversification_bonus = 10
        elif current_weight < 0.20:  # Moins de 20%
            diversification_bonus = 5
        elif current_weight > MAX_POSITION_PCT:  # Trop concentre
            diversification_bonus = -20  # Penalite

        # Score ajuste
        adjusted_score = score + diversification_bonus

        # Nombre d'actions qu'on peut acheter
        shares_affordable = int(cash / price)

        candidates.append({
            'ticker': ticker,
            'price': price,
            'score': score,
            'adjusted_score': adjusted_score,
            'diversification_bonus': diversification_bonus,
            'current_weight': current_weight * 100,
            'shares_affordable': shares_affordable,
            'details': details
        })

    if not candidates:
        return None

    # Trier par score ajuste
    candidates.sort(key=lambda x: x['adjusted_score'], reverse=True)

    return candidates


# Simulation
print('\n' + '='*100)
print('SIMULATION MOIS PAR MOIS')
print('='*100)

cash = 0.0
positions = {}
total_invested = 0.0
transactions = []

current_date = START_DATE.replace(day=1)
month_num = 0

while current_date <= END_DATE:
    month_num += 1
    print('\n' + '#'*100)
    print('MOIS {}: {}'.format(month_num, current_date.strftime("%B %Y").upper()))
    print('#'*100)

    # Ajout investissement
    cash += MONTHLY_INVESTMENT
    total_invested += MONTHLY_INVESTMENT

    # Calculer valeur portefeuille
    portfolio_value = cash
    for ticker, pos in positions.items():
        price = get_price(ticker, current_date)
        if price:
            portfolio_value += pos['shares'] * price

    print('\n>>> SITUATION AVANT DECISION')
    print('    Cash: {:.2f} EUR'.format(cash))
    print('    Valeur portefeuille: {:.2f} EUR'.format(portfolio_value))

    # Obtenir les candidats
    candidates = select_best_stock(current_date, cash, positions)

    print('\n>>> ANALYSE DES ACTIONS ABORDABLES (score >= {}):'.format(MIN_SCORE))
    print('-'*100)

    if candidates:
        print('{:<10} {:>8} {:>8} {:>10} {:>12} {:>10} {:>8}'.format(
            'Ticker', 'Prix', 'Score', 'Bonus Div', 'Score Adj', 'Poids Act', 'Achetable'
        ))
        print('-'*100)
        for c in candidates[:5]:  # Top 5
            print('{:<10} {:>8.2f} {:>8}/100 {:>+10} {:>12}/100 {:>9.1f}% {:>8}'.format(
                c['ticker'], c['price'], c['score'], c['diversification_bonus'],
                c['adjusted_score'], c['current_weight'], c['shares_affordable']
            ))

        # Meilleur choix
        best = candidates[0]

        print('\n>>> DECISION')
        print('-'*50)
        print('  Choix: {} (Score ajuste: {}/100)'.format(best['ticker'], best['adjusted_score']))
        print('  Raisons:')
        print('    - Score qualite: {}/100'.format(best['score']))
        print('    - Bonus diversification: {:+d}'.format(best['diversification_bonus']))
        print('    - Prix unitaire: {:.2f} EUR'.format(best['price']))
        print('    - Actions achetables: {}'.format(best['shares_affordable']))

        # Achat
        shares_to_buy = best['shares_affordable']
        if shares_to_buy > 0:
            cost = shares_to_buy * best['price']
            cash -= cost

            ticker = best['ticker']
            if ticker in positions:
                old = positions[ticker]
                total_shares = old['shares'] + shares_to_buy
                avg = ((old['shares'] * old['avg_cost']) + cost) / total_shares
                positions[ticker] = {'shares': total_shares, 'avg_cost': avg}
                action_type = 'RENFORCEMENT'
            else:
                positions[ticker] = {'shares': shares_to_buy, 'avg_cost': best['price']}
                action_type = 'NOUVELLE POSITION'

            transactions.append({
                'date': current_date,
                'action': 'BUY',
                'ticker': ticker,
                'shares': shares_to_buy,
                'price': best['price'],
                'total': cost
            })

            print('\n  >>> ACHAT ({})'.format(action_type))
            print('      {} x {} @ {:.2f} EUR = {:.2f} EUR'.format(
                shares_to_buy, ticker, best['price'], cost
            ))
    else:
        print('  Aucune action disponible avec score >= {} et prix <= {:.2f} EUR'.format(
            MIN_SCORE, cash
        ))

    # Etat du portefeuille
    print('\n>>> PORTEFEUILLE APRES DECISION')
    print('-'*50)
    print('  Cash: {:.2f} EUR'.format(cash))

    portfolio_value = cash
    if positions:
        print('  Positions:')
        for ticker, pos in sorted(positions.items()):
            price = get_price(ticker, current_date)
            if price:
                value = pos['shares'] * price
                gain = ((price / pos['avg_cost']) - 1) * 100
                weight = value / (portfolio_value + value - cash) * 100 if portfolio_value > cash else 0
                portfolio_value += value
                print('    {}: {} x {:.2f} EUR = {:.2f} EUR ({:+.1f}%) [poids: {:.1f}%]'.format(
                    ticker, pos['shares'], price, value, gain, weight
                ))

    perf = ((portfolio_value / total_invested) - 1) * 100
    print('  ' + '='*40)
    print('  TOTAL: {:.2f} EUR (investi: {:.2f} EUR)'.format(portfolio_value, total_invested))
    print('  PERFORMANCE: {:+.1f}%'.format(perf))

    current_date += relativedelta(months=1)

# Resume final
print('\n' + '='*100)
print('RESUME FINAL')
print('='*100)

final_value = cash
print('\nPositions finales:')
for ticker, pos in sorted(positions.items()):
    price = get_price(ticker, END_DATE)
    if price:
        value = pos['shares'] * price
        gain = ((price / pos['avg_cost']) - 1) * 100
        final_value += value
        print('  {}: {} actions, PRU {:.2f} EUR, valeur {:.2f} EUR ({:+.1f}%)'.format(
            ticker, pos['shares'], pos['avg_cost'], value, gain
        ))

print('\nResultat:')
print('  Total investi: {:.2f} EUR'.format(total_invested))
print('  Valeur finale: {:.2f} EUR'.format(final_value))
print('  Gain/Perte: {:+.2f} EUR ({:+.1f}%)'.format(final_value - total_invested, ((final_value/total_invested)-1)*100))

print('\nTransactions effectuees: {}'.format(len(transactions)))
for tx in transactions:
    print('  {} - {} {} x {} @ {:.2f} EUR'.format(
        tx['date'].strftime('%Y-%m'), tx['action'], tx['shares'], tx['ticker'], tx['price']
    ))
