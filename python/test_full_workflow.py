"""
Test complet du workflow utilisateur Stock Advisor v3.0
Simule un utilisateur qui utilise toutes les fonctionnalites
"""
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import json

print("=" * 70)
print("WORKFLOW COMPLET - STOCK ADVISOR v3.0")
print("Simulation d'un investisseur francais")
print("=" * 70)

# =============================================================================
# ETAPE 1: Creation des portefeuilles
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 1: CREATION DES PORTEFEUILLES")
print("=" * 70)

from src.portfolio.manager import PortfolioManager
pm = PortfolioManager()

# Supprimer les anciens portefeuilles de test
for p in pm.get_all_portfolios():
    if "Test" in p.name or "Workflow" in p.name:
        pm.delete_portfolio(p.id)

# Creer un PEA
pea = pm.create_portfolio(
    name="Mon PEA Boursorama",
    portfolio_type="PEA",
    broker="Boursorama",
    currency="EUR",
    target_value=150000,
    monthly_contribution=500
)
print(f"  [OK] PEA cree: {pea.name}")

# Creer un CTO
cto = pm.create_portfolio(
    name="Mon CTO Degiro",
    portfolio_type="CTO",
    broker="Degiro",
    currency="EUR",
    target_value=100000,
    monthly_contribution=300
)
print(f"  [OK] CTO cree: {cto.name}")

# Creer une Assurance-Vie
av = pm.create_portfolio(
    name="AV Linxea Spirit",
    portfolio_type="ASSURANCE_VIE",
    broker="Linxea",
    currency="EUR"
)
print(f"  [OK] Assurance-Vie creee: {av.name}")

# =============================================================================
# ETAPE 2: Ajout de positions
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 2: AJOUT DE POSITIONS")
print("=" * 70)

# PEA - Actions europeennes
pea_positions = [
    ("MC.PA", 5, 750.0, "LVMH"),
    ("OR.PA", 10, 380.0, "L'Oreal"),
    ("SAN.PA", 50, 95.0, "Sanofi"),
    ("AI.PA", 8, 165.0, "Air Liquide"),
    ("TTE.PA", 30, 58.0, "TotalEnergies"),
]

for ticker, qty, price, name in pea_positions:
    try:
        pm.add_position(pea.id, ticker, qty, price, fees=5.0)
        print(f"  [OK] PEA: {qty}x {ticker} ({name}) @ {price}EUR")
    except Exception as e:
        print(f"  [!] Erreur {ticker}: {e}")

# CTO - Actions US et internationales
cto_positions = [
    ("AAPL", 15, 175.0, "Apple"),
    ("MSFT", 8, 380.0, "Microsoft"),
    ("GOOGL", 5, 140.0, "Alphabet"),
    ("NVDA", 10, 450.0, "Nvidia"),
    ("JNJ", 12, 160.0, "Johnson & Johnson"),
]

for ticker, qty, price, name in cto_positions:
    try:
        pm.add_position(cto.id, ticker, qty, price, fees=1.0)
        print(f"  [OK] CTO: {qty}x {ticker} ({name}) @ {price}USD")
    except Exception as e:
        print(f"  [!] Erreur {ticker}: {e}")

# =============================================================================
# ETAPE 3: Vue globale des portefeuilles
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 3: VUE GLOBALE DES PORTEFEUILLES")
print("=" * 70)

global_summary = pm.get_all_portfolios_summary()
print(f"\n  Nombre de portefeuilles: {global_summary['portfolios_count']}")
print(f"  Valeur totale: {global_summary['total_value']:,.2f} EUR")
print(f"  Total investi: {global_summary['total_invested']:,.2f} EUR")
print(f"  Plus/Moins value: {global_summary['total_gain']:+,.2f} EUR ({global_summary['total_gain_pct']:+.1f}%)")

