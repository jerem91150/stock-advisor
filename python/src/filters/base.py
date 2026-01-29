"""
Système de Filtres - Filtrage des actions selon critères personnalisables
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
import json
from loguru import logger


class FilterType(Enum):
    """Types de filtres disponibles."""
    SECTORAL = "sectoral"
    ETHICAL = "ethical"
    FUNDAMENTAL = "fundamental"
    TECHNICAL = "technical"
    GEOGRAPHIC = "geographic"
    OWNERSHIP = "ownership"
    MARKET = "market"


@dataclass
class FilterResult:
    """Résultat d'un filtre."""
    passed: bool
    filter_name: str
    reason: Optional[str] = None


@dataclass
class StockFilterData:
    """Données d'une action pour filtrage."""
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    market_cap: Optional[float] = None  # En millions
    pea_eligible: bool = False

    # Fondamentaux
    pe_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None

    # Actionnariat (si disponible)
    state_owned_percentage: Optional[float] = None
    sovereign_fund_owned: bool = False
    major_shareholders: list[str] = field(default_factory=list)


class BaseFilter(ABC):
    """Classe de base pour tous les filtres."""

    def __init__(self, name: str, filter_type: FilterType, enabled: bool = True):
        self.name = name
        self.filter_type = filter_type
        self.enabled = enabled

    @abstractmethod
    def apply(self, stock: StockFilterData) -> FilterResult:
        """Applique le filtre à une action."""
        pass

    def to_dict(self) -> dict:
        """Sérialise le filtre en dictionnaire."""
        return {
            "name": self.name,
            "type": self.filter_type.value,
            "enabled": self.enabled,
            "config": self._get_config()
        }

    @abstractmethod
    def _get_config(self) -> dict:
        """Retourne la configuration spécifique du filtre."""
        pass


class SectorFilter(BaseFilter):
    """Filtre par secteur d'activité."""

    # Secteurs controversés par défaut
    DEFAULT_EXCLUDED_SECTORS = [
        "Tobacco",
        "Aerospace & Defense",
        "Gambling",
        "Adult Entertainment"
    ]

    DEFAULT_EXCLUDED_INDUSTRIES = [
        "Tobacco",
        "Weapons",
        "Casinos & Gaming",
        "Coal",
    ]

    def __init__(
        self,
        excluded_sectors: Optional[list[str]] = None,
        excluded_industries: Optional[list[str]] = None,
        name: str = "Filtre Sectoriel",
        enabled: bool = True
    ):
        super().__init__(name, FilterType.SECTORAL, enabled)
        self.excluded_sectors = excluded_sectors or self.DEFAULT_EXCLUDED_SECTORS.copy()
        self.excluded_industries = excluded_industries or self.DEFAULT_EXCLUDED_INDUSTRIES.copy()

    def apply(self, stock: StockFilterData) -> FilterResult:
        if not self.enabled:
            return FilterResult(passed=True, filter_name=self.name)

        # Vérifier secteur
        if stock.sector:
            for excluded in self.excluded_sectors:
                if excluded.lower() in stock.sector.lower():
                    return FilterResult(
                        passed=False,
                        filter_name=self.name,
                        reason=f"Secteur exclu: {stock.sector}"
                    )

        # Vérifier industrie
        if stock.industry:
            for excluded in self.excluded_industries:
                if excluded.lower() in stock.industry.lower():
                    return FilterResult(
                        passed=False,
                        filter_name=self.name,
                        reason=f"Industrie exclue: {stock.industry}"
                    )

        return FilterResult(passed=True, filter_name=self.name)

    def _get_config(self) -> dict:
        return {
            "excluded_sectors": self.excluded_sectors,
            "excluded_industries": self.excluded_industries
        }


