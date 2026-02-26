"""
Module d'Estimation de Prix - Analyse si le prix actuel est un bon prix d'achat

Combine plusieurs méthodes de valorisation :
1. Analyse des multiples (P/E, EV/EBITDA comparés au secteur et historique)
2. Modèle DCF simplifié (Discounted Cash Flow)
3. Modèle de Gordon (Dividend Discount Model) pour actions à dividendes
4. Analyse technique des niveaux de prix (supports, moyennes mobiles)
5. Comparaison au prix cible des analystes
6. Position dans le range 52 semaines
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import pandas as pd
import numpy as np
from loguru import logger


class PriceSignal(Enum):
    """Signal de prix d'achat."""
    STRONG_BUY = "strong_buy"      # Prix très attractif
    BUY = "buy"                     # Bon prix d'achat
    HOLD = "hold"                   # Prix correct, attendre
    OVERVALUED = "overvalued"       # Prix trop élevé
    AVOID = "avoid"                 # Éviter


@dataclass
class PriceLevel:
    """Niveau de prix identifié."""
    price: float
    level_type: str  # "support", "resistance", "ma50", "ma200", "target"
    strength: str    # "strong", "moderate", "weak"
    description: str


@dataclass
class ValuationMethod:
    """Résultat d'une méthode de valorisation."""
    method_name: str
    fair_value: Optional[float]
    current_price: float
    upside_percent: Optional[float]
    confidence: str  # "high", "medium", "low"
    description: str


@dataclass
class PriceAnalysis:
    """Analyse complète du prix d'achat."""
    ticker: str
    current_price: float
    currency: str

    # Signal global
    signal: PriceSignal
    signal_strength: int  # 1-5

    # Estimation de la juste valeur
    fair_value_low: Optional[float]
    fair_value_mid: Optional[float]
    fair_value_high: Optional[float]

    # Potentiel
    upside_percent: Optional[float]
    downside_risk_percent: Optional[float]

    # Méthodes de valorisation utilisées
    valuation_methods: list[ValuationMethod] = field(default_factory=list)

    # Niveaux de prix clés
    price_levels: list[PriceLevel] = field(default_factory=list)

    # Prix d'achat recommandés
    ideal_buy_price: Optional[float] = None
    max_buy_price: Optional[float] = None

    # Contexte
    position_52w: float = 0  # 0-100, position dans le range 52 semaines
    distance_from_ma200: float = 0  # % au-dessus/dessous MA200
    analyst_target: Optional[float] = None
    analyst_recommendation: Optional[str] = None

    # Résumé
    summary: str = ""
    reasons: list[str] = field(default_factory=list)


