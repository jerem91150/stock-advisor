"""
Script de test complet pour Stock Advisor v3.0
"""
import sys
sys.path.insert(0, '.')

print('='*70)
print('TEST COMPLET STOCK ADVISOR v3.0')
print('='*70)

# Test 1: Portfolio Manager
print('\n[1/7] TEST PORTFOLIO MANAGER')
try:
    from src.portfolio.manager import PortfolioManager
    pm = PortfolioManager()

    # Creer un portefeuille de test
    pf = pm.create_portfolio('Test PEA', 'PEA', broker='Boursorama', currency='EUR')
    print(f'  OK Portefeuille cree: {pf.name} (ID: {pf.id})')

    # Ajouter des positions
    pos1, tx1 = pm.add_position(pf.id, 'AAPL', 10, 150.0, fees=5.0)
    pos2, tx2 = pm.add_position(pf.id, 'MSFT', 5, 350.0, fees=5.0)
    pos3, tx3 = pm.add_position(pf.id, 'MC.PA', 3, 800.0, fees=2.0)
    print(f'  OK 3 positions ajoutees: AAPL, MSFT, MC.PA')

    # Summary
    summary = pm.get_portfolio_summary(pf.id)
    print(f'  OK Valeur totale: {summary.current_value:,.2f} EUR')
    print(f'  OK Performance: {summary.total_gain_pct:+.1f}%')

    # Allocations
    sectors = pm.get_allocation_by_sector(pf.id)
    print(f'  OK Secteurs: {list(sectors.keys())[:3]}')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 2: Dividend Tracker
print('\n[2/7] TEST DIVIDEND TRACKER')
try:
    from src.portfolio.dividend_tracker import DividendTracker
    dt = DividendTracker()

    # Test dividend info
    info = dt.get_dividend_info('AAPL')
    if info:
        print(f'  OK AAPL: {info.dividend_yield:.2f}% yield, {info.amount:.2f}$/action')
    else:
        print('  OK AAPL: Pas de dividende ou erreur API')

    # Test upcoming dividends
    positions = [{'ticker': 'AAPL', 'quantity': 10, 'name': 'Apple'}]
    upcoming = dt.get_upcoming_dividends(positions, days_ahead=90)
    print(f'  OK Dividendes a venir (90j): {len(upcoming)} trouves')

    # Test annual estimate
    estimate = dt.get_annual_dividend_estimate(positions)
    print(f'  OK Estimation annuelle: {estimate["total_annual"]:.2f} EUR')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 3: Moning Scores
print('\n[3/7] TEST MONING SCORES')
try:
    from src.analysis.moning_scores import MoningStyleScorer
    scorer = MoningStyleScorer()

    # Test Dividend Safety Score
    div_score = scorer.calculate_dividend_safety_score('JNJ')
    if div_score:
        print(f'  OK JNJ Dividend Safety: {div_score.total_score:.1f}/20 ({div_score.rating})')
    else:
        print('  OK JNJ: Score non disponible')

    # Test Growth Score
    growth_score = scorer.calculate_growth_score('NVDA')
    if growth_score:
        print(f'  OK NVDA Growth Score: {growth_score.total_score:.1f}/20 ({growth_score.rating})')
    else:
        print('  OK NVDA: Score non disponible')

    # Test Valuation
    valuation = scorer.calculate_valuation_indicator('AAPL')
    if valuation:
        print(f'  OK AAPL Valuation: {valuation.status} (Fair Value: {valuation.fair_value:.2f})')
    else:
        print('  OK AAPL: Valuation non disponible')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 4: Projections Engine
