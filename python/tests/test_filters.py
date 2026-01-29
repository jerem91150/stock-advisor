"""
Tests pour le système de filtres.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.filters.base import (
    FilterManager, StockFilterData, FilterResult, FilterType,
    SectorFilter, EthicalFilter, FundamentalFilter, GeographicFilter, OwnershipFilter
)


class TestStockFilterData:
    """Tests pour la structure StockFilterData."""

    def test_create_filter_data(self):
        """Test de création de données de filtre."""
        data = StockFilterData(
            ticker="AAPL",
            name="Apple Inc",
            sector="Technology",
            industry="Consumer Electronics",
            country="United States",
            market_cap=3000000,
            pea_eligible=False
        )

        assert data.ticker == "AAPL"
        assert data.name == "Apple Inc"
        assert data.pea_eligible is False

    def test_filter_data_defaults(self):
        """Test des valeurs par défaut."""
        data = StockFilterData(ticker="TEST", name="Test Corp")

        assert data.sector is None
        assert data.pe_ratio is None
        assert data.pea_eligible is False
        assert data.major_shareholders == []


class TestSectorFilter:
    """Tests pour le filtre sectoriel."""

    def test_exclude_tobacco(self):
        """Test exclusion du tabac."""
        filter_obj = SectorFilter(excluded_industries=["Tobacco"])
        stock = StockFilterData(
            ticker="PM",
            name="Philip Morris",
            industry="Tobacco"
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Tobacco" in result.reason

    def test_exclude_defense(self):
        """Test exclusion de la défense."""
        filter_obj = SectorFilter(excluded_sectors=["Aerospace & Defense"])
        stock = StockFilterData(
            ticker="LMT",
            name="Lockheed Martin",
            sector="Aerospace & Defense"
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Defense" in result.reason

    def test_pass_technology(self):
        """Test passage d'une action tech."""
        filter_obj = SectorFilter()
        stock = StockFilterData(
            ticker="AAPL",
            name="Apple",
            sector="Technology",
            industry="Consumer Electronics"
        )

        result = filter_obj.apply(stock)
        assert result.passed

    def test_disabled_filter(self):
        """Test filtre désactivé."""
        filter_obj = SectorFilter(enabled=False)
        stock = StockFilterData(
            ticker="PM",
            name="Philip Morris",
            industry="Tobacco"
        )

        result = filter_obj.apply(stock)
        assert result.passed  # Filtre désactivé = tout passe

    def test_custom_exclusions(self):
        """Test exclusions personnalisées."""
        filter_obj = SectorFilter(
            excluded_sectors=["Energy"],
            excluded_industries=["Oil & Gas"]
        )
        stock = StockFilterData(
            ticker="XOM",
            name="Exxon",
            sector="Energy",
            industry="Oil & Gas"
        )

        result = filter_obj.apply(stock)
        assert not result.passed


class TestEthicalFilter:
    """Tests pour le filtre éthique."""

    def test_exclude_controversial_ticker(self):
        """Test exclusion d'un ticker controversé."""
        filter_obj = EthicalFilter()
        stock = StockFilterData(
            ticker="PM",  # Philip Morris dans la liste
            name="Philip Morris International"
        )

        result = filter_obj.apply(stock)
        assert not result.passed

    def test_custom_exclusion(self):
        """Test exclusion personnalisée."""
        filter_obj = EthicalFilter(custom_exclusions=["TEST"])
        stock = StockFilterData(ticker="TEST", name="Test Corp")

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Exclu manuellement" in result.reason

    def test_exclude_gambling(self):
        """Test exclusion des jeux d'argent."""
        filter_obj = EthicalFilter(exclude_gambling=True)
        stock = StockFilterData(
            ticker="MGM",
            name="MGM Resorts",
            industry="Casinos & Gaming"
        )

        result = filter_obj.apply(stock)
        assert not result.passed

    def test_include_gambling_when_disabled(self):
        """Test inclusion des jeux d'argent quand désactivé."""
        filter_obj = EthicalFilter(exclude_gambling=False)
        stock = StockFilterData(
            ticker="MGM",
            name="MGM Resorts",
            industry="Casinos & Gaming"
        )

        result = filter_obj.apply(stock)
        assert result.passed

    def test_exclude_fossil_fuels(self):
        """Test exclusion des énergies fossiles."""
        filter_obj = EthicalFilter(exclude_fossil_fuels=True)
        stock = StockFilterData(
            ticker="XOM",
            name="Exxon Mobil",
            industry="Oil & Gas"
        )

        result = filter_obj.apply(stock)
        assert not result.passed

    def test_pass_clean_company(self):
        """Test passage d'une entreprise propre."""
        filter_obj = EthicalFilter()
        stock = StockFilterData(
            ticker="AAPL",
            name="Apple Inc",
            sector="Technology",
            industry="Consumer Electronics"
        )

        result = filter_obj.apply(stock)
        assert result.passed