class EthicalFilter(BaseFilter):
    """Filtre éthique (ESG simplifié)."""

    # Liste d'entreprises controversées (exemples)
    CONTROVERSIAL_COMPANIES = [
        "PM",       # Philip Morris
        "MO",       # Altria
        "BTI",      # British American Tobacco
        "LMT",      # Lockheed Martin
        "RTX",      # Raytheon
        "NOC",      # Northrop Grumman
        "BA",       # Boeing (défense)
        "GD",       # General Dynamics
    ]

    def __init__(
        self,
        exclude_tobacco: bool = True,
        exclude_weapons: bool = True,
        exclude_gambling: bool = True,
        exclude_fossil_fuels: bool = False,
        custom_exclusions: Optional[list[str]] = None,
        name: str = "Filtre Éthique",
        enabled: bool = True
    ):
        super().__init__(name, FilterType.ETHICAL, enabled)
        self.exclude_tobacco = exclude_tobacco
        self.exclude_weapons = exclude_weapons
        self.exclude_gambling = exclude_gambling
        self.exclude_fossil_fuels = exclude_fossil_fuels
        self.custom_exclusions = custom_exclusions or []

    def apply(self, stock: StockFilterData) -> FilterResult:
        if not self.enabled:
            return FilterResult(passed=True, filter_name=self.name)

        # Vérifier exclusions personnalisées
        if stock.ticker in self.custom_exclusions:
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason=f"Exclu manuellement: {stock.ticker}"
            )

        # Vérifier entreprises controversées connues
        if stock.ticker in self.CONTROVERSIAL_COMPANIES:
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason=f"Entreprise controversée: {stock.name}"
            )

        industry = (stock.industry or "").lower()
        sector = (stock.sector or "").lower()

        # Tabac
        if self.exclude_tobacco and ("tobacco" in industry or "tobacco" in sector):
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason="Industrie du tabac"
            )

        # Armes/Défense
        if self.exclude_weapons:
            weapon_keywords = ["defense", "weapon", "military", "aerospace & defense"]
            if any(kw in industry or kw in sector for kw in weapon_keywords):
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason="Industrie de l'armement"
                )

        # Jeux d'argent
        if self.exclude_gambling:
            gambling_keywords = ["gambling", "casino", "gaming"]
            if any(kw in industry for kw in gambling_keywords):
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason="Industrie des jeux d'argent"
                )

        # Énergies fossiles
        if self.exclude_fossil_fuels:
            fossil_keywords = ["oil", "gas", "coal", "petroleum"]
            if any(kw in industry for kw in fossil_keywords):
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason="Énergies fossiles"
                )

        return FilterResult(passed=True, filter_name=self.name)

    def _get_config(self) -> dict:
        return {
            "exclude_tobacco": self.exclude_tobacco,
            "exclude_weapons": self.exclude_weapons,
            "exclude_gambling": self.exclude_gambling,
            "exclude_fossil_fuels": self.exclude_fossil_fuels,
            "custom_exclusions": self.custom_exclusions
        }


class FundamentalFilter(BaseFilter):
    """Filtre par critères fondamentaux."""

    def __init__(
        self,
        max_pe: Optional[float] = None,
        min_pe: Optional[float] = None,
        max_peg: Optional[float] = None,
        max_debt_to_equity: Optional[float] = None,
        min_dividend_yield: Optional[float] = None,
        min_roe: Optional[float] = None,
        min_market_cap: Optional[float] = None,  # En millions
        max_market_cap: Optional[float] = None,
        name: str = "Filtre Fondamental",
        enabled: bool = True
    ):
        super().__init__(name, FilterType.FUNDAMENTAL, enabled)
        self.max_pe = max_pe
        self.min_pe = min_pe
        self.max_peg = max_peg
        self.max_debt_to_equity = max_debt_to_equity
        self.min_dividend_yield = min_dividend_yield
        self.min_roe = min_roe
        self.min_market_cap = min_market_cap
        self.max_market_cap = max_market_cap

    def apply(self, stock: StockFilterData) -> FilterResult:
        if not self.enabled:
            return FilterResult(passed=True, filter_name=self.name)

        # P/E
        if stock.pe_ratio is not None:
            if self.max_pe and stock.pe_ratio > self.max_pe:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"P/E trop élevé: {stock.pe_ratio:.1f} > {self.max_pe}"
                )
            if self.min_pe and stock.pe_ratio < self.min_pe:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"P/E trop faible: {stock.pe_ratio:.1f} < {self.min_pe}"
                )

        # PEG
        if self.max_peg and stock.peg_ratio is not None:
            if stock.peg_ratio > self.max_peg:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"PEG trop élevé: {stock.peg_ratio:.2f} > {self.max_peg}"
                )

        # Dette/Equity
        if self.max_debt_to_equity and stock.debt_to_equity is not None:
            if stock.debt_to_equity > self.max_debt_to_equity:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Dette/Equity trop élevé: {stock.debt_to_equity:.2f}"
                )

        # Rendement dividende
        if self.min_dividend_yield and stock.dividend_yield is not None:
            div_pct = stock.dividend_yield * 100 if stock.dividend_yield < 1 else stock.dividend_yield
            if div_pct < self.min_dividend_yield:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Rendement dividende insuffisant: {div_pct:.2f}%"
                )

        # ROE
        if self.min_roe and stock.roe is not None:
            roe_pct = stock.roe * 100 if stock.roe < 1 else stock.roe
            if roe_pct < self.min_roe:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"ROE insuffisant: {roe_pct:.1f}%"
                )

        # Market Cap
        if stock.market_cap is not None:
            if self.min_market_cap and stock.market_cap < self.min_market_cap:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Market Cap trop faible: {stock.market_cap:.0f}M"
                )
            if self.max_market_cap and stock.market_cap > self.max_market_cap:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Market Cap trop élevé: {stock.market_cap:.0f}M"
                )

        return FilterResult(passed=True, filter_name=self.name)

    def _get_config(self) -> dict:
        return {
            "max_pe": self.max_pe,
            "min_pe": self.min_pe,
            "max_peg": self.max_peg,
            "max_debt_to_equity": self.max_debt_to_equity,
            "min_dividend_yield": self.min_dividend_yield,
            "min_roe": self.min_roe,
            "min_market_cap": self.min_market_cap,
            "max_market_cap": self.max_market_cap
        }