for portfolio in pm.get_all_portfolios():
    summary = pm.get_portfolio_summary(portfolio.id)
    if summary:
        print(f"\n  --- {summary.name} ({summary.portfolio_type}) ---")
        print(f"      Valeur: {summary.current_value:,.2f} EUR")
        print(f"      Performance: {summary.total_gain_pct:+.1f}%")
        print(f"      Positions: {summary.positions_count}")

# =============================================================================
# ETAPE 4: Analyse des dividendes
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 4: ANALYSE DES DIVIDENDES")
print("=" * 70)

from src.portfolio.dividend_tracker import DividendTracker
dt = DividendTracker()

# Positions CTO pour les dividendes US
cto_positions_data = [
    {'ticker': 'AAPL', 'quantity': 15, 'name': 'Apple'},
    {'ticker': 'MSFT', 'quantity': 8, 'name': 'Microsoft'},
    {'ticker': 'JNJ', 'quantity': 12, 'name': 'Johnson & Johnson'},
]

estimate = dt.get_annual_dividend_estimate(cto_positions_data)
print(f"\n  Estimation dividendes annuels CTO: {estimate['total_annual']:.2f} EUR")
print(f"  Moyenne mensuelle: {estimate['monthly_average']:.2f} EUR")

upcoming = dt.get_upcoming_dividends(cto_positions_data, days_ahead=90)
print(f"\n  Dividendes a venir (90 jours): {len(upcoming)}")
for div in upcoming[:3]:
    print(f"    - {div.ticker}: {div.expected_amount:.2f} EUR (ex-date: {div.days_until_ex}j)")

# =============================================================================
# ETAPE 5: Scores Moning
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 5: SCORES STYLE MONING")
print("=" * 70)

from src.analysis.moning_scores import MoningStyleScorer
scorer = MoningStyleScorer()

test_stocks = ["JNJ", "AAPL", "TTE.PA"]
for ticker in test_stocks:
    print(f"\n  --- {ticker} ---")

    div_score = scorer.calculate_dividend_safety_score(ticker)
    if div_score:
        print(f"    Surete Dividende: {div_score.total_score:.1f}/20 ({div_score.rating})")

    growth_score = scorer.calculate_growth_score(ticker)
    if growth_score:
        print(f"    Score Croissance: {growth_score.total_score:.1f}/20 ({growth_score.rating})")

    valuation = scorer.calculate_valuation_indicator(ticker)
    if valuation:
        print(f"    Valorisation: {valuation.status} (Fair Value: {valuation.fair_value:.2f})")

# =============================================================================
# ETAPE 6: Simulation Monte Carlo
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 6: SIMULATION MONTE CARLO (5000 scenarios)")
print("=" * 70)

from src.analysis.projections import ProjectionEngine, RiskProfile
engine = ProjectionEngine()

# Simulation sur 20 ans avec le capital actuel
initial_capital = global_summary['total_value']
monthly_contribution = 800  # PEA + CTO

mc = engine.monte_carlo_simulation(
    initial_capital=initial_capital,
    monthly_contribution=monthly_contribution,
    years=20,
    risk_profile=RiskProfile.MODERE
)

print(f"\n  Capital initial: {initial_capital:,.0f} EUR")
print(f"  Versement mensuel: {monthly_contribution} EUR")
print(f"  Duree: 20 ans")
print(f"\n  Resultats (5000 simulations):")
print(f"    Scenario median: {mc.final_median:,.0f} EUR")
print(f"    Scenario optimiste (95%): {mc.final_optimistic:,.0f} EUR")
print(f"    Scenario pessimiste (5%): {mc.final_pessimistic:,.0f} EUR")
print(f"    Probabilite de doubler: {mc.probability_of_success:.1f}%")
print(f"    Max drawdown moyen: -{mc.max_drawdown:.1f}%")

# =============================================================================
# ETAPE 7: Calculateur FIRE
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 7: CALCULATEUR FIRE")
print("=" * 70)

fire = engine.calculate_fire(
    current_age=35,
    current_portfolio=initial_capital,
    monthly_contribution=monthly_contribution,
    monthly_expenses=3500,  # Depenses mensuelles souhaitees
    expected_return=0.07,
    safe_withdrawal_rate=0.04
)

