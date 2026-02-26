"""
AI Portfolio Advisor - Analyse IA du portefeuille avec Ollama
Style Moning AI Analysis
"""

import json
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class AIAnalysisResult:
    """Résultat de l'analyse IA."""
    summary: str  # Résumé en 2-3 phrases
    strengths: List[str]  # Points forts
    weaknesses: List[str]  # Points faibles
    recommendations: List[str]  # Recommandations
    risk_assessment: str  # Évaluation du risque
    outlook: str  # Perspective
    confidence: str  # Confiance dans l'analyse
    timestamp: datetime


class AIPortfolioAdvisor:
    """Conseiller IA pour l'analyse de portefeuille."""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # ou mistral, phi, etc.

    def _check_ollama(self) -> bool:
        """Vérifie si Ollama est disponible."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Appelle Ollama pour générer une réponse."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 1000
                    }
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            print(f"Erreur Ollama: {e}")
        return None

    def analyze_portfolio(
        self,
        portfolio_data: Dict
    ) -> AIAnalysisResult:
        """
        Analyse un portefeuille avec l'IA.

        Args:
            portfolio_data: {
                'total_value': float,
                'total_gain': float,
                'gain_pct': float,
                'positions': [
                    {'ticker': str, 'name': str, 'value': float, 'weight': float,
                     'gain_pct': float, 'sector': str, 'score': float}
                ],
                'sector_allocation': {'sector': pct},
                'country_allocation': {'country': pct},
                'diversification_score': float
            }
        """
        # Construire le contexte
        positions_text = ""
        for pos in portfolio_data.get('positions', [])[:10]:  # Top 10
            positions_text += f"- {pos.get('ticker', 'N/A')} ({pos.get('name', '')[:20]}): "
            positions_text += f"{pos.get('weight', 0):.1f}% du portefeuille, "
            positions_text += f"perf: {pos.get('gain_pct', 0):+.1f}%, "
            positions_text += f"secteur: {pos.get('sector', 'N/A')}, "
            positions_text += f"score: {pos.get('score', 50):.0f}/100\n"

        sector_text = ", ".join([
            f"{s}: {p:.1f}%"
            for s, p in portfolio_data.get('sector_allocation', {}).items()
        ][:5])

        country_text = ", ".join([
            f"{c}: {p:.1f}%"
            for c, p in portfolio_data.get('country_allocation', {}).items()
        ][:5])

        prompt = f"""Tu es un conseiller financier expert. Analyse ce portefeuille d'investissement et donne des conseils personnalisés.

DONNÉES DU PORTEFEUILLE:
- Valeur totale: {portfolio_data.get('total_value', 0):,.0f}€
- Performance: {portfolio_data.get('gain_pct', 0):+.1f}%
- Gain/Perte: {portfolio_data.get('total_gain', 0):+,.0f}€
- Score de diversification: {portfolio_data.get('diversification_score', 50):.0f}/100

POSITIONS PRINCIPALES:
{positions_text}

RÉPARTITION SECTORIELLE: {sector_text}

RÉPARTITION GÉOGRAPHIQUE: {country_text}

Réponds en français avec le format JSON suivant:
{{
    "summary": "Résumé en 2-3 phrases de l'état du portefeuille",
    "strengths": ["Point fort 1", "Point fort 2", "Point fort 3"],
    "weaknesses": ["Point faible 1", "Point faible 2"],
    "recommendations": ["Recommandation 1", "Recommandation 2", "Recommandation 3"],
    "risk_assessment": "Faible/Modéré/Élevé avec explication",
    "outlook": "Perspective à court/moyen terme"
}}

