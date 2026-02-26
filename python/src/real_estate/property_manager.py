"""
Gestionnaire de biens immobiliers pour Stock Advisor.
Suivi des biens, revenus locatifs, crédits, rendement.
"""
import json
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import math


class PropertyType(Enum):
    """Types de biens immobiliers."""
    APARTMENT = "appartement"
    HOUSE = "maison"
    STUDIO = "studio"
    PARKING = "parking"
    COMMERCIAL = "commercial"
    LAND = "terrain"
    OTHER = "autre"


class PropertyUsage(Enum):
    """Usage du bien."""
    PRIMARY_RESIDENCE = "residence_principale"
    SECONDARY_RESIDENCE = "residence_secondaire"
    RENTAL = "locatif"
    COMMERCIAL = "commercial"
    MIXED = "mixte"


@dataclass
class Mortgage:
    """Crédit immobilier associé."""
    id: Optional[int] = None
    property_id: int = 0
    bank: str = ""
    initial_amount: float = 0
    remaining_amount: float = 0
    interest_rate: float = 0  # Taux annuel
    monthly_payment: float = 0
    start_date: str = ""  # YYYY-MM-DD
    duration_months: int = 0
    insurance_rate: float = 0  # Taux assurance annuel

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Mortgage':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Property:
    """Représente un bien immobilier."""
    id: Optional[int] = None
    name: str = ""
    property_type: PropertyType = PropertyType.APARTMENT
    usage: PropertyUsage = PropertyUsage.RENTAL
    address: str = ""
    city: str = ""
    postal_code: str = ""
    area_sqm: float = 0  # Surface en m²
    rooms: int = 0
    purchase_date: str = ""  # YYYY-MM-DD
    purchase_price: float = 0
    notary_fees: float = 0
    renovation_cost: float = 0
    current_value: float = 0  # Estimation actuelle
    monthly_rent: float = 0  # Loyer mensuel (si locatif)
    monthly_charges: float = 0  # Charges copropriété
    property_tax: float = 0  # Taxe foncière annuelle
    management_fees_pct: float = 0  # Frais de gestion (%)
    vacancy_rate: float = 5  # Taux de vacance (%)
    notes: str = ""
    created_at: str = ""
    mortgages: List[Mortgage] = field(default_factory=list)

    @property
    def total_investment(self) -> float:
        """Coût total d'acquisition."""
        return self.purchase_price + self.notary_fees + self.renovation_cost

    @property
    def annual_rent_gross(self) -> float:
        """Loyer annuel brut."""
        return self.monthly_rent * 12

    @property
    def annual_rent_net(self) -> float:
        """Loyer annuel net de charges et vacance."""
        gross = self.annual_rent_gross
        vacancy = gross * (self.vacancy_rate / 100)
        charges = self.monthly_charges * 12
        management = gross * (self.management_fees_pct / 100)
        return gross - vacancy - charges - management - self.property_tax

    @property
    def gross_yield(self) -> float:
        """Rendement brut (%)."""
        if self.total_investment == 0:
            return 0
        return (self.annual_rent_gross / self.total_investment) * 100

    @property
    def net_yield(self) -> float:
        """Rendement net (%)."""
        if self.total_investment == 0:
            return 0
        return (self.annual_rent_net / self.total_investment) * 100

    @property
    def monthly_mortgage_total(self) -> float:
        """Total mensualités crédit."""
        return sum(m.monthly_payment for m in self.mortgages)

    @property
    def cashflow_monthly(self) -> float:
        """Cash-flow mensuel."""
        return self.monthly_rent - self.monthly_charges - self.monthly_mortgage_total - (self.property_tax / 12)

    @property
    def price_per_sqm(self) -> float:
        """Prix au m²."""
        if self.area_sqm == 0:
            return 0
        return self.purchase_price / self.area_sqm

    @property
    def capital_gain(self) -> float:
        """Plus-value latente."""
        return self.current_value - self.total_investment

    @property
    def capital_gain_pct(self) -> float:
        """Plus-value latente en %."""
        if self.total_investment == 0:
            return 0
        return (self.capital_gain / self.total_investment) * 100

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['property_type'] = self.property_type.value
        d['usage'] = self.usage.value
        d['mortgages'] = [m.to_dict() for m in self.mortgages]
        # Ajouter les propriétés calculées
        d['total_investment'] = self.total_investment
        d['gross_yield'] = self.gross_yield
        d['net_yield'] = self.net_yield
        d['cashflow_monthly'] = self.cashflow_monthly
        d['capital_gain'] = self.capital_gain
        d['capital_gain_pct'] = self.capital_gain_pct
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Property':
        mortgages = [Mortgage.from_dict(m) for m in data.pop('mortgages', [])]
        # Ignorer les propriétés calculées
        for key in ['total_investment', 'gross_yield', 'net_yield', 'cashflow_monthly',
                    'capital_gain', 'capital_gain_pct', 'annual_rent_gross', 'annual_rent_net',
                    'monthly_mortgage_total', 'price_per_sqm']:
            data.pop(key, None)

        data['property_type'] = PropertyType(data.get('property_type', 'appartement'))
        data['usage'] = PropertyUsage(data.get('usage', 'locatif'))

        prop = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        prop.mortgages = mortgages
        return prop