class GeographicFilter(BaseFilter):
    """Filtre géographique."""

    # Pays de l'UE/EEE (pour PEA)
    EU_COUNTRIES = [
        "France", "Germany", "Italy", "Spain", "Netherlands", "Belgium",
        "Portugal", "Austria", "Ireland", "Finland", "Luxembourg", "Greece",
        "Denmark", "Sweden", "Poland", "Czech Republic", "Hungary", "Romania",
        "Bulgaria", "Croatia", "Slovakia", "Slovenia", "Estonia", "Latvia",
        "Lithuania", "Cyprus", "Malta", "Norway", "Iceland", "Liechtenstein"
    ]

    def __init__(
        self,
        allowed_countries: Optional[list[str]] = None,
        excluded_countries: Optional[list[str]] = None,
        pea_only: bool = False,
        name: str = "Filtre Géographique",
        enabled: bool = True
    ):
        super().__init__(name, FilterType.GEOGRAPHIC, enabled)
        self.allowed_countries = allowed_countries
        self.excluded_countries = excluded_countries or []
        self.pea_only = pea_only

    def apply(self, stock: StockFilterData) -> FilterResult:
        if not self.enabled:
            return FilterResult(passed=True, filter_name=self.name)

        # Filtre PEA uniquement
        if self.pea_only and not stock.pea_eligible:
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason="Non éligible PEA"
            )

        # Pays exclus
        if stock.country and stock.country in self.excluded_countries:
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason=f"Pays exclu: {stock.country}"
            )

        # Pays autorisés
        if self.allowed_countries and stock.country:
            if stock.country not in self.allowed_countries:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Pays non autorisé: {stock.country}"
                )

        return FilterResult(passed=True, filter_name=self.name)

    def _get_config(self) -> dict:
        return {
            "allowed_countries": self.allowed_countries,
            "excluded_countries": self.excluded_countries,
            "pea_only": self.pea_only
        }


class OwnershipFilter(BaseFilter):
    """Filtre par structure d'actionnariat."""

    def __init__(
        self,
        exclude_state_owned: bool = False,
        max_state_ownership: Optional[float] = None,  # Pourcentage
        exclude_sovereign_funds: bool = False,
        name: str = "Filtre Actionnariat",
        enabled: bool = True
    ):
        super().__init__(name, FilterType.OWNERSHIP, enabled)
        self.exclude_state_owned = exclude_state_owned
        self.max_state_ownership = max_state_ownership
        self.exclude_sovereign_funds = exclude_sovereign_funds

    def apply(self, stock: StockFilterData) -> FilterResult:
        if not self.enabled:
            return FilterResult(passed=True, filter_name=self.name)

        # Exclure entreprises d'État
        if self.exclude_state_owned and stock.state_owned_percentage:
            if stock.state_owned_percentage > 50:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Entreprise d'État ({stock.state_owned_percentage:.1f}%)"
                )

        # Maximum participation État
        if self.max_state_ownership and stock.state_owned_percentage:
            if stock.state_owned_percentage > self.max_state_ownership:
                return FilterResult(
                    passed=False,
                    filter_name=self.name,
                    reason=f"Participation État trop élevée: {stock.state_owned_percentage:.1f}%"
                )

        # Exclure fonds souverains
        if self.exclude_sovereign_funds and stock.sovereign_fund_owned:
            return FilterResult(
                passed=False,
                filter_name=self.name,
                reason="Détenue par un fonds souverain"
            )

        return FilterResult(passed=True, filter_name=self.name)

    def _get_config(self) -> dict:
        return {
            "exclude_state_owned": self.exclude_state_owned,
            "max_state_ownership": self.max_state_ownership,
            "exclude_sovereign_funds": self.exclude_sovereign_funds
        }