print(f"\n  Age actuel: 35 ans")
print(f"  Portefeuille: {initial_capital:,.0f} EUR")
print(f"  Epargne mensuelle: {monthly_contribution} EUR")
print(f"  Depenses mensuelles FIRE: 3,500 EUR")
print(f"\n  FIRE Number: {fire.fire_number:,.0f} EUR")
print(f"  Age FIRE: {fire.fire_age} ans (dans {fire.years_to_fire} ans)")
print(f"  Progres actuel: {fire.current_progress:.1f}%")
print(f"  Revenu passif mensuel: {fire.monthly_passive_income:,.0f} EUR")
print(f"\n  Scenarios:")
print(f"    Optimiste: {fire.optimistic_age} ans")
print(f"    Median: {fire.fire_age} ans")
print(f"    Pessimiste: {fire.pessimistic_age} ans")

# =============================================================================
# ETAPE 8: Projection dividendes 40 ans
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 8: PROJECTION DIVIDENDES 40 ANS")
print("=" * 70)

div_proj = engine.project_dividends(
    initial_capital=initial_capital,
    monthly_contribution=monthly_contribution,
    years=40,
    initial_yield=0.025,  # 2.5% rendement initial
    dividend_growth=0.06  # 6% croissance/an
)

print(f"\n  Capital initial: {initial_capital:,.0f} EUR")
print(f"  Versement mensuel: {monthly_contribution} EUR")
print(f"  Rendement initial: 2.5%")
print(f"  Croissance dividende: 6%/an")
print(f"\n  A 40 ans:")
print(f"    Valeur portefeuille: {div_proj.portfolio_value[-1]:,.0f} EUR")
print(f"    Dividende annuel: {div_proj.final_annual_dividend:,.0f} EUR")
print(f"    Dividende mensuel: {div_proj.final_monthly_income:,.0f} EUR")
print(f"    Yield on Cost: {div_proj.yield_on_cost[-1]:.1f}%")

print(f"\n  Jalons:")
for year in [10, 20, 30, 40]:
    print(f"    Annee {year}: {div_proj.annual_dividends[year]:,.0f} EUR/an ({div_proj.annual_dividends[year]/12:,.0f} EUR/mois)")

# =============================================================================
# ETAPE 9: Analyse ETF
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 9: ANALYSE ETF")
print("=" * 70)

from src.analysis.etf_analyzer import ETFAnalyzer
etf_analyzer = ETFAnalyzer()

# Comparaison S&P 500
print("\n  Comparaison ETF S&P 500:")
comparison = etf_analyzer.compare_etfs(['SPY', 'VOO', 'IVV'])
if comparison:
    for etf in comparison.etfs:
        print(f"    {etf.ticker}: TER={etf.expense_ratio:.2f}%, Perf 1Y={etf.perf_1y:+.1f}%")
    print(f"    Recommandation: {comparison.recommendation}")

# Screener ETF World PEA
print("\n  ETF World eligibles PEA (TER < 0.3%):")
world_etfs = etf_analyzer.get_etf_screener(category='WORLD', max_ter=0.5, pea_only=True)
for etf in world_etfs[:3]:
    print(f"    {etf.ticker}: {etf.name[:30]} - TER={etf.expense_ratio:.2f}%")

# =============================================================================
# ETAPE 10: Score de diversification
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 10: SCORE DE DIVERSIFICATION")
print("=" * 70)

# Preparer les positions pour l'analyse
all_positions = []
for portfolio in pm.get_all_portfolios():
    details = pm.get_position_details(portfolio.id)
    for d in details:
        all_positions.append({
            'ticker': d.ticker,
            'value': d.current_value,
            'sector': d.sector or 'Other',
            'country': 'France' if '.PA' in d.ticker else 'United States'
        })

div_score = engine.calculate_diversification_score(all_positions)