class PropertyManager:
    """Gestionnaire de patrimoine immobilier."""

    def __init__(self, db_path: str = "data/real_estate.db"):
        """Initialise le gestionnaire."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                property_type TEXT NOT NULL,
                usage TEXT NOT NULL,
                address TEXT,
                city TEXT,
                postal_code TEXT,
                area_sqm REAL,
                rooms INTEGER,
                purchase_date TEXT,
                purchase_price REAL,
                notary_fees REAL,
                renovation_cost REAL,
                current_value REAL,
                monthly_rent REAL,
                monthly_charges REAL,
                property_tax REAL,
                management_fees_pct REAL,
                vacancy_rate REAL,
                notes TEXT,
                created_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mortgages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER NOT NULL,
                bank TEXT,
                initial_amount REAL,
                remaining_amount REAL,
                interest_rate REAL,
                monthly_payment REAL,
                start_date TEXT,
                duration_months INTEGER,
                insurance_rate REAL,
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rental_income (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT DEFAULT 'rent',
                notes TEXT,
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS property_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                description TEXT,
                FOREIGN KEY (property_id) REFERENCES properties (id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_property(self, prop: Property) -> Property:
        """Ajoute un bien immobilier."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        prop.created_at = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO properties (name, property_type, usage, address, city, postal_code,
                                   area_sqm, rooms, purchase_date, purchase_price, notary_fees,
                                   renovation_cost, current_value, monthly_rent, monthly_charges,
                                   property_tax, management_fees_pct, vacancy_rate, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (prop.name, prop.property_type.value, prop.usage.value, prop.address,
              prop.city, prop.postal_code, prop.area_sqm, prop.rooms, prop.purchase_date,
              prop.purchase_price, prop.notary_fees, prop.renovation_cost, prop.current_value,
              prop.monthly_rent, prop.monthly_charges, prop.property_tax,
              prop.management_fees_pct, prop.vacancy_rate, prop.notes, prop.created_at))

        prop.id = cursor.lastrowid

        # Ajouter les crédits
        for mortgage in prop.mortgages:
            mortgage.property_id = prop.id
            self._add_mortgage(cursor, mortgage)

        conn.commit()
        conn.close()

        return prop

    def _add_mortgage(self, cursor, mortgage: Mortgage):
        """Ajoute un crédit (utilise un curseur existant)."""
        cursor.execute('''
            INSERT INTO mortgages (property_id, bank, initial_amount, remaining_amount,
                                  interest_rate, monthly_payment, start_date, duration_months, insurance_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (mortgage.property_id, mortgage.bank, mortgage.initial_amount,
              mortgage.remaining_amount, mortgage.interest_rate, mortgage.monthly_payment,
              mortgage.start_date, mortgage.duration_months, mortgage.insurance_rate))
        mortgage.id = cursor.lastrowid

    def get_property(self, property_id: int) -> Optional[Property]:
        """Récupère un bien par ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM properties WHERE id = ?', (property_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        prop = self._row_to_property(row)

        # Récupérer les crédits
        cursor.execute('SELECT * FROM mortgages WHERE property_id = ?', (property_id,))
        for mortgage_row in cursor.fetchall():
            prop.mortgages.append(self._row_to_mortgage(mortgage_row))

        conn.close()
        return prop

    def get_all_properties(self) -> List[Property]:
        """Récupère tous les biens."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM properties ORDER BY created_at DESC')
        rows = cursor.fetchall()

        properties = []
        for row in rows:
            prop = self._row_to_property(row)

            cursor.execute('SELECT * FROM mortgages WHERE property_id = ?', (prop.id,))
            for mortgage_row in cursor.fetchall():
                prop.mortgages.append(self._row_to_mortgage(mortgage_row))

            properties.append(prop)

        conn.close()
        return properties

    def _row_to_property(self, row) -> Property:
        """Convertit une ligne SQL en Property."""
        return Property(
            id=row[0],
            name=row[1],
            property_type=PropertyType(row[2]),
            usage=PropertyUsage(row[3]),
            address=row[4] or '',
            city=row[5] or '',
            postal_code=row[6] or '',
            area_sqm=row[7] or 0,
            rooms=row[8] or 0,
            purchase_date=row[9] or '',
            purchase_price=row[10] or 0,
            notary_fees=row[11] or 0,
            renovation_cost=row[12] or 0,
            current_value=row[13] or 0,
            monthly_rent=row[14] or 0,
            monthly_charges=row[15] or 0,
            property_tax=row[16] or 0,
            management_fees_pct=row[17] or 0,
            vacancy_rate=row[18] or 5,
            notes=row[19] or '',
            created_at=row[20] or ''
        )

    def _row_to_mortgage(self, row) -> Mortgage:
        """Convertit une ligne SQL en Mortgage."""
        return Mortgage(
            id=row[0],
            property_id=row[1],
            bank=row[2] or '',
            initial_amount=row[3] or 0,
            remaining_amount=row[4] or 0,
            interest_rate=row[5] or 0,
            monthly_payment=row[6] or 0,
            start_date=row[7] or '',
            duration_months=row[8] or 0,
            insurance_rate=row[9] or 0
        )

    def update_property(self, prop: Property) -> bool:
        """Met à jour un bien."""
        if not prop.id:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE properties SET name = ?, property_type = ?, usage = ?, address = ?,
                city = ?, postal_code = ?, area_sqm = ?, rooms = ?, purchase_date = ?,
                purchase_price = ?, notary_fees = ?, renovation_cost = ?, current_value = ?,
                monthly_rent = ?, monthly_charges = ?, property_tax = ?, management_fees_pct = ?,
                vacancy_rate = ?, notes = ?
            WHERE id = ?
        ''', (prop.name, prop.property_type.value, prop.usage.value, prop.address,
              prop.city, prop.postal_code, prop.area_sqm, prop.rooms, prop.purchase_date,
              prop.purchase_price, prop.notary_fees, prop.renovation_cost, prop.current_value,
              prop.monthly_rent, prop.monthly_charges, prop.property_tax,
              prop.management_fees_pct, prop.vacancy_rate, prop.notes, prop.id))

        conn.commit()
        conn.close()
        return True

    def delete_property(self, property_id: int) -> bool:
        """Supprime un bien et ses données associées."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM mortgages WHERE property_id = ?', (property_id,))
        cursor.execute('DELETE FROM rental_income WHERE property_id = ?', (property_id,))
        cursor.execute('DELETE FROM property_expenses WHERE property_id = ?', (property_id,))
        cursor.execute('DELETE FROM properties WHERE id = ?', (property_id,))

        conn.commit()
        conn.close()
        return True

    def add_rental_income(self, property_id: int, amount: float,
                          date: str = None, income_type: str = 'rent',
                          notes: str = '') -> int:
        """Enregistre un revenu locatif."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        date = date or datetime.now().strftime('%Y-%m-%d')

        cursor.execute('''
            INSERT INTO rental_income (property_id, date, amount, type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (property_id, date, amount, income_type, notes))

        income_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return income_id

    def add_expense(self, property_id: int, amount: float, category: str,
                    date: str = None, description: str = '') -> int:
        """Enregistre une dépense."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        date = date or datetime.now().strftime('%Y-%m-%d')

        cursor.execute('''
            INSERT INTO property_expenses (property_id, date, amount, category, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (property_id, date, amount, category, description))

        expense_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return expense_id

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Retourne un résumé du patrimoine immobilier."""
        properties = self.get_all_properties()

        if not properties:
            return {
                'total_value': 0,
                'total_investment': 0,
                'total_debt': 0,
                'net_worth': 0,
                'monthly_rent': 0,
                'monthly_cashflow': 0,
                'avg_gross_yield': 0,
                'avg_net_yield': 0,
                'count': 0
            }

        total_value = sum(p.current_value for p in properties)
        total_investment = sum(p.total_investment for p in properties)
        total_debt = sum(sum(m.remaining_amount for m in p.mortgages) for p in properties)
        monthly_rent = sum(p.monthly_rent for p in properties if p.usage == PropertyUsage.RENTAL)
        monthly_cashflow = sum(p.cashflow_monthly for p in properties if p.usage == PropertyUsage.RENTAL)

        rental_props = [p for p in properties if p.usage == PropertyUsage.RENTAL and p.total_investment > 0]
        avg_gross = sum(p.gross_yield for p in rental_props) / len(rental_props) if rental_props else 0
        avg_net = sum(p.net_yield for p in rental_props) / len(rental_props) if rental_props else 0

        return {
            'total_value': total_value,
            'total_investment': total_investment,
            'total_debt': total_debt,
            'net_worth': total_value - total_debt,
            'monthly_rent': monthly_rent,
            'monthly_cashflow': monthly_cashflow,
            'avg_gross_yield': avg_gross,
            'avg_net_yield': avg_net,
            'count': len(properties),
            'capital_gain': total_value - total_investment,
            'capital_gain_pct': ((total_value - total_investment) / total_investment * 100) if total_investment > 0 else 0
        }

    def calculate_mortgage_payment(self, principal: float, annual_rate: float,
                                    years: int, insurance_rate: float = 0) -> Dict[str, float]:
        """
        Calcule la mensualité d'un crédit.

        Args:
            principal: Montant emprunté
            annual_rate: Taux annuel (ex: 3.5 pour 3.5%)
            years: Durée en années
            insurance_rate: Taux assurance annuel (%)

        Returns:
            Dict avec monthly_payment, total_interest, total_cost
        """
        monthly_rate = annual_rate / 100 / 12
        n_payments = years * 12

        if monthly_rate == 0:
            monthly_principal = principal / n_payments
        else:
            monthly_principal = principal * (monthly_rate * (1 + monthly_rate) ** n_payments) / \
                               ((1 + monthly_rate) ** n_payments - 1)

        monthly_insurance = principal * (insurance_rate / 100) / 12
        monthly_total = monthly_principal + monthly_insurance

        total_interest = (monthly_principal * n_payments) - principal
        total_insurance = monthly_insurance * n_payments
        total_cost = principal + total_interest + total_insurance

        return {
            'monthly_payment': monthly_total,
            'monthly_principal': monthly_principal,
            'monthly_insurance': monthly_insurance,
            'total_interest': total_interest,
            'total_insurance': total_insurance,
            'total_cost': total_cost,
            'n_payments': n_payments
        }


# Test
if __name__ == "__main__":
    print("=== Test Property Manager ===\n")

    manager = PropertyManager("test_real_estate.db")

    # Créer un bien
    prop = Property(
        name="Studio Paris 11",
        property_type=PropertyType.STUDIO,
        usage=PropertyUsage.RENTAL,
        address="15 rue de la Roquette",
        city="Paris",
        postal_code="75011",
        area_sqm=25,
        rooms=1,
        purchase_date="2023-01-15",
        purchase_price=180000,
        notary_fees=14400,  # 8%
        renovation_cost=5000,
        current_value=195000,
        monthly_rent=850,
        monthly_charges=80,
        property_tax=600,
        management_fees_pct=7,
        vacancy_rate=5
    )

    # Ajouter un crédit
    mortgage = Mortgage(
        bank="BNP Paribas",
        initial_amount=144000,  # 80% LTV
        remaining_amount=138000,
        interest_rate=3.2,
        monthly_payment=695,
        start_date="2023-02-01",
        duration_months=240,
        insurance_rate=0.36
    )
    prop.mortgages.append(mortgage)

    # Sauvegarder
    prop = manager.add_property(prop)
    print(f"Bien créé: {prop.name} (ID: {prop.id})")

    # Afficher les métriques
    print(f"\n=== Métriques ===")
    print(f"Investissement total: {prop.total_investment:,.0f}€")
    print(f"Valeur actuelle: {prop.current_value:,.0f}€")
    print(f"Plus-value: {prop.capital_gain:,.0f}€ ({prop.capital_gain_pct:.1f}%)")
    print(f"Rendement brut: {prop.gross_yield:.2f}%")
    print(f"Rendement net: {prop.net_yield:.2f}%")
    print(f"Cash-flow mensuel: {prop.cashflow_monthly:,.0f}€")

    # Résumé portefeuille
    summary = manager.get_portfolio_summary()
    print(f"\n=== Résumé Patrimoine ===")
    print(f"Valeur totale: {summary['total_value']:,.0f}€")
    print(f"Dette totale: {summary['total_debt']:,.0f}€")
    print(f"Patrimoine net: {summary['net_worth']:,.0f}€")

    # Nettoyage
    import os
    os.remove("test_real_estate.db")
    print("\n✅ Test terminé")