class PriceEstimator:
    """Estimateur de prix d'achat optimal."""

    # Multiples moyens par secteur (données de référence)
    SECTOR_MULTIPLES = {
        "Technology": {"pe": 28, "ev_ebitda": 18, "pb": 6},
        "Healthcare": {"pe": 22, "ev_ebitda": 14, "pb": 4},
        "Financial Services": {"pe": 12, "ev_ebitda": 8, "pb": 1.2},
        "Consumer Cyclical": {"pe": 20, "ev_ebitda": 12, "pb": 4},
        "Consumer Defensive": {"pe": 22, "ev_ebitda": 14, "pb": 5},
        "Industrials": {"pe": 20, "ev_ebitda": 12, "pb": 3},
        "Energy": {"pe": 10, "ev_ebitda": 5, "pb": 1.5},
        "Basic Materials": {"pe": 15, "ev_ebitda": 8, "pb": 2},
        "Utilities": {"pe": 18, "ev_ebitda": 10, "pb": 1.8},
        "Real Estate": {"pe": 35, "ev_ebitda": 18, "pb": 1.5},
        "Communication Services": {"pe": 18, "ev_ebitda": 10, "pb": 3},
    }

    # Taux sans risque et prime de risque pour DCF
    RISK_FREE_RATE = 0.03  # 3%
    EQUITY_RISK_PREMIUM = 0.05  # 5%
    TERMINAL_GROWTH_RATE = 0.02  # 2%

    def __init__(self):
        self.methods_used = []

    def analyze_price(
        self,
        ticker: str,
        current_price: float,
        currency: str,
        fundamentals: dict,
        price_history: Optional[pd.DataFrame],
        sector: Optional[str] = None,
        analyst_target: Optional[float] = None,
        analyst_recommendation: Optional[str] = None
    ) -> PriceAnalysis:
        """
        Analyse complète pour déterminer si c'est un bon prix d'achat.

        Args:
            ticker: Symbole de l'action
            current_price: Prix actuel
            currency: Devise
            fundamentals: Dict avec EPS, FCF, dividendes, etc.
            price_history: DataFrame avec historique OHLCV
            sector: Secteur d'activité
            analyst_target: Prix cible des analystes
            analyst_recommendation: Recommandation consensus

        Returns:
            PriceAnalysis avec signal et niveaux de prix
        """
        valuation_methods = []
        price_levels = []
        fair_values = []

        # 1. Valorisation par les multiples
        multiple_valuation = self._valuation_by_multiples(
            current_price, fundamentals, sector
        )
        if multiple_valuation:
            valuation_methods.append(multiple_valuation)
            if multiple_valuation.fair_value:
                fair_values.append(multiple_valuation.fair_value)

        # 2. Modèle DCF simplifié
        dcf_valuation = self._dcf_valuation(current_price, fundamentals)
        if dcf_valuation:
            valuation_methods.append(dcf_valuation)
            if dcf_valuation.fair_value:
                fair_values.append(dcf_valuation.fair_value)

        # 3. Modèle de Gordon (dividendes)
        gordon_valuation = self._gordon_model(current_price, fundamentals)
        if gordon_valuation:
            valuation_methods.append(gordon_valuation)
            if gordon_valuation.fair_value:
                fair_values.append(gordon_valuation.fair_value)

        # 4. Comparaison au prix cible analystes
        if analyst_target:
            analyst_valuation = ValuationMethod(
                method_name="Prix cible analystes",
                fair_value=analyst_target,
                current_price=current_price,
                upside_percent=((analyst_target - current_price) / current_price) * 100,
                confidence="medium",
                description=f"Consensus analystes: {analyst_target:.2f} {currency}"
            )
            valuation_methods.append(analyst_valuation)
            fair_values.append(analyst_target)

        # 5. Analyse technique des niveaux
        tech_levels = []
        position_52w = 50
        distance_ma200 = 0

        if price_history is not None and len(price_history) >= 50:
            tech_levels, position_52w, distance_ma200 = self._analyze_technical_levels(
                current_price, price_history
            )
            price_levels.extend(tech_levels)

        # Calculer la juste valeur (moyenne pondérée)
        fair_value_mid = None
        fair_value_low = None
        fair_value_high = None

        if fair_values:
            fair_value_mid = np.median(fair_values)
            fair_value_low = min(fair_values)
            fair_value_high = max(fair_values)

        # Calculer le potentiel
        upside_percent = None
        downside_risk = None

        if fair_value_mid:
            upside_percent = ((fair_value_mid - current_price) / current_price) * 100
            if fair_value_low:
                downside_risk = ((current_price - fair_value_low) / current_price) * 100

        # Déterminer le signal d'achat
        signal, signal_strength, reasons = self._determine_signal(
            current_price, fair_value_mid, fair_value_low,
            upside_percent, position_52w, distance_ma200,
            valuation_methods
        )

        # Calculer les prix d'achat recommandés
        ideal_buy_price, max_buy_price = self._calculate_buy_prices(
            current_price, fair_value_mid, fair_value_low, price_levels
        )

        # Générer le résumé
        summary = self._generate_summary(
            signal, current_price, fair_value_mid, upside_percent,
            ideal_buy_price, currency
        )

        return PriceAnalysis(
            ticker=ticker,
            current_price=current_price,
            currency=currency,
            signal=signal,
            signal_strength=signal_strength,
            fair_value_low=fair_value_low,
            fair_value_mid=fair_value_mid,
            fair_value_high=fair_value_high,
            upside_percent=upside_percent,
            downside_risk_percent=downside_risk,
            valuation_methods=valuation_methods,
            price_levels=price_levels,
            ideal_buy_price=ideal_buy_price,
            max_buy_price=max_buy_price,
            position_52w=position_52w,
            distance_from_ma200=distance_ma200,
            analyst_target=analyst_target,
            analyst_recommendation=analyst_recommendation,
            summary=summary,
            reasons=reasons
        )

    def _valuation_by_multiples(
        self,
        current_price: float,
        fundamentals: dict,
        sector: Optional[str]
    ) -> Optional[ValuationMethod]:
        """Valorisation par comparaison des multiples au secteur."""
        eps = fundamentals.get("eps")
        pe_ratio = fundamentals.get("pe_ratio")

        if not eps or eps <= 0:
            return None

        # Obtenir le P/E moyen du secteur
        sector_multiples = self.SECTOR_MULTIPLES.get(sector, {"pe": 18})
        sector_pe = sector_multiples.get("pe", 18)

        # Calculer la juste valeur basée sur le P/E du secteur
        fair_value = eps * sector_pe

        # Ajuster si le P/E actuel est très différent
        if pe_ratio and pe_ratio > 0:
            # Si P/E actuel < P/E secteur, l'action pourrait être sous-évaluée
            pe_discount = (sector_pe - pe_ratio) / sector_pe * 100
        else:
            pe_discount = 0

        upside = ((fair_value - current_price) / current_price) * 100

        # Confiance basée sur la disponibilité des données
        confidence = "high" if pe_ratio and sector else "medium"

        description = f"P/E actuel: {pe_ratio:.1f} vs secteur: {sector_pe}"
        if pe_ratio and pe_ratio < sector_pe:
            description += f" (decote de {abs(pe_discount):.0f}%)"
        elif pe_ratio and pe_ratio > sector_pe:
            description += f" (prime de {abs(pe_discount):.0f}%)"

        return ValuationMethod(
            method_name="Multiples (P/E secteur)",
            fair_value=fair_value,
            current_price=current_price,
            upside_percent=upside,
            confidence=confidence,
            description=description
        )

    def _dcf_valuation(
        self,
        current_price: float,
        fundamentals: dict
    ) -> Optional[ValuationMethod]:
        """
        Valorisation DCF simplifiée basée sur le FCF Yield.

        Approche simplifiée: FCF Yield = FCF / Market Cap
        Si FCF Yield > 5%, l'action est potentiellement sous-évaluée
        """
        fcf = fundamentals.get("free_cash_flow")  # En millions
        market_cap = fundamentals.get("market_cap")  # En millions

        if not fcf or not market_cap or market_cap <= 0:
            return None

        # FCF Yield
        fcf_yield = (fcf / market_cap) * 100

        # Un bon FCF Yield est généralement > 5%
        # On utilise l'inverse pour estimer une juste valeur
        target_fcf_yield = 5.0  # 5% cible

        if fcf_yield <= 0:
            return None

        # Juste valeur basée sur le FCF Yield cible
        # Si FCF = 100M et on veut 5% yield, market cap devrait être 2000M
        implied_market_cap = fcf / (target_fcf_yield / 100)

        # Convertir en prix par action
        fair_value = current_price * (implied_market_cap / market_cap)

        # Appliquer marge de sécurité de 15%
        fair_value = fair_value * 0.85

        upside = ((fair_value - current_price) / current_price) * 100

        return ValuationMethod(
            method_name="FCF Yield",
            fair_value=fair_value,
            current_price=current_price,
            upside_percent=upside,
            confidence="medium",
            description=f"FCF Yield actuel: {fcf_yield:.1f}% (cible: {target_fcf_yield}%)"
        )

    def _gordon_model(
        self,
        current_price: float,
        fundamentals: dict
    ) -> Optional[ValuationMethod]:
        """
        Modèle de Gordon (Dividend Discount Model).

        Formule: P = D1 / (r - g)
        où D1 = dividende attendu, r = rendement requis, g = croissance dividende
        """
        dividend_yield = fundamentals.get("dividend_yield")
        dividend_growth = fundamentals.get("earnings_growth", 0.03)  # Proxy

        if not dividend_yield or dividend_yield <= 0:
            return None

        # Dividende actuel par action
        dividend_per_share = current_price * dividend_yield

        # Croissance du dividende (plafonner)
        if dividend_growth is None:
            dividend_growth = 0.03
        growth = min(max(dividend_growth, 0), 0.08)  # 0% à 8%

        # Rendement requis
        required_return = self.RISK_FREE_RATE + self.EQUITY_RISK_PREMIUM

        # S'assurer que r > g
        if required_return <= growth:
            growth = required_return - 0.01

        # Dividende attendu l'année prochaine
        d1 = dividend_per_share * (1 + growth)

        # Valeur selon Gordon
        fair_value = d1 / (required_return - growth)

        upside = ((fair_value - current_price) / current_price) * 100

        return ValuationMethod(
            method_name="Gordon (Dividendes)",
            fair_value=fair_value,
            current_price=current_price,
            upside_percent=upside,
            confidence="medium" if dividend_yield > 0.02 else "low",
            description=f"Dividende: {dividend_per_share:.2f}, croissance: {growth*100:.0f}%"
        )

    def _analyze_technical_levels(
        self,
        current_price: float,
        df: pd.DataFrame
    ) -> tuple[list[PriceLevel], float, float]:
        """
        Analyse les niveaux techniques clés.

        Returns:
            (price_levels, position_52w, distance_ma200)
        """
        levels = []

        close = df['Close']
        high = df['High']
        low = df['Low']

        # Moyennes mobiles
        ma50 = close.rolling(50).mean().iloc[-1]
        ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        if not pd.isna(ma50):
            distance_ma50 = ((current_price - ma50) / ma50) * 100
            strength = "strong" if abs(distance_ma50) < 3 else "moderate"
            levels.append(PriceLevel(
                price=ma50,
                level_type="ma50",
                strength=strength,
                description=f"MM50: {ma50:.2f} ({distance_ma50:+.1f}%)"
            ))

        distance_ma200 = 0
        if ma200 and not pd.isna(ma200):
            distance_ma200 = ((current_price - ma200) / ma200) * 100
            strength = "strong"
            levels.append(PriceLevel(
                price=ma200,
                level_type="ma200",
                strength=strength,
                description=f"MM200: {ma200:.2f} ({distance_ma200:+.1f}%)"
            ))

        # Range 52 semaines
        high_52w = high.tail(252).max()
        low_52w = low.tail(252).min()

        position_52w = ((current_price - low_52w) / (high_52w - low_52w)) * 100 \
                       if high_52w != low_52w else 50

        levels.append(PriceLevel(
            price=high_52w,
            level_type="resistance",
            strength="strong",
            description=f"Plus haut 52 sem: {high_52w:.2f}"
        ))

        levels.append(PriceLevel(
            price=low_52w,
            level_type="support",
            strength="strong",
            description=f"Plus bas 52 sem: {low_52w:.2f}"
        ))

        # Supports/Résistances basés sur les pivots récents
        recent_highs = high.tail(60)
        recent_lows = low.tail(60)

        # Support récent
        support_level = recent_lows.quantile(0.1)
        if support_level < current_price:
            levels.append(PriceLevel(
                price=support_level,
                level_type="support",
                strength="moderate",
                description=f"Support recent: {support_level:.2f}"
            ))

        # Résistance récente
        resistance_level = recent_highs.quantile(0.9)
        if resistance_level > current_price:
            levels.append(PriceLevel(
                price=resistance_level,
                level_type="resistance",
                strength="moderate",
                description=f"Resistance recente: {resistance_level:.2f}"
            ))

        return levels, position_52w, distance_ma200

    def _determine_signal(
        self,
        current_price: float,
        fair_value: Optional[float],
        fair_value_low: Optional[float],
        upside: Optional[float],
        position_52w: float,
        distance_ma200: float,
        methods: list[ValuationMethod]
    ) -> tuple[PriceSignal, int, list[str]]:
        """Détermine le signal d'achat et sa force."""
        reasons = []
        score = 50  # Score neutre de base

        # 1. Analyse du potentiel de hausse
        if upside is not None:
            if upside > 30:
                score += 25
                reasons.append(f"Fort potentiel de hausse ({upside:+.0f}%)")
            elif upside > 15:
                score += 15
                reasons.append(f"Bon potentiel de hausse ({upside:+.0f}%)")
            elif upside > 0:
                score += 5
                reasons.append(f"Potentiel de hausse modere ({upside:+.0f}%)")
            elif upside > -10:
                score -= 5
                reasons.append(f"Potentiel limite ({upside:+.0f}%)")
            else:
                score -= 20
                reasons.append(f"Surevalue ({upside:+.0f}%)")

        # 2. Position dans le range 52 semaines
        if position_52w < 20:
            score += 15
            reasons.append("Proche du plus bas 52 semaines")
        elif position_52w < 40:
            score += 8
            reasons.append("Dans la partie basse du range annuel")
        elif position_52w > 90:
            score -= 15
            reasons.append("Proche du plus haut 52 semaines")
        elif position_52w > 75:
            score -= 8
            reasons.append("Dans la partie haute du range annuel")

        # 3. Distance par rapport à la MA200
        if distance_ma200 < -15:
            score += 10
            reasons.append("Bien en-dessous de la MM200 (opportunite)")
        elif distance_ma200 < -5:
            score += 5
            reasons.append("En-dessous de la MM200")
        elif distance_ma200 > 20:
            score -= 10
            reasons.append("Tres au-dessus de la MM200 (risque)")

        # 4. Consensus des méthodes de valorisation
        bullish_methods = sum(1 for m in methods if m.upside_percent and m.upside_percent > 10)
        bearish_methods = sum(1 for m in methods if m.upside_percent and m.upside_percent < -10)

        if bullish_methods >= 3:
            score += 10
            reasons.append(f"{bullish_methods} methodes suggerent une sous-evaluation")
        elif bearish_methods >= 2:
            score -= 10
            reasons.append(f"{bearish_methods} methodes suggerent une surevaluation")

        # Convertir le score en signal
        if score >= 75:
            signal = PriceSignal.STRONG_BUY
            strength = 5
        elif score >= 60:
            signal = PriceSignal.BUY
            strength = 4
        elif score >= 45:
            signal = PriceSignal.HOLD
            strength = 3
        elif score >= 30:
            signal = PriceSignal.OVERVALUED
            strength = 2
        else:
            signal = PriceSignal.AVOID
            strength = 1

        return signal, strength, reasons

    def _calculate_buy_prices(
        self,
        current_price: float,
        fair_value: Optional[float],
        fair_value_low: Optional[float],
        price_levels: list[PriceLevel]
    ) -> tuple[Optional[float], Optional[float]]:
        """Calcule les prix d'achat recommandés."""
        ideal_buy = None
        max_buy = None

        # Prix d'achat idéal = juste valeur avec marge de sécurité 15%
        if fair_value:
            ideal_buy = fair_value * 0.85

        # Prix d'achat maximum = juste valeur
        if fair_value:
            max_buy = fair_value

        # Ajuster avec les supports techniques
        supports = [l.price for l in price_levels
                   if l.level_type == "support" and l.price < current_price]

        if supports:
            nearest_support = max(supports)
            if ideal_buy is None or nearest_support < ideal_buy:
                # Le support peut être un meilleur point d'entrée
                if nearest_support > current_price * 0.7:  # Pas plus de 30% en-dessous
                    ideal_buy = nearest_support

        return ideal_buy, max_buy

    def _generate_summary(
        self,
        signal: PriceSignal,
        current_price: float,
        fair_value: Optional[float],
        upside: Optional[float],
        ideal_buy: Optional[float],
        currency: str
    ) -> str:
        """Génère un résumé textuel de l'analyse."""
        signal_texts = {
            PriceSignal.STRONG_BUY: "ACHAT FORT - Prix tres attractif",
            PriceSignal.BUY: "ACHAT - Bon prix d'entree",
            PriceSignal.HOLD: "ATTENDRE - Prix correct mais pas optimal",
            PriceSignal.OVERVALUED: "SUREVALUE - Attendre une correction",
            PriceSignal.AVOID: "EVITER - Prix trop eleve"
        }

        summary = signal_texts[signal]

        if fair_value and upside:
            summary += f". Juste valeur estimee: {fair_value:.2f} {currency} ({upside:+.1f}%)"

        if ideal_buy and ideal_buy < current_price:
            discount = ((current_price - ideal_buy) / current_price) * 100
            summary += f". Prix d'achat ideal: {ideal_buy:.2f} {currency} (-{discount:.0f}%)"

        return summary