class FilterManager:
    """Gestionnaire de filtres."""

    def __init__(self):
        self.filters: list[BaseFilter] = []

    def add_filter(self, filter_obj: BaseFilter) -> None:
        """Ajoute un filtre."""
        self.filters.append(filter_obj)

    def remove_filter(self, name: str) -> bool:
        """Supprime un filtre par son nom."""
        for i, f in enumerate(self.filters):
            if f.name == name:
                self.filters.pop(i)
                return True
        return False

    def enable_filter(self, name: str) -> bool:
        """Active un filtre."""
        for f in self.filters:
            if f.name == name:
                f.enabled = True
                return True
        return False

    def disable_filter(self, name: str) -> bool:
        """Désactive un filtre."""
        for f in self.filters:
            if f.name == name:
                f.enabled = False
                return True
        return False

    def apply_filters(self, stock: StockFilterData) -> tuple[bool, list[FilterResult]]:
        """
        Applique tous les filtres à une action.

        Returns:
            (passed, list[FilterResult])
        """
        results = []
        passed = True

        for filter_obj in self.filters:
            result = filter_obj.apply(stock)
            results.append(result)
            if not result.passed:
                passed = False

        return passed, results

    def filter_stocks(self, stocks: list[StockFilterData]) -> list[StockFilterData]:
        """Filtre une liste d'actions."""
        filtered = []
        for stock in stocks:
            passed, _ = self.apply_filters(stock)
            if passed:
                filtered.append(stock)
        return filtered

    def get_filter_summary(self, stocks: list[StockFilterData]) -> dict:
        """Génère un résumé des filtres appliqués."""
        summary = {
            "total_stocks": len(stocks),
            "passed": 0,
            "rejected": 0,
            "by_filter": {}
        }

        for filter_obj in self.filters:
            summary["by_filter"][filter_obj.name] = {"rejected": 0, "reasons": []}

        for stock in stocks:
            passed, results = self.apply_filters(stock)
            if passed:
                summary["passed"] += 1
            else:
                summary["rejected"] += 1
                for result in results:
                    if not result.passed:
                        summary["by_filter"][result.filter_name]["rejected"] += 1
                        summary["by_filter"][result.filter_name]["reasons"].append(
                            f"{stock.ticker}: {result.reason}"
                        )

        return summary

    def to_json(self) -> str:
        """Sérialise tous les filtres en JSON."""
        return json.dumps([f.to_dict() for f in self.filters], indent=2)

    def load_default_filters(self) -> None:
        """Charge les filtres par défaut."""
        self.filters = [
            SectorFilter(),
            EthicalFilter(),
            FundamentalFilter(
                max_pe=50,
                max_peg=3,
                max_debt_to_equity=2,
                min_market_cap=1000  # 1 milliard
            ),
            GeographicFilter()
        ]


# Instance singleton
filter_manager = FilterManager()


def main():
    """Test du système de filtres."""
    # Charger les filtres par défaut
    filter_manager.load_default_filters()

    # Créer des actions de test
    test_stocks = [
        StockFilterData(
            ticker="AAPL",
            name="Apple Inc",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            market_cap=3000000,
            pe_ratio=28,
            peg_ratio=2.1,
            debt_to_equity=1.5
        ),
        StockFilterData(
            ticker="PM",
            name="Philip Morris",
            sector="Consumer Staples",
            industry="Tobacco",
            country="United States",
            market_cap=150000,
            pe_ratio=15
        ),
        StockFilterData(
            ticker="MC.PA",
            name="LVMH",
            sector="Consumer Discretionary",
            industry="Luxury Goods",
            country="France",
            market_cap=400000,
            pe_ratio=25,
            pea_eligible=True
        ),
        StockFilterData(
            ticker="LMT",
            name="Lockheed Martin",
            sector="Aerospace & Defense",
            industry="Defense",
            country="United States",
            market_cap=120000,
            pe_ratio=18
        )
    ]

    print("=== Test des Filtres ===\n")

    for stock in test_stocks:
        passed, results = filter_manager.apply_filters(stock)
        status = "✓ PASS" if passed else "✗ REJECT"
        print(f"{stock.ticker} ({stock.name}): {status}")

        for result in results:
            if not result.passed:
                print(f"  - {result.filter_name}: {result.reason}")

        print()

    # Résumé
    print("=== Résumé ===")
    summary = filter_manager.get_filter_summary(test_stocks)
    print(f"Total: {summary['total_stocks']}")
    print(f"Acceptés: {summary['passed']}")
    print(f"Rejetés: {summary['rejected']}")


if __name__ == "__main__":
    main()