class TestFundamentalFilter:
    """Tests pour le filtre fondamental."""

    def test_filter_high_pe(self):
        """Test filtre P/E trop élevé."""
        filter_obj = FundamentalFilter(max_pe=30)
        stock = StockFilterData(
            ticker="HIGH",
            name="High PE Corp",
            pe_ratio=50.0
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "P/E trop élevé" in result.reason

    def test_filter_low_pe(self):
        """Test filtre P/E trop bas."""
        filter_obj = FundamentalFilter(min_pe=5)
        stock = StockFilterData(
            ticker="LOW",
            name="Low PE Corp",
            pe_ratio=3.0
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "P/E trop faible" in result.reason

    def test_filter_high_peg(self):
        """Test filtre PEG trop élevé."""
        filter_obj = FundamentalFilter(max_peg=2.0)
        stock = StockFilterData(
            ticker="TEST",
            name="Test Corp",
            peg_ratio=3.5
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "PEG trop élevé" in result.reason

    def test_filter_high_debt(self):
        """Test filtre dette trop élevée."""
        filter_obj = FundamentalFilter(max_debt_to_equity=1.5)
        stock = StockFilterData(
            ticker="DEBT",
            name="Debt Corp",
            debt_to_equity=2.5
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Dette/Equity trop élevé" in result.reason

    def test_filter_low_dividend(self):
        """Test filtre dividende insuffisant."""
        filter_obj = FundamentalFilter(min_dividend_yield=2.0)
        stock = StockFilterData(
            ticker="LOW",
            name="Low Div Corp",
            dividend_yield=0.005  # 0.5%
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "dividende insuffisant" in result.reason

    def test_filter_low_roe(self):
        """Test filtre ROE insuffisant."""
        filter_obj = FundamentalFilter(min_roe=15)
        stock = StockFilterData(
            ticker="LOW",
            name="Low ROE Corp",
            roe=0.08  # 8%
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "ROE insuffisant" in result.reason

    def test_filter_small_market_cap(self):
        """Test filtre market cap trop petite."""
        filter_obj = FundamentalFilter(min_market_cap=1000)
        stock = StockFilterData(
            ticker="SMALL",
            name="Small Corp",
            market_cap=500
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Market Cap trop faible" in result.reason

    def test_filter_large_market_cap(self):
        """Test filtre market cap trop grande."""
        filter_obj = FundamentalFilter(max_market_cap=100000)
        stock = StockFilterData(
            ticker="MEGA",
            name="Mega Corp",
            market_cap=500000
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Market Cap trop élevé" in result.reason

    def test_pass_all_criteria(self):
        """Test passage de tous les critères."""
        filter_obj = FundamentalFilter(
            max_pe=30,
            max_peg=2.0,
            max_debt_to_equity=1.5,
            min_market_cap=1000
        )
        stock = StockFilterData(
            ticker="GOOD",
            name="Good Corp",
            pe_ratio=20,
            peg_ratio=1.5,
            debt_to_equity=0.8,
            market_cap=50000
        )

        result = filter_obj.apply(stock)
        assert result.passed


class TestGeographicFilter:
    """Tests pour le filtre géographique."""

    def test_pea_only(self):
        """Test PEA uniquement."""
        filter_obj = GeographicFilter(pea_only=True)

        stock_pea = StockFilterData(
            ticker="MC.PA",
            name="LVMH",
            country="France",
            pea_eligible=True
        )
        stock_cto = StockFilterData(
            ticker="AAPL",
            name="Apple",
            country="United States",
            pea_eligible=False
        )

        assert filter_obj.apply(stock_pea).passed
        assert not filter_obj.apply(stock_cto).passed

    def test_excluded_country(self):
        """Test pays exclu."""
        filter_obj = GeographicFilter(excluded_countries=["China"])
        stock = StockFilterData(
            ticker="BABA",
            name="Alibaba",
            country="China"
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Pays exclu" in result.reason

    def test_allowed_countries(self):
        """Test pays autorisés uniquement."""
        filter_obj = GeographicFilter(allowed_countries=["France", "Germany"])

        stock_fr = StockFilterData(ticker="MC.PA", name="LVMH", country="France")
        stock_us = StockFilterData(ticker="AAPL", name="Apple", country="United States")

        assert filter_obj.apply(stock_fr).passed
        assert not filter_obj.apply(stock_us).passed


class TestOwnershipFilter:
    """Tests pour le filtre d'actionnariat."""

    def test_exclude_state_owned(self):
        """Test exclusion entreprises d'État."""
        filter_obj = OwnershipFilter(exclude_state_owned=True)
        stock = StockFilterData(
            ticker="STATE",
            name="State Corp",
            state_owned_percentage=60.0
        )

        result = filter_obj.apply(stock)
        assert not result.passed
        assert "Entreprise d'État" in result.reason

    def test_max_state_ownership(self):
        """Test seuil max participation État."""
        filter_obj = OwnershipFilter(max_state_ownership=20.0)
        stock = StockFilterData(
            ticker="PART",
            name="Partial State Corp",
            state_owned_percentage=35.0
        )

        result = filter_obj.apply(stock)
        assert not result.passed

    def test_exclude_sovereign_funds(self):
        """Test exclusion fonds souverains."""
        filter_obj = OwnershipFilter(exclude_sovereign_funds=True)
        stock = StockFilterData(
            ticker="SOV",
            name="Sovereign Held Corp",
            sovereign_fund_owned=True
        )

        result = filter_obj.apply(stock)
        assert not result.passed


class TestFilterManager:
    """Tests pour le gestionnaire de filtres."""

    def test_add_filter(self):
        """Test ajout de filtre."""
        manager = FilterManager()
        filter_obj = SectorFilter()

        manager.add_filter(filter_obj)
        assert len(manager.filters) == 1

    def test_remove_filter(self):
        """Test suppression de filtre."""
        manager = FilterManager()
        filter_obj = SectorFilter(name="Test Filter")

        manager.add_filter(filter_obj)
        assert manager.remove_filter("Test Filter")
        assert len(manager.filters) == 0

    def test_enable_disable_filter(self):
        """Test activation/désactivation de filtre."""
        manager = FilterManager()
        filter_obj = SectorFilter(name="Test", enabled=True)
        manager.add_filter(filter_obj)

        manager.disable_filter("Test")
        assert not manager.filters[0].enabled

        manager.enable_filter("Test")
        assert manager.filters[0].enabled

    def test_apply_multiple_filters(self, sample_stock_filter_data):
        """Test application de plusieurs filtres."""
        manager = FilterManager()
        manager.add_filter(EthicalFilter())
        manager.add_filter(FundamentalFilter(max_pe=30, min_market_cap=1000))

        # AAPL devrait passer
        passed, results = manager.apply_filters(sample_stock_filter_data[0])
        assert passed

        # PM (tabac) ne devrait pas passer
        passed, results = manager.apply_filters(sample_stock_filter_data[1])
        assert not passed

    def test_filter_stocks_list(self, sample_stock_filter_data):
        """Test filtrage d'une liste d'actions."""
        manager = FilterManager()
        manager.add_filter(EthicalFilter())
        manager.add_filter(FundamentalFilter(max_pe=30, min_market_cap=1000))

        filtered = manager.filter_stocks(sample_stock_filter_data)

        # Devrait exclure PM (tabac), LMT (défense), TINY (small cap)
        assert len(filtered) < len(sample_stock_filter_data)

        # Vérifier que les exclus ne sont pas dans la liste
        tickers = [s.ticker for s in filtered]
        assert "PM" not in tickers  # Tabac
        assert "LMT" not in tickers  # Défense

    def test_get_filter_summary(self, sample_stock_filter_data):
        """Test résumé des filtres."""
        manager = FilterManager()
        manager.add_filter(EthicalFilter())

        summary = manager.get_filter_summary(sample_stock_filter_data)

        assert "total_stocks" in summary
        assert "passed" in summary
        assert "rejected" in summary
        assert summary["total_stocks"] == len(sample_stock_filter_data)
        assert summary["passed"] + summary["rejected"] == summary["total_stocks"]

    def test_load_default_filters(self):
        """Test chargement des filtres par défaut."""
        manager = FilterManager()
        manager.load_default_filters()

        assert len(manager.filters) > 0

        # Vérifier qu'on a les types de filtres attendus
        filter_types = [f.filter_type for f in manager.filters]
        assert FilterType.SECTORAL in filter_types
        assert FilterType.ETHICAL in filter_types
        assert FilterType.FUNDAMENTAL in filter_types

    def test_to_json(self):
        """Test sérialisation JSON."""
        manager = FilterManager()
        manager.add_filter(SectorFilter())

        json_str = manager.to_json()
        assert "Filtre Sectoriel" in json_str
        assert "sectoral" in json_str


class TestFilterResult:
    """Tests pour la structure FilterResult."""

    def test_passed_result(self):
        """Test résultat passé."""
        result = FilterResult(passed=True, filter_name="Test")

        assert result.passed
        assert result.filter_name == "Test"
        assert result.reason is None

    def test_failed_result(self):
        """Test résultat échoué."""
        result = FilterResult(
            passed=False,
            filter_name="Test",
            reason="Critère non respecté"
        )

        assert not result.passed
        assert result.reason == "Critère non respecté"
