"""
Projections et Simulations - Style Finary
- Simulation Monte Carlo (5000 runs)
- Projection patrimoine 30-40 ans
- Calculateur FIRE (Financial Independence)
- Projection dividendes long terme
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class RiskProfile(Enum):
    """Profil de risque."""
    CONSERVATEUR = "conservateur"
    MODERE = "modere"
    DYNAMIQUE = "dynamique"
    AGRESSIF = "agressif"


@dataclass
class MonteCarloResult:
    """Résultat de simulation Monte Carlo."""
    # Scénarios
    median_trajectory: List[float]  # 50e percentile
    optimistic_trajectory: List[float]  # 95e percentile
    pessimistic_trajectory: List[float]  # 5e percentile

    # Valeurs finales
    final_median: float
    final_optimistic: float
    final_pessimistic: float

    # Statistiques
    probability_of_success: float  # % de simulations atteignant l'objectif
    expected_return: float  # Rendement moyen annuel
    volatility: float  # Écart-type annuel
    max_drawdown: float  # Pire drawdown moyen

    # Métadonnées
    num_simulations: int
    years: int
    initial_capital: float
    monthly_contribution: float


@dataclass
class FIREResult:
    """Résultat du calculateur FIRE."""
    # Dates clés
    fire_age: int  # Âge d'indépendance financière
    years_to_fire: int
    fire_date: datetime

    # Montants
    fire_number: float  # Capital nécessaire
    current_progress: float  # % du chemin parcouru
    monthly_passive_income: float  # Revenu passif mensuel à FIRE

    # Scénarios
    optimistic_age: int
    pessimistic_age: int

    # Recommandations
    monthly_savings_needed: float  # Pour atteindre FIRE plus tôt
    analysis: List[str]


@dataclass
class DividendProjection:
    """Projection des dividendes."""
    years: List[int]
    annual_dividends: List[float]
    cumulative_dividends: List[float]
    portfolio_value: List[float]
    yield_on_cost: List[float]

    # À 40 ans
    final_annual_dividend: float
    final_monthly_income: float
    total_dividends_received: float


@dataclass
class DiversificationScore:
    """Score de diversification."""
    total_score: float  # 0-100

    # Composantes
    sector_score: float
    geographic_score: float
    asset_class_score: float
    currency_score: float
    concentration_score: float

    # Alertes
    alerts: List[str]
    recommendations: List[str]

    # Détails
    top_holding_weight: float
    sector_concentration: Dict[str, float]
    country_concentration: Dict[str, float]


class ProjectionEngine:
    """Moteur de projections et simulations."""

    # Paramètres par défaut selon profil de risque
    RISK_PARAMS = {
        RiskProfile.CONSERVATEUR: {'return': 0.04, 'volatility': 0.08},
        RiskProfile.MODERE: {'return': 0.06, 'volatility': 0.12},
        RiskProfile.DYNAMIQUE: {'return': 0.08, 'volatility': 0.18},
        RiskProfile.AGRESSIF: {'return': 0.10, 'volatility': 0.25},
    }

    def __init__(self):
        self.num_simulations = 5000

    def monte_carlo_simulation(
        self,
        initial_capital: float,
        monthly_contribution: float,
        years: int,
        expected_return: float = None,
        volatility: float = None,
        risk_profile: RiskProfile = RiskProfile.MODERE,
        target_value: float = None
    ) -> MonteCarloResult:
        """
        Exécute une simulation Monte Carlo.

        Args:
            initial_capital: Capital initial
            monthly_contribution: Versement mensuel
            years: Nombre d'années
            expected_return: Rendement annuel attendu (optionnel)
            volatility: Volatilité annuelle (optionnel)
            risk_profile: Profil de risque si return/vol non spécifiés
            target_value: Objectif à atteindre (pour calcul probabilité)
        """
        # Utiliser les paramètres du profil si non spécifiés
        if expected_return is None:
            expected_return = self.RISK_PARAMS[risk_profile]['return']
        if volatility is None:
            volatility = self.RISK_PARAMS[risk_profile]['volatility']

        # Convertir en mensuel
        monthly_return = expected_return / 12
        monthly_vol = volatility / np.sqrt(12)
        months = years * 12

        # Matrice de simulations [num_simulations x months]
        np.random.seed(42)  # Pour reproductibilité
        random_returns = np.random.normal(
            monthly_return,
            monthly_vol,
            (self.num_simulations, months)
        )

        # Simuler les trajectoires
        portfolios = np.zeros((self.num_simulations, months + 1))
        portfolios[:, 0] = initial_capital

        for month in range(months):
            # Croissance + contribution
            portfolios[:, month + 1] = (
                portfolios[:, month] * (1 + random_returns[:, month])
                + monthly_contribution
            )

        # Calculer les percentiles par mois
        median_trajectory = np.percentile(portfolios, 50, axis=0).tolist()
        optimistic_trajectory = np.percentile(portfolios, 95, axis=0).tolist()
        pessimistic_trajectory = np.percentile(portfolios, 5, axis=0).tolist()

        # Valeurs finales
        final_values = portfolios[:, -1]
        final_median = np.median(final_values)
        final_optimistic = np.percentile(final_values, 95)
        final_pessimistic = np.percentile(final_values, 5)

        # Probabilité de succès
        if target_value:
            probability_of_success = np.mean(final_values >= target_value) * 100
        else:
            # Par défaut: probabilité de doubler le capital investi
            total_invested = initial_capital + monthly_contribution * months
            probability_of_success = np.mean(final_values >= total_invested * 2) * 100

        # Calcul du max drawdown moyen
        drawdowns = []
        for sim in range(min(1000, self.num_simulations)):  # Échantillon pour perf
            running_max = np.maximum.accumulate(portfolios[sim])
            drawdown = (portfolios[sim] - running_max) / running_max
            drawdowns.append(np.min(drawdown))
        max_drawdown = abs(np.mean(drawdowns)) * 100

        return MonteCarloResult(
            median_trajectory=median_trajectory,
            optimistic_trajectory=optimistic_trajectory,
            pessimistic_trajectory=pessimistic_trajectory,
            final_median=final_median,
            final_optimistic=final_optimistic,
            final_pessimistic=final_pessimistic,
            probability_of_success=probability_of_success,
            expected_return=expected_return * 100,
            volatility=volatility * 100,
            max_drawdown=max_drawdown,
            num_simulations=self.num_simulations,
            years=years,
            initial_capital=initial_capital,
            monthly_contribution=monthly_contribution
        )

    def calculate_fire(
        self,
        current_age: int,
        current_portfolio: float,
        monthly_contribution: float,
        monthly_expenses: float,
        expected_return: float = 0.07,
        inflation: float = 0.02,
        safe_withdrawal_rate: float = 0.04
    ) -> FIREResult:
        """
        Calcule l'âge d'indépendance financière (FIRE).

        Args:
            current_age: Âge actuel
            current_portfolio: Valeur actuelle du portefeuille
            monthly_contribution: Épargne mensuelle
            monthly_expenses: Dépenses mensuelles souhaitées à la retraite
            expected_return: Rendement annuel attendu
            inflation: Taux d'inflation
            safe_withdrawal_rate: Taux de retrait sûr (règle des 4%)
        """
        # Calculer le FIRE number (capital nécessaire)
        annual_expenses = monthly_expenses * 12
        fire_number = annual_expenses / safe_withdrawal_rate

        # Rendement réel (net d'inflation)
        real_return = expected_return - inflation

        # Simulation année par année
        portfolio = current_portfolio
        annual_contribution = monthly_contribution * 12
        years = 0
        max_years = 60  # Limite à 60 ans de projection

        while portfolio < fire_number and years < max_years:
            portfolio = portfolio * (1 + real_return) + annual_contribution
            years += 1

        fire_age = current_age + years
        fire_date = datetime(datetime.now().year + years, 1, 1)

        # Calcul du progrès actuel
        current_progress = (current_portfolio / fire_number) * 100

        # Revenu passif mensuel à FIRE
        monthly_passive_income = (fire_number * safe_withdrawal_rate) / 12

        # Scénarios optimiste/pessimiste
        # Optimiste: +2% de rendement
        portfolio_opt = current_portfolio
        years_opt = 0
        while portfolio_opt < fire_number and years_opt < max_years:
            portfolio_opt = portfolio_opt * (1 + real_return + 0.02) + annual_contribution
            years_opt += 1
        optimistic_age = current_age + years_opt

        # Pessimiste: -2% de rendement
        portfolio_pess = current_portfolio
        years_pess = 0
        while portfolio_pess < fire_number and years_pess < max_years:
            portfolio_pess = portfolio_pess * (1 + real_return - 0.02) + annual_contribution
            years_pess += 1
        pessimistic_age = current_age + years_pess

        # Recommandations
        analysis = []

        if years <= 10:
            analysis.append(f"Excellent! FIRE atteignable dans {years} ans")
        elif years <= 20:
            analysis.append(f"Bon rythme, FIRE dans {years} ans")
        elif years <= 30:
            analysis.append(f"Objectif long terme ({years} ans)")
        else:
            analysis.append("Considérez d'augmenter votre taux d'épargne")

        # Épargne nécessaire pour atteindre FIRE 5 ans plus tôt
        target_years = max(years - 5, 1)
        # Formule du versement pour valeur future
        if real_return > 0:
            fv_factor = ((1 + real_return) ** target_years - 1) / real_return
            pv_factor = (1 + real_return) ** target_years
            needed_annual = (fire_number - current_portfolio * pv_factor) / fv_factor
            monthly_savings_needed = max(needed_annual / 12, 0)
        else:
            monthly_savings_needed = (fire_number - current_portfolio) / (target_years * 12)

        if monthly_savings_needed > monthly_contribution:
            diff = monthly_savings_needed - monthly_contribution
            analysis.append(f"Pour FIRE 5 ans plus tôt: +{diff:.0f}€/mois d'épargne")

        return FIREResult(
            fire_age=fire_age,
            years_to_fire=years,
            fire_date=fire_date,
            fire_number=fire_number,
            current_progress=current_progress,
            monthly_passive_income=monthly_passive_income,
            optimistic_age=optimistic_age,
            pessimistic_age=pessimistic_age,
            monthly_savings_needed=monthly_savings_needed,
            analysis=analysis
        )

    def project_dividends(
        self,
        initial_capital: float,
        monthly_contribution: float,
        years: int = 40,
        initial_yield: float = 0.03,  # 3%
        dividend_growth: float = 0.05,  # 5% par an
        price_appreciation: float = 0.05  # 5% par an
    ) -> DividendProjection:
        """
        Projette les dividendes sur le long terme (style Moning).

        Args:
            initial_capital: Capital initial
            monthly_contribution: Versement mensuel
            years: Nombre d'années (défaut 40)
            initial_yield: Rendement dividende initial
            dividend_growth: Croissance annuelle du dividende
            price_appreciation: Appréciation annuelle du cours
        """
        years_list = list(range(years + 1))
        annual_dividends = []
        cumulative_dividends = []
        portfolio_values = []
        yield_on_cost = []

        portfolio = initial_capital
        total_cost = initial_capital
        total_dividends = 0
        current_yield = initial_yield

        for year in range(years + 1):
            # Dividende de l'année
            annual_div = portfolio * current_yield
            annual_dividends.append(annual_div)

            total_dividends += annual_div
            cumulative_dividends.append(total_dividends)

            portfolio_values.append(portfolio)

            # Yield on cost (rendement sur coût d'acquisition)
            yoc = (annual_div / total_cost * 100) if total_cost > 0 else 0
            yield_on_cost.append(yoc)

            # Évolution pour l'année suivante
            if year < years:
                # Réinvestissement des dividendes + contribution
                annual_contribution = monthly_contribution * 12
                portfolio = portfolio * (1 + price_appreciation) + annual_div + annual_contribution
                total_cost += annual_contribution

                # Croissance du dividende
                current_yield = initial_yield * ((1 + dividend_growth) ** (year + 1))
                # Ajuster pour l'appréciation du cours
                current_yield = current_yield / ((1 + price_appreciation) ** (year + 1))
                current_yield = max(current_yield, initial_yield * 0.5)  # Plancher

        return DividendProjection(
            years=years_list,
            annual_dividends=annual_dividends,
            cumulative_dividends=cumulative_dividends,
            portfolio_value=portfolio_values,
            yield_on_cost=yield_on_cost,
            final_annual_dividend=annual_dividends[-1],
            final_monthly_income=annual_dividends[-1] / 12,
            total_dividends_received=total_dividends
        )

    def calculate_diversification_score(
        self,
        positions: List[Dict]  # [{'ticker': str, 'value': float, 'sector': str, 'country': str}]
    ) -> DiversificationScore:
        """
        Calcule le score de diversification du portefeuille.
        """
        if not positions:
            return DiversificationScore(
                total_score=0,
                sector_score=0,
                geographic_score=0,
                asset_class_score=0,
                currency_score=0,
                concentration_score=0,
                alerts=["Portefeuille vide"],
                recommendations=["Ajoutez des positions"],
                top_holding_weight=0,
                sector_concentration={},
                country_concentration={}
            )

        total_value = sum(p.get('value', 0) for p in positions)
        if total_value == 0:
            total_value = 1

        alerts = []
        recommendations = []

        # 1. CONCENTRATION (0-20 points)
        weights = sorted([p.get('value', 0) / total_value for p in positions], reverse=True)
        top_holding_weight = weights[0] * 100 if weights else 0

        # Herfindahl Index
        hhi = sum(w ** 2 for w in weights)

        if hhi < 0.05:  # Très diversifié
            concentration_score = 20
        elif hhi < 0.10:
            concentration_score = 16
        elif hhi < 0.15:
            concentration_score = 12
        elif hhi < 0.25:
            concentration_score = 8
            alerts.append(f"Position principale: {top_holding_weight:.0f}% du portefeuille")
        else:
            concentration_score = 4
            alerts.append(f"Concentration excessive: {top_holding_weight:.0f}%")
            recommendations.append("Diversifiez vos positions (max 10% par titre)")

        # 2. SECTEURS (0-20 points)
        sector_values = {}
        for p in positions:
            sector = p.get('sector', 'Autre') or 'Autre'
            sector_values[sector] = sector_values.get(sector, 0) + p.get('value', 0)

        sector_concentration = {s: v / total_value * 100 for s, v in sector_values.items()}
        num_sectors = len([s for s, v in sector_concentration.items() if v > 2])

        if num_sectors >= 8:
            sector_score = 20
        elif num_sectors >= 6:
            sector_score = 16
        elif num_sectors >= 4:
            sector_score = 12
        elif num_sectors >= 2:
            sector_score = 8
            recommendations.append("Diversifiez dans plus de secteurs")
        else:
            sector_score = 4
            alerts.append("Concentration sectorielle élevée")

        # Alerte si un secteur > 40%
        for sector, pct in sector_concentration.items():
            if pct > 40:
                alerts.append(f"Secteur {sector}: {pct:.0f}% (>40%)")

        # 3. GÉOGRAPHIE (0-20 points)
        country_values = {}
        for p in positions:
            country = p.get('country', 'Autre') or 'Autre'
            country_values[country] = country_values.get(country, 0) + p.get('value', 0)

        country_concentration = {c: v / total_value * 100 for c, v in country_values.items()}
        num_countries = len([c for c, v in country_concentration.items() if v > 2])

        if num_countries >= 6:
            geographic_score = 20
        elif num_countries >= 4:
            geographic_score = 16
        elif num_countries >= 2:
            geographic_score = 12
        elif num_countries >= 1:
            geographic_score = 8
            recommendations.append("Diversifiez géographiquement")
        else:
            geographic_score = 4

        # 4. CLASSES D'ACTIFS (0-20 points) - Simplifié car on n'a que des actions
        # On donne un score moyen, l'utilisateur devrait aussi avoir des obligations, immo, etc.
        asset_class_score = 10
        recommendations.append("Considérez d'autres classes d'actifs (obligations, immobilier)")

        # 5. DEVISES (0-20 points)
        # Approximation basée sur les pays
        currency_zones = {
            'United States': 'USD',
            'France': 'EUR', 'Germany': 'EUR', 'Netherlands': 'EUR', 'Italy': 'EUR',
            'United Kingdom': 'GBP',
            'Japan': 'JPY',
            'China': 'CNY',
            'Switzerland': 'CHF'
        }

        currency_exposure = {}
        for p in positions:
            country = p.get('country', 'Autre')
            currency = currency_zones.get(country, 'EUR')
            currency_exposure[currency] = currency_exposure.get(currency, 0) + p.get('value', 0)

        num_currencies = len([c for c, v in currency_exposure.items() if v / total_value > 0.05])

        if num_currencies >= 4:
            currency_score = 20
        elif num_currencies >= 3:
            currency_score = 16
        elif num_currencies >= 2:
            currency_score = 12
        else:
            currency_score = 8
            recommendations.append("Exposez-vous à d'autres devises (USD, CHF)")

        # SCORE TOTAL
        total_score = (
            concentration_score +
            sector_score +
            geographic_score +
            asset_class_score +
            currency_score
        )

        return DiversificationScore(
            total_score=total_score,
            sector_score=sector_score,
            geographic_score=geographic_score,
            asset_class_score=asset_class_score,
            currency_score=currency_score,
            concentration_score=concentration_score,
            alerts=alerts,
            recommendations=recommendations,
            top_holding_weight=top_holding_weight,
            sector_concentration=sector_concentration,
            country_concentration=country_concentration
        )


def get_projection_engine() -> ProjectionEngine:
    """Factory function."""
    return ProjectionEngine()


if __name__ == "__main__":
    engine = ProjectionEngine()

    print("=" * 70)
    print("TEST SIMULATION MONTE CARLO")
    print("=" * 70)

    result = engine.monte_carlo_simulation(
        initial_capital=10000,
        monthly_contribution=500,
        years=20,
        risk_profile=RiskProfile.MODERE
    )

    print(f"\nCapital initial: {result.initial_capital:,.0f}€")
    print(f"Versement mensuel: {result.monthly_contribution:,.0f}€")
    print(f"Durée: {result.years} ans")
    print(f"Rendement attendu: {result.expected_return:.1f}%")
    print(f"Volatilité: {result.volatility:.1f}%")
    print(f"\nRésultats après {result.years} ans:")
    print(f"  Scénario médian: {result.final_median:,.0f}€")
    print(f"  Scénario optimiste (95%): {result.final_optimistic:,.0f}€")
    print(f"  Scénario pessimiste (5%): {result.final_pessimistic:,.0f}€")
    print(f"\nProbabilité de succès: {result.probability_of_success:.1f}%")
    print(f"Max drawdown moyen: -{result.max_drawdown:.1f}%")

    print("\n" + "=" * 70)
    print("TEST CALCULATEUR FIRE")
    print("=" * 70)

    fire = engine.calculate_fire(
        current_age=30,
        current_portfolio=50000,
        monthly_contribution=1000,
        monthly_expenses=3000
    )

    print(f"\nÂge actuel: 30 ans")
    print(f"Portefeuille: 50,000€")
    print(f"Épargne mensuelle: 1,000€")
    print(f"Dépenses mensuelles FIRE: 3,000€")
    print(f"\nFIRE Number: {fire.fire_number:,.0f}€")
    print(f"Progrès actuel: {fire.current_progress:.1f}%")
    print(f"\nÂge FIRE: {fire.fire_age} ans (dans {fire.years_to_fire} ans)")
    print(f"  Optimiste: {fire.optimistic_age} ans")
    print(f"  Pessimiste: {fire.pessimistic_age} ans")
    print(f"\nRevenu passif mensuel: {fire.monthly_passive_income:,.0f}€")
    for a in fire.analysis:
        print(f"  → {a}")

    print("\n" + "=" * 70)
    print("TEST PROJECTION DIVIDENDES 40 ANS")
    print("=" * 70)

    div_proj = engine.project_dividends(
        initial_capital=10000,
        monthly_contribution=200,
        years=40,
        initial_yield=0.03
    )

    print(f"\nCapital initial: 10,000€")
    print(f"Versement mensuel: 200€")
    print(f"Rendement initial: 3%")
    print(f"\nÀ 40 ans:")
    print(f"  Valeur portefeuille: {div_proj.portfolio_value[-1]:,.0f}€")
    print(f"  Dividende annuel: {div_proj.final_annual_dividend:,.0f}€")
    print(f"  Dividende mensuel: {div_proj.final_monthly_income:,.0f}€")
    print(f"  Total dividendes reçus: {div_proj.total_dividends_received:,.0f}€")
    print(f"  Yield on Cost: {div_proj.yield_on_cost[-1]:.1f}%")

    # Quelques jalons
    for year in [5, 10, 20, 30, 40]:
        print(f"  Année {year}: {div_proj.annual_dividends[year]:,.0f}€/an")