print('\n[4/7] TEST PROJECTIONS ENGINE')
try:
    from src.analysis.projections import ProjectionEngine, RiskProfile
    engine = ProjectionEngine()

    # Test Monte Carlo
    mc = engine.monte_carlo_simulation(
        initial_capital=10000,
        monthly_contribution=500,
        years=20,
        risk_profile=RiskProfile.MODERE
    )
    print(f'  OK Monte Carlo: Median={mc.final_median:,.0f} EUR, Pessimiste={mc.final_pessimistic:,.0f} EUR')
    print(f'  OK Probabilite de succes: {mc.probability_of_success:.1f}%')

    # Test FIRE
    fire = engine.calculate_fire(30, 50000, 1000, 3000, 0.07, 0.04)
    print(f'  OK FIRE: Age={fire.fire_age} ans, Number={fire.fire_number:,.0f} EUR')
    print(f'  OK Progres actuel: {fire.current_progress:.1f}%')

    # Test Dividend Projection
    div_proj = engine.project_dividends(10000, 200, 40, 0.03, 0.05)
    print(f'  OK Projection 40 ans: {div_proj.final_annual_dividend:,.0f} EUR/an')

    # Test Diversification Score
    positions = [
        {'ticker': 'AAPL', 'value': 5000, 'sector': 'Technology', 'country': 'US'},
        {'ticker': 'JNJ', 'value': 3000, 'sector': 'Healthcare', 'country': 'US'},
        {'ticker': 'MC.PA', 'value': 2000, 'sector': 'Luxury', 'country': 'France'}
    ]
    div_score = engine.calculate_diversification_score(positions)
    print(f'  OK Score Diversification: {div_score.total_score:.0f}/100')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 5: ETF Analyzer
print('\n[5/7] TEST ETF ANALYZER')
try:
    from src.analysis.etf_analyzer import ETFAnalyzer
    analyzer = ETFAnalyzer()

    # Test ETF info
    etf = analyzer.get_etf_info('SPY')
    if etf:
        print(f'  OK SPY: TER={etf.expense_ratio:.2f}%, Perf 1Y={etf.perf_1y:+.1f}%')
    else:
        print('  OK SPY: Info non disponible')

    # Test comparison
    comparison = analyzer.compare_etfs(['SPY', 'VOO', 'IVV'])
    if comparison:
        print(f'  OK Comparaison: {len(comparison.etfs)} ETFs compares')
        print(f'  OK Recommandation: {comparison.recommendation}')
    else:
        print('  OK Comparaison non disponible')

    # Test screener
    screener = analyzer.get_etf_screener(category='SP500', max_ter=0.5)
    print(f'  OK Screener S&P500: {len(screener)} ETFs trouves')

    # Test fee analysis
    positions = [{'ticker': 'SPY', 'value': 10000}]
    fees = analyzer.analyze_portfolio_fees(positions)
    print(f'  OK Frais annuels estimes: {fees.annual_fees:.0f} EUR')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 6: AI Advisor
print('\n[6/7] TEST AI ADVISOR')
try:
    from src.analysis.ai_advisor import AIPortfolioAdvisor
    advisor = AIPortfolioAdvisor()

    # Check Ollama
    ollama_available = advisor._check_ollama()
    print(f'  OK Ollama disponible: {ollama_available}')

    # Test portfolio analysis (rule-based fallback)
    portfolio_data = {
        'total_value': 25000,
        'total_gain': 3500,
        'gain_pct': 14.0,
        'diversification_score': 65,
        'positions': [
            {'ticker': 'AAPL', 'name': 'Apple', 'value': 5000, 'weight': 20, 'gain_pct': 25, 'sector': 'Technology', 'score': 75},
            {'ticker': 'MSFT', 'name': 'Microsoft', 'value': 4000, 'weight': 16, 'gain_pct': 30, 'sector': 'Technology', 'score': 80},
        ],
        'sector_allocation': {'Technology': 36, 'Healthcare': 12},
        'country_allocation': {'United States': 58, 'France': 14}
    }

    result = advisor.analyze_portfolio(portfolio_data)
    print(f'  OK Analyse generee')
    print(f'  OK Points forts: {len(result.strengths)}, Points faibles: {len(result.weaknesses)}')
    print(f'  OK Recommandations: {len(result.recommendations)}')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

# Test 7: Full Scoring
print('\n[7/7] TEST SCORING COMPLET (yfinance)')
try:
    import yfinance as yf

    tickers = ['AAPL', 'NVDA', 'MC.PA']
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        pe = info.get('trailingPE', 'N/A')
        roe = info.get('returnOnEquity', 0)
        roe_pct = roe * 100 if roe else 0
        print(f'  OK {ticker}: Prix={price:.2f}, P/E={pe}, ROE={roe_pct:.1f}%')

    print('  STATUS: OK')
except Exception as e:
    print(f'  STATUS: ERREUR - {e}')

print('\n' + '='*70)
print('TOUS LES TESTS TERMINES')
print('='*70)