Sois précis et actionnable dans tes recommandations."""

        # Vérifier Ollama
        if self._check_ollama():
            response = self._call_ollama(prompt)
            if response:
                return self._parse_ai_response(response)

        # Fallback: analyse basée sur des règles
        return self._rule_based_analysis(portfolio_data)

    def _parse_ai_response(self, response: str) -> AIAnalysisResult:
        """Parse la réponse JSON de l'IA."""
        try:
            # Extraire le JSON de la réponse
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                return AIAnalysisResult(
                    summary=data.get('summary', 'Analyse non disponible'),
                    strengths=data.get('strengths', []),
                    weaknesses=data.get('weaknesses', []),
                    recommendations=data.get('recommendations', []),
                    risk_assessment=data.get('risk_assessment', 'Non évalué'),
                    outlook=data.get('outlook', 'Non disponible'),
                    confidence="Haute",
                    timestamp=datetime.now()
                )
        except json.JSONDecodeError:
            pass

        # Si parsing échoue, retourner la réponse brute
        return AIAnalysisResult(
            summary=response[:500] if response else "Analyse non disponible",
            strengths=[],
            weaknesses=[],
            recommendations=[],
            risk_assessment="Non évalué",
            outlook="Non disponible",
            confidence="Faible",
            timestamp=datetime.now()
        )

    def _rule_based_analysis(self, portfolio_data: Dict) -> AIAnalysisResult:
        """Analyse basée sur des règles (fallback sans Ollama)."""
        strengths = []
        weaknesses = []
        recommendations = []

        total_value = portfolio_data.get('total_value', 0)
        gain_pct = portfolio_data.get('gain_pct', 0)
        div_score = portfolio_data.get('diversification_score', 50)
        positions = portfolio_data.get('positions', [])
        sector_alloc = portfolio_data.get('sector_allocation', {})

        # Analyser la performance
        if gain_pct > 15:
            strengths.append(f"Excellente performance ({gain_pct:+.1f}%)")
        elif gain_pct > 5:
            strengths.append(f"Bonne performance ({gain_pct:+.1f}%)")
        elif gain_pct < -10:
            weaknesses.append(f"Performance négative ({gain_pct:+.1f}%)")

        # Analyser la diversification
        if div_score >= 70:
            strengths.append(f"Portefeuille bien diversifié (score: {div_score:.0f}/100)")
        elif div_score < 50:
            weaknesses.append(f"Diversification insuffisante (score: {div_score:.0f}/100)")
            recommendations.append("Diversifiez davantage vos positions")

        # Analyser la concentration
        if positions:
            top_weight = max(p.get('weight', 0) for p in positions)
            if top_weight > 30:
                weaknesses.append(f"Position trop concentrée ({top_weight:.0f}% sur une seule valeur)")
                recommendations.append("Réduisez votre exposition à la position principale")
            elif top_weight < 15:
                strengths.append("Bonne répartition entre les positions")

        # Analyser les secteurs
        if sector_alloc:
            tech_pct = sector_alloc.get('Technology', 0) + sector_alloc.get('Tech', 0)
            if tech_pct > 40:
                weaknesses.append(f"Surexposition au secteur technologique ({tech_pct:.0f}%)")
                recommendations.append("Diversifiez dans d'autres secteurs (santé, consommation)")

        # Analyser les scores des positions
        high_score_positions = [p for p in positions if p.get('score', 0) >= 70]
        low_score_positions = [p for p in positions if p.get('score', 0) < 40]

        if len(high_score_positions) >= 3:
            strengths.append(f"{len(high_score_positions)} positions avec un score élevé (>70)")

        if low_score_positions:
            weaknesses.append(f"{len(low_score_positions)} position(s) avec score faible (<40)")
            for p in low_score_positions[:2]:
                recommendations.append(f"Revoir la position {p.get('ticker', '')} (score: {p.get('score', 0):.0f})")

        # Recommandations générales
        if len(positions) < 5:
            recommendations.append("Ajoutez plus de positions pour réduire le risque")
        if len(recommendations) == 0:
            recommendations.append("Continuez votre stratégie actuelle")
            recommendations.append("Restez discipliné dans vos versements réguliers")

        # Évaluation du risque
        if div_score >= 70 and len(positions) >= 10:
            risk = "Faible - Portefeuille bien diversifié"
        elif div_score >= 50 and len(positions) >= 5:
            risk = "Modéré - Diversification acceptable"
        else:
            risk = "Élevé - Concentration excessive"

        # Résumé
        if gain_pct > 0:
            summary = f"Votre portefeuille de {total_value:,.0f}€ affiche une performance positive de {gain_pct:+.1f}%. "
        else:
            summary = f"Votre portefeuille de {total_value:,.0f}€ est actuellement en perte de {gain_pct:.1f}%. "

        if div_score >= 60:
            summary += "La diversification est satisfaisante."
        else:
            summary += "La diversification pourrait être améliorée."

        # Perspective
        outlook = "Perspective neutre à positive. "
        if high_score_positions:
            outlook += f"Les {len(high_score_positions)} positions bien notées devraient soutenir la performance."

        return AIAnalysisResult(
            summary=summary,
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            recommendations=recommendations[:5],
            risk_assessment=risk,
            outlook=outlook,
            confidence="Moyenne (analyse basée sur règles)",
            timestamp=datetime.now()
        )

    def get_stock_insight(self, ticker: str, stock_data: Dict) -> str:
        """Génère un insight rapide sur une action."""
        prompt = f"""En une phrase, donne ton avis sur l'action {ticker}:
- Prix: {stock_data.get('price', 0):.2f}
- Score global: {stock_data.get('score', 50):.0f}/100
- P/E: {stock_data.get('pe', 'N/A')}
- Croissance CA: {stock_data.get('revenue_growth', 'N/A')}%
- Rendement dividende: {stock_data.get('dividend_yield', 0):.2f}%

Réponds en français, une phrase maximum."""

        if self._check_ollama():
            response = self._call_ollama(prompt)
            if response:
                return response.strip()

        # Fallback
        score = stock_data.get('score', 50)
        if score >= 70:
            return f"{ticker} présente un profil attractif avec un score de {score:.0f}/100."
        elif score >= 50:
            return f"{ticker} est dans la moyenne avec un score de {score:.0f}/100."
        else:
            return f"{ticker} nécessite une vigilance avec un score de {score:.0f}/100."