# Instance singleton
estimator = PriceEstimator()


def main():
    """Test du module d'estimation de prix."""
    # Test avec des données simulées
    fundamentals = {
        "eps": 6.05,
        "pe_ratio": 28.5,
        "free_cash_flow": 100000,  # millions
        "market_cap": 3000000,  # millions
        "shares_outstanding": 16200000000,
        "dividend_yield": 0.005,
        "revenue_growth": 0.08,
        "earnings_growth": 0.10,
        "beta": 1.2
    }

    import pandas as pd
    import numpy as np

    # Créer des données de prix simulées
    np.random.seed(42)
    dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
    prices = 150 + np.cumsum(np.random.randn(300) * 2)

    df = pd.DataFrame({
        'Open': prices - np.random.rand(300),
        'High': prices + np.random.rand(300) * 2,
        'Low': prices - np.random.rand(300) * 2,
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 300)
    }, index=dates)

    current_price = 185.50

    analysis = estimator.analyze_price(
        ticker="AAPL",
        current_price=current_price,
        currency="USD",
        fundamentals=fundamentals,
        price_history=df,
        sector="Technology",
        analyst_target=200.0,
        analyst_recommendation="Buy"
    )

    print("="*60)
    print(f"ANALYSE DE PRIX - {analysis.ticker}")
    print("="*60)
    print(f"\nPrix actuel: {analysis.current_price} {analysis.currency}")
    print(f"\nSIGNAL: {analysis.signal.value.upper()} (Force: {analysis.signal_strength}/5)")
    print(f"\n{analysis.summary}")

    print("\n--- Estimation Juste Valeur ---")
    print(f"  Basse: {analysis.fair_value_low:.2f}" if analysis.fair_value_low else "  Basse: N/A")
    print(f"  Mediane: {analysis.fair_value_mid:.2f}" if analysis.fair_value_mid else "  Mediane: N/A")
    print(f"  Haute: {analysis.fair_value_high:.2f}" if analysis.fair_value_high else "  Haute: N/A")

    print("\n--- Prix d'Achat Recommandes ---")
    print(f"  Ideal: {analysis.ideal_buy_price:.2f}" if analysis.ideal_buy_price else "  Ideal: N/A")
    print(f"  Maximum: {analysis.max_buy_price:.2f}" if analysis.max_buy_price else "  Maximum: N/A")

    print("\n--- Methodes de Valorisation ---")
    for method in analysis.valuation_methods:
        print(f"  {method.method_name}:")
        print(f"    Juste valeur: {method.fair_value:.2f}" if method.fair_value else "    Juste valeur: N/A")
        print(f"    Potentiel: {method.upside_percent:+.1f}%" if method.upside_percent else "    Potentiel: N/A")
        print(f"    {method.description}")

    print("\n--- Niveaux de Prix ---")
    for level in analysis.price_levels:
        print(f"  {level.level_type}: {level.price:.2f} ({level.strength})")

    print("\n--- Raisons ---")
    for reason in analysis.reasons:
        print(f"  - {reason}")


if __name__ == "__main__":
    main()