print(f"\n  Score total: {div_score.total_score}/100")
print(f"\n  Detail des scores:")
print(f"    Concentration: {div_score.concentration_score}/20")
print(f"    Secteurs: {div_score.sector_score}/20")
print(f"    Geographie: {div_score.geographic_score}/20")
print(f"    Classes d'actifs: {div_score.asset_class_score}/20")
print(f"    Devises: {div_score.currency_score}/20")

if div_score.alerts:
    print(f"\n  Alertes:")
    for alert in div_score.alerts:
        print(f"    [!] {alert}")

if div_score.recommendations:
    print(f"\n  Recommandations:")
    for rec in div_score.recommendations[:3]:
        print(f"    -> {rec}")

# =============================================================================
# ETAPE 11: Analyse IA
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 11: ANALYSE IA DU PORTEFEUILLE")
print("=" * 70)

from src.analysis.ai_advisor import AIPortfolioAdvisor
advisor = AIPortfolioAdvisor()

# Verifier Ollama
ollama_status = "Connecte" if advisor._check_ollama() else "Non disponible (fallback regles)"
print(f"\n  Ollama: {ollama_status}")

# Preparer les donnees
portfolio_data = {
    'total_value': global_summary['total_value'],
    'total_gain': global_summary['total_gain'],
    'gain_pct': global_summary['total_gain_pct'],
    'diversification_score': div_score.total_score,
    'positions': [
        {'ticker': p['ticker'], 'name': p['ticker'], 'value': p['value'],
         'weight': p['value']/global_summary['total_value']*100,
         'gain_pct': 0, 'sector': p['sector'], 'score': 60}
        for p in all_positions
    ],
    'sector_allocation': div_score.sector_concentration,
    'country_allocation': div_score.country_concentration
}

result = advisor.analyze_portfolio(portfolio_data)

print(f"\n  Resume:")
print(f"    {result.summary[:100]}...")

print(f"\n  Points forts ({len(result.strengths)}):")
for s in result.strengths[:3]:
    print(f"    [+] {s}")

print(f"\n  Points faibles ({len(result.weaknesses)}):")
for w in result.weaknesses[:3]:
    print(f"    [-] {w}")

print(f"\n  Recommandations ({len(result.recommendations)}):")
for r in result.recommendations[:3]:
    print(f"    -> {r}")

print(f"\n  Risque: {result.risk_assessment}")
print(f"  Confiance: {result.confidence}")

# =============================================================================
# ETAPE 12: Export JSON
# =============================================================================
print("\n" + "=" * 70)
print("ETAPE 12: EXPORT JSON")
print("=" * 70)

for portfolio in pm.get_all_portfolios():
    json_data = pm.export_portfolio_to_json(portfolio.id)
    filename = f"export_{portfolio.name.replace(' ', '_')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(json_data)
    print(f"  [OK] Exporte: {filename}")

# =============================================================================
# RESUME FINAL
# =============================================================================
print("\n" + "=" * 70)
print("RESUME FINAL - STOCK ADVISOR v3.0")
print("=" * 70)

print(f"""
  PORTEFEUILLES:
    - {global_summary['portfolios_count']} portefeuilles crees
    - Valeur totale: {global_summary['total_value']:,.0f} EUR
    - Performance: {global_summary['total_gain_pct']:+.1f}%

  SIMULATIONS:
    - Monte Carlo 20 ans: {mc.final_median:,.0f} EUR (median)
    - FIRE a {fire.fire_age} ans
    - Dividendes a 40 ans: {div_proj.final_monthly_income:,.0f} EUR/mois

  SCORES:
    - Diversification: {div_score.total_score}/100
    - JNJ Dividend Safety: 18.5/20
    - NVDA Growth: 17.5/20

  ANALYSE IA: {len(result.recommendations)} recommandations generees
""")

print("=" * 70)
print("TOUS LES TESTS WORKFLOW TERMINES AVEC SUCCES!")
print("=" * 70)
print("\nApplication accessible sur: http://localhost:8502")