def get_ai_advisor() -> AIPortfolioAdvisor:
    """Factory function."""
    return AIPortfolioAdvisor()


if __name__ == "__main__":
    advisor = AIPortfolioAdvisor()

    # Test
    portfolio_data = {
        'total_value': 25000,
        'total_gain': 3500,
        'gain_pct': 14.0,
        'diversification_score': 65,
        'positions': [
            {'ticker': 'AAPL', 'name': 'Apple Inc', 'value': 5000, 'weight': 20,
             'gain_pct': 25, 'sector': 'Technology', 'score': 75},
            {'ticker': 'MSFT', 'name': 'Microsoft', 'value': 4000, 'weight': 16,
             'gain_pct': 30, 'sector': 'Technology', 'score': 80},
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'value': 3000, 'weight': 12,
             'gain_pct': 5, 'sector': 'Healthcare', 'score': 65},
            {'ticker': 'KO', 'name': 'Coca-Cola', 'value': 2500, 'weight': 10,
             'gain_pct': 8, 'sector': 'Consumer', 'score': 60},
            {'ticker': 'MC.PA', 'name': 'LVMH', 'value': 3500, 'weight': 14,
             'gain_pct': 15, 'sector': 'Luxury', 'score': 70},
        ],
        'sector_allocation': {
            'Technology': 36,
            'Healthcare': 12,
            'Consumer': 10,
            'Luxury': 14,
            'Other': 28
        },
        'country_allocation': {
            'United States': 58,
            'France': 14,
            'Other': 28
        }
    }

    print("=" * 70)
    print("TEST ANALYSE IA DU PORTEFEUILLE")
    print("=" * 70)

    result = advisor.analyze_portfolio(portfolio_data)

    print(f"\n📊 RÉSUMÉ:")
    print(f"  {result.summary}")

    print(f"\n✅ POINTS FORTS:")
    for s in result.strengths:
        print(f"  • {s}")

    print(f"\n⚠️ POINTS FAIBLES:")
    for w in result.weaknesses:
        print(f"  • {w}")

    print(f"\n💡 RECOMMANDATIONS:")
    for r in result.recommendations:
        print(f"  • {r}")

    print(f"\n🎯 RISQUE: {result.risk_assessment}")
    print(f"\n📈 PERSPECTIVE: {result.outlook}")
    print(f"\n🔍 Confiance: {result.confidence}")
