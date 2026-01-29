"""
Analyse Fondamentale - Évaluation et scoring
"""

from dataclasses import dataclass
from typing import Optional
from loguru import logger


@dataclass
class FundamentalSignal:
    """Signal fondamental individuel."""
    name: str
    value: Optional[float]
    signal: str  # "bullish", "bearish", "neutral"
    weight: float
    description: str
    threshold_low: Optional[float] = None
    threshold_high: Optional[float] = None


@dataclass
class FundamentalAnalysis:
    """Résultat complet de l'analyse fondamentale."""
    ticker: str
    score: float  # 0-100
    signals: list[FundamentalSignal]
    valuation: str  # "undervalued", "fairly_valued", "overvalued"
    quality: str  # "high", "medium", "low"
    growth: str  # "high", "moderate", "low", "negative"
    financial_health: str  # "strong", "moderate", "weak"


class FundamentalAnalyzer:
    """Analyseur fondamental pour les actions."""

    def __init__(self):
        # Pondérations des critères
        self.weights = {
            # Valorisation (35%)
            "pe_ratio": 0.10,
            "peg_ratio": 0.10,
            "pb_ratio": 0.05,
            "ev_ebitda": 0.10,

            # Rentabilité (25%)
            "roe": 0.10,
            "profit_margin": 0.10,
            "roa": 0.05,

            # Croissance (20%)
            "revenue_growth": 0.10,
            "earnings_growth": 0.10,

            # Santé financière (15%)
            "debt_to_equity": 0.10,
            "current_ratio": 0.05,

            # Dividendes (5%)
            "dividend_yield": 0.05
        }

        # Seuils par secteur (valeurs par défaut)
        self.default_thresholds = {
            "pe_ratio": {"low": 10, "high": 25, "max": 50},
            "peg_ratio": {"low": 0.5, "high": 1.5, "max": 3},
            "pb_ratio": {"low": 1, "high": 3, "max": 10},
            "ev_ebitda": {"low": 6, "high": 12, "max": 25},
            "roe": {"low": 10, "high": 20, "min": 0},
            "profit_margin": {"low": 5, "high": 15, "min": 0},
            "roa": {"low": 5, "high": 10, "min": 0},
            "revenue_growth": {"low": 5, "high": 20, "min": -10},
            "earnings_growth": {"low": 5, "high": 25, "min": -20},
            "debt_to_equity": {"low": 0.3, "high": 1.5, "max": 3},
            "current_ratio": {"low": 1, "high": 2, "min": 0.5},
            "dividend_yield": {"low": 1, "high": 4, "max": 10}
        }

        # Seuils ajustés par secteur
        self.sector_adjustments = {
            "Technology": {
                "pe_ratio": {"low": 15, "high": 35, "max": 80},
                "pb_ratio": {"low": 2, "high": 8, "max": 20},
                "revenue_growth": {"low": 10, "high": 30, "min": 0},
            },
            "Financials": {
                "pe_ratio": {"low": 8, "high": 15, "max": 25},
                "pb_ratio": {"low": 0.5, "high": 1.5, "max": 3},
                "debt_to_equity": {"low": 1, "high": 5, "max": 15},  # Banques ont plus de dette
            },
            "Utilities": {
                "pe_ratio": {"low": 12, "high": 20, "max": 30},
                "dividend_yield": {"low": 3, "high": 5, "max": 8},
                "revenue_growth": {"low": 0, "high": 5, "min": -5},
            },
            "Real Estate": {
                "pe_ratio": {"low": 15, "high": 30, "max": 50},
                "dividend_yield": {"low": 3, "high": 6, "max": 10},
            },
            "Healthcare": {
                "pe_ratio": {"low": 12, "high": 30, "max": 60},
                "revenue_growth": {"low": 5, "high": 15, "min": 0},
            },
            "Consumer Staples": {
                "pe_ratio": {"low": 15, "high": 25, "max": 35},
                "dividend_yield": {"low": 2, "high": 4, "max": 6},
            },
            "Energy": {
                "pe_ratio": {"low": 5, "high": 15, "max": 25},
                "dividend_yield": {"low": 3, "high": 6, "max": 10},
            }
        }

    def get_thresholds(self, metric: str, sector: Optional[str] = None) -> dict:
        """Récupère les seuils pour une métrique, ajustés au secteur si disponible."""
        base = self.default_thresholds.get(metric, {})

        if sector and sector in self.sector_adjustments:
            sector_adj = self.sector_adjustments[sector].get(metric, {})
            return {**base, **sector_adj}

        return base

    def analyze(
        self,
        fundamentals: dict,
        ticker: str = "",
        sector: Optional[str] = None
    ) -> Optional[FundamentalAnalysis]:
        """
        Analyse fondamentale complète d'une action.

        Args:
            fundamentals: Dict avec les données fondamentales
            ticker: Symbole de l'action
            sector: Secteur pour ajuster les seuils

        Returns:
            FundamentalAnalysis avec score et signaux
        """
        try:
            signals = []

            # 1. Valorisation
            pe_signal = self._analyze_pe(fundamentals.get("pe_ratio"), sector)
            signals.append(pe_signal)

            peg_signal = self._analyze_peg(fundamentals.get("peg_ratio"), sector)
            signals.append(peg_signal)

            pb_signal = self._analyze_pb(fundamentals.get("pb_ratio"), sector)
            signals.append(pb_signal)

            ev_ebitda_signal = self._analyze_ev_ebitda(fundamentals.get("ev_ebitda"), sector)
            signals.append(ev_ebitda_signal)

            # 2. Rentabilité
            roe_signal = self._analyze_roe(fundamentals.get("roe"), sector)
            signals.append(roe_signal)

            margin_signal = self._analyze_profit_margin(fundamentals.get("profit_margin"), sector)
            signals.append(margin_signal)

            roa_signal = self._analyze_roa(fundamentals.get("roa"), sector)
            signals.append(roa_signal)

            # 3. Croissance
            rev_growth_signal = self._analyze_revenue_growth(fundamentals.get("revenue_growth"), sector)
            signals.append(rev_growth_signal)

            earn_growth_signal = self._analyze_earnings_growth(fundamentals.get("earnings_growth"), sector)
            signals.append(earn_growth_signal)

            # 4. Santé financière
            debt_signal = self._analyze_debt(fundamentals.get("debt_to_equity"), sector)
            signals.append(debt_signal)

            current_ratio_signal = self._analyze_current_ratio(fundamentals.get("current_ratio"), sector)
            signals.append(current_ratio_signal)

            # 5. Dividendes
            div_signal = self._analyze_dividend(fundamentals.get("dividend_yield"), sector)
            signals.append(div_signal)

            # Calcul du score global
            score = self._calculate_score(signals)

            # Évaluations qualitatives
            valuation = self._assess_valuation(signals)
            quality = self._assess_quality(signals)
            growth = self._assess_growth(signals)
            financial_health = self._assess_financial_health(signals)

            return FundamentalAnalysis(
                ticker=ticker,
                score=score,
                signals=signals,
                valuation=valuation,
                quality=quality,
                growth=growth,
                financial_health=financial_health
            )

        except Exception as e:
            logger.error(f"Erreur analyse fondamentale {ticker}: {e}")
            return None

    def _analyze_pe(self, pe: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le P/E ratio."""
        thresholds = self.get_thresholds("pe_ratio", sector)

        if pe is None or pe <= 0:
            return FundamentalSignal(
                name="pe_ratio",
                value=pe,
                signal="neutral",
                weight=self.weights["pe_ratio"],
                description="P/E non disponible ou négatif (entreprise non rentable)",
                threshold_low=thresholds.get("low"),
                threshold_high=thresholds.get("high")
            )

        if pe < thresholds["low"]:
            signal = "bullish"
            description = f"P/E attractif ({pe:.1f} < {thresholds['low']})"
        elif pe > thresholds["high"]:
            signal = "bearish"
            description = f"P/E élevé ({pe:.1f} > {thresholds['high']})"
        else:
            signal = "neutral"
            description = f"P/E dans la normale ({pe:.1f})"

        return FundamentalSignal(
            name="pe_ratio",
            value=pe,
            signal=signal,
            weight=self.weights["pe_ratio"],
            description=description,
            threshold_low=thresholds.get("low"),
            threshold_high=thresholds.get("high")
        )

    def _analyze_peg(self, peg: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le PEG ratio."""
        thresholds = self.get_thresholds("peg_ratio", sector)

        if peg is None or peg <= 0:
            return FundamentalSignal(
                name="peg_ratio",
                value=peg,
                signal="neutral",
                weight=self.weights["peg_ratio"],
                description="PEG non disponible",
                threshold_low=thresholds.get("low"),
                threshold_high=thresholds.get("high")
            )

        if peg < thresholds["low"]:
            signal = "bullish"
            description = f"PEG très attractif ({peg:.2f} < {thresholds['low']})"
        elif peg <= 1:
            signal = "bullish"
            description = f"PEG attractif ({peg:.2f} ≤ 1)"
        elif peg > thresholds["high"]:
            signal = "bearish"
            description = f"PEG élevé ({peg:.2f} > {thresholds['high']})"
        else:
            signal = "neutral"
            description = f"PEG dans la normale ({peg:.2f})"

        return FundamentalSignal(
            name="peg_ratio",
            value=peg,
            signal=signal,
            weight=self.weights["peg_ratio"],
            description=description,
            threshold_low=thresholds.get("low"),
            threshold_high=thresholds.get("high")
        )

    def _analyze_pb(self, pb: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le P/B ratio."""
        thresholds = self.get_thresholds("pb_ratio", sector)

        if pb is None or pb <= 0:
            return FundamentalSignal(
                name="pb_ratio",
                value=pb,
                signal="neutral",
                weight=self.weights["pb_ratio"],
                description="P/B non disponible"
            )

        if pb < thresholds["low"]:
            signal = "bullish"
            description = f"P/B attractif ({pb:.2f} < {thresholds['low']})"
        elif pb > thresholds["high"]:
            signal = "bearish"
            description = f"P/B élevé ({pb:.2f} > {thresholds['high']})"
        else:
            signal = "neutral"
            description = f"P/B dans la normale ({pb:.2f})"

        return FundamentalSignal(
            name="pb_ratio",
            value=pb,
            signal=signal,
            weight=self.weights["pb_ratio"],
            description=description
        )

    def _analyze_ev_ebitda(self, ev_ebitda: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le EV/EBITDA."""
        thresholds = self.get_thresholds("ev_ebitda", sector)

        if ev_ebitda is None or ev_ebitda <= 0:
            return FundamentalSignal(
                name="ev_ebitda",
                value=ev_ebitda,
                signal="neutral",
                weight=self.weights["ev_ebitda"],
                description="EV/EBITDA non disponible"
            )

        if ev_ebitda < thresholds["low"]:
            signal = "bullish"
            description = f"EV/EBITDA attractif ({ev_ebitda:.1f} < {thresholds['low']})"
        elif ev_ebitda > thresholds["high"]:
            signal = "bearish"
            description = f"EV/EBITDA élevé ({ev_ebitda:.1f} > {thresholds['high']})"
        else:
            signal = "neutral"
            description = f"EV/EBITDA dans la normale ({ev_ebitda:.1f})"

        return FundamentalSignal(
            name="ev_ebitda",
            value=ev_ebitda,
            signal=signal,
            weight=self.weights["ev_ebitda"],
            description=description
        )

    def _analyze_roe(self, roe: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le ROE."""
        thresholds = self.get_thresholds("roe", sector)

        if roe is None:
            return FundamentalSignal(
                name="roe",
                value=roe,
                signal="neutral",
                weight=self.weights["roe"],
                description="ROE non disponible"
            )

        # Convertir en pourcentage si nécessaire
        roe_pct = roe * 100 if roe < 1 else roe

        if roe_pct > thresholds["high"]:
            signal = "bullish"
            description = f"ROE excellent ({roe_pct:.1f}% > {thresholds['high']}%)"
        elif roe_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"ROE correct ({roe_pct:.1f}%)"
        elif roe_pct > 0:
            signal = "bearish"
            description = f"ROE faible ({roe_pct:.1f}% < {thresholds['low']}%)"
        else:
            signal = "bearish"
            description = f"ROE négatif ({roe_pct:.1f}%)"

        return FundamentalSignal(
            name="roe",
            value=roe_pct,
            signal=signal,
            weight=self.weights["roe"],
            description=description
        )

    def _analyze_profit_margin(self, margin: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse la marge bénéficiaire."""
        thresholds = self.get_thresholds("profit_margin", sector)

        if margin is None:
            return FundamentalSignal(
                name="profit_margin",
                value=margin,
                signal="neutral",
                weight=self.weights["profit_margin"],
                description="Marge non disponible"
            )

        margin_pct = margin * 100 if abs(margin) < 1 else margin

        if margin_pct > thresholds["high"]:
            signal = "bullish"
            description = f"Marge excellente ({margin_pct:.1f}%)"
        elif margin_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"Marge correcte ({margin_pct:.1f}%)"
        elif margin_pct > 0:
            signal = "bearish"
            description = f"Marge faible ({margin_pct:.1f}%)"
        else:
            signal = "bearish"
            description = f"Marge négative ({margin_pct:.1f}%)"

        return FundamentalSignal(
            name="profit_margin",
            value=margin_pct,
            signal=signal,
            weight=self.weights["profit_margin"],
            description=description
        )

    def _analyze_roa(self, roa: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le ROA."""
        thresholds = self.get_thresholds("roa", sector)

        if roa is None:
            return FundamentalSignal(
                name="roa",
                value=roa,
                signal="neutral",
                weight=self.weights["roa"],
                description="ROA non disponible"
            )

        roa_pct = roa * 100 if abs(roa) < 1 else roa

        if roa_pct > thresholds["high"]:
            signal = "bullish"
            description = f"ROA excellent ({roa_pct:.1f}%)"
        elif roa_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"ROA correct ({roa_pct:.1f}%)"
        else:
            signal = "bearish"
            description = f"ROA faible ({roa_pct:.1f}%)"

        return FundamentalSignal(
            name="roa",
            value=roa_pct,
            signal=signal,
            weight=self.weights["roa"],
            description=description
        )

    def _analyze_revenue_growth(self, growth: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse la croissance du CA."""
        thresholds = self.get_thresholds("revenue_growth", sector)

        if growth is None:
            return FundamentalSignal(
                name="revenue_growth",
                value=growth,
                signal="neutral",
                weight=self.weights["revenue_growth"],
                description="Croissance CA non disponible"
            )

        growth_pct = growth * 100 if abs(growth) < 1 else growth

        if growth_pct > thresholds["high"]:
            signal = "bullish"
            description = f"Forte croissance CA ({growth_pct:.1f}%)"
        elif growth_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"Croissance CA modérée ({growth_pct:.1f}%)"
        elif growth_pct >= 0:
            signal = "bearish"
            description = f"Croissance CA faible ({growth_pct:.1f}%)"
        else:
            signal = "bearish"
            description = f"CA en déclin ({growth_pct:.1f}%)"

        return FundamentalSignal(
            name="revenue_growth",
            value=growth_pct,
            signal=signal,
            weight=self.weights["revenue_growth"],
            description=description
        )

    def _analyze_earnings_growth(self, growth: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse la croissance des bénéfices."""
        thresholds = self.get_thresholds("earnings_growth", sector)

        if growth is None:
            return FundamentalSignal(
                name="earnings_growth",
                value=growth,
                signal="neutral",
                weight=self.weights["earnings_growth"],
                description="Croissance bénéfices non disponible"
            )

        growth_pct = growth * 100 if abs(growth) < 1 else growth

        if growth_pct > thresholds["high"]:
            signal = "bullish"
            description = f"Forte croissance bénéfices ({growth_pct:.1f}%)"
        elif growth_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"Croissance bénéfices modérée ({growth_pct:.1f}%)"
        elif growth_pct >= 0:
            signal = "bearish"
            description = f"Croissance bénéfices faible ({growth_pct:.1f}%)"
        else:
            signal = "bearish"
            description = f"Bénéfices en déclin ({growth_pct:.1f}%)"

        return FundamentalSignal(
            name="earnings_growth",
            value=growth_pct,
            signal=signal,
            weight=self.weights["earnings_growth"],
            description=description
        )

    def _analyze_debt(self, debt_to_equity: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le ratio dette/capitaux propres."""
        thresholds = self.get_thresholds("debt_to_equity", sector)

        if debt_to_equity is None:
            return FundamentalSignal(
                name="debt_to_equity",
                value=debt_to_equity,
                signal="neutral",
                weight=self.weights["debt_to_equity"],
                description="Dette/Equity non disponible"
            )

        # Convertir si en pourcentage
        d_e = debt_to_equity / 100 if debt_to_equity > 10 else debt_to_equity

        if d_e < thresholds["low"]:
            signal = "bullish"
            description = f"Faible endettement (D/E: {d_e:.2f})"
        elif d_e > thresholds["high"]:
            signal = "bearish"
            description = f"Endettement élevé (D/E: {d_e:.2f})"
        else:
            signal = "neutral"
            description = f"Endettement modéré (D/E: {d_e:.2f})"

        return FundamentalSignal(
            name="debt_to_equity",
            value=d_e,
            signal=signal,
            weight=self.weights["debt_to_equity"],
            description=description
        )

    def _analyze_current_ratio(self, ratio: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le current ratio."""
        thresholds = self.get_thresholds("current_ratio", sector)

        if ratio is None:
            return FundamentalSignal(
                name="current_ratio",
                value=ratio,
                signal="neutral",
                weight=self.weights["current_ratio"],
                description="Current ratio non disponible"
            )

        if ratio > thresholds["high"]:
            signal = "bullish"
            description = f"Excellente liquidité (CR: {ratio:.2f})"
        elif ratio >= thresholds["low"]:
            signal = "neutral"
            description = f"Liquidité correcte (CR: {ratio:.2f})"
        else:
            signal = "bearish"
            description = f"Liquidité faible (CR: {ratio:.2f})"

        return FundamentalSignal(
            name="current_ratio",
            value=ratio,
            signal=signal,
            weight=self.weights["current_ratio"],
            description=description
        )

    def _analyze_dividend(self, div_yield: Optional[float], sector: Optional[str]) -> FundamentalSignal:
        """Analyse le rendement du dividende."""
        thresholds = self.get_thresholds("dividend_yield", sector)

        if div_yield is None or div_yield == 0:
            return FundamentalSignal(
                name="dividend_yield",
                value=0,
                signal="neutral",
                weight=self.weights["dividend_yield"],
                description="Pas de dividende"
            )

        div_pct = div_yield * 100 if div_yield < 1 else div_yield

        if div_pct > thresholds.get("max", 10):
            signal = "bearish"
            description = f"Rendement trop élevé, risque de coupe ({div_pct:.1f}%)"
        elif div_pct >= thresholds["high"]:
            signal = "bullish"
            description = f"Bon rendement ({div_pct:.1f}%)"
        elif div_pct >= thresholds["low"]:
            signal = "neutral"
            description = f"Rendement modéré ({div_pct:.1f}%)"
        else:
            signal = "neutral"
            description = f"Rendement faible ({div_pct:.1f}%)"

        return FundamentalSignal(
            name="dividend_yield",
            value=div_pct,
            signal=signal,
            weight=self.weights["dividend_yield"],
            description=description
        )

    def _calculate_score(self, signals: list[FundamentalSignal]) -> float:
        """Calcule le score global (0-100)."""
        total_weight = sum(s.weight for s in signals if s.value is not None)
        weighted_score = 0

        for signal in signals:
            if signal.value is None:
                continue

            if signal.signal == "bullish":
                score = 100
            elif signal.signal == "bearish":
                score = 0
            else:
                score = 50

            weighted_score += score * (signal.weight / total_weight) if total_weight > 0 else 0

        return round(weighted_score, 2)

    def _assess_valuation(self, signals: list[FundamentalSignal]) -> str:
        """Évalue si l'action est sous/sur-évaluée."""
        valuation_signals = ["pe_ratio", "peg_ratio", "pb_ratio", "ev_ebitda"]
        bullish_count = sum(1 for s in signals if s.name in valuation_signals and s.signal == "bullish")
        bearish_count = sum(1 for s in signals if s.name in valuation_signals and s.signal == "bearish")

        if bullish_count >= 3:
            return "undervalued"
        elif bearish_count >= 3:
            return "overvalued"
        else:
            return "fairly_valued"

    def _assess_quality(self, signals: list[FundamentalSignal]) -> str:
        """Évalue la qualité de l'entreprise."""
        quality_signals = ["roe", "profit_margin", "roa"]
        bullish_count = sum(1 for s in signals if s.name in quality_signals and s.signal == "bullish")

        if bullish_count >= 2:
            return "high"
        elif bullish_count >= 1:
            return "medium"
        else:
            return "low"

    def _assess_growth(self, signals: list[FundamentalSignal]) -> str:
        """Évalue le potentiel de croissance."""
        growth_signals = ["revenue_growth", "earnings_growth"]
        growth_values = [s for s in signals if s.name in growth_signals and s.value is not None]

        if not growth_values:
            return "moderate"

        avg_growth = sum(s.value for s in growth_values) / len(growth_values)

        if avg_growth > 15:
            return "high"
        elif avg_growth > 5:
            return "moderate"
        elif avg_growth >= 0:
            return "low"
        else:
            return "negative"

    def _assess_financial_health(self, signals: list[FundamentalSignal]) -> str:
        """Évalue la santé financière."""
        health_signals = ["debt_to_equity", "current_ratio"]
        bullish_count = sum(1 for s in signals if s.name in health_signals and s.signal == "bullish")
        bearish_count = sum(1 for s in signals if s.name in health_signals and s.signal == "bearish")

        if bullish_count >= 2:
            return "strong"
        elif bearish_count >= 2:
            return "weak"
        else:
            return "moderate"


# Instance singleton
analyzer = FundamentalAnalyzer()


def main():
    """Test de l'analyseur fondamental."""
    # Données de test
    test_fundamentals = {
        "pe_ratio": 22.5,
        "peg_ratio": 1.2,
        "pb_ratio": 4.5,
        "ev_ebitda": 15.0,
        "roe": 0.25,  # 25%
        "profit_margin": 0.21,  # 21%
        "roa": 0.12,  # 12%
        "revenue_growth": 0.08,  # 8%
        "earnings_growth": 0.15,  # 15%
        "debt_to_equity": 0.8,
        "current_ratio": 1.5,
        "dividend_yield": 0.006  # 0.6%
    }

    analysis = analyzer.analyze(test_fundamentals, "TEST", "Technology")

    if analysis:
        print(f"=== Analyse Fondamentale {analysis.ticker} ===")
        print(f"\nScore: {analysis.score}/100")
        print(f"Valorisation: {analysis.valuation}")
        print(f"Qualité: {analysis.quality}")
        print(f"Croissance: {analysis.growth}")
        print(f"Santé financière: {analysis.financial_health}")

        print("\n--- Signaux ---")
        for signal in analysis.signals:
            emoji = "🟢" if signal.signal == "bullish" else "🔴" if signal.signal == "bearish" else "🟡"
            print(f"{emoji} {signal.name}: {signal.description}")


if __name__ == "__main__":
    main()
