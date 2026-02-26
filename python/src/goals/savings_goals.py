"""
Gestionnaire d'objectifs d'épargne pour Stock Advisor.
Définir, suivre et projeter les objectifs financiers.
"""
import json
import sqlite3
from dataclasses import dataclass, asdict, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any
import math


class GoalStatus(Enum):
    """Statut d'un objectif."""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class GoalCategory(Enum):
    """Catégories d'objectifs."""
    EMERGENCY_FUND = "fonds_urgence"
    RETIREMENT = "retraite"
    HOUSE = "immobilier"
    TRAVEL = "voyage"
    EDUCATION = "education"
    CAR = "voiture"
    WEDDING = "mariage"
    INVESTMENT = "investissement"
    OTHER = "autre"


@dataclass
class SavingsGoal:
    """Représente un objectif d'épargne."""
    id: Optional[int] = None
    name: str = ""
    category: GoalCategory = GoalCategory.OTHER
    target_amount: float = 0
    current_amount: float = 0
    target_date: str = ""  # YYYY-MM-DD
    monthly_contribution: float = 0
    priority: int = 1  # 1 = haute, 5 = basse
    status: GoalStatus = GoalStatus.ACTIVE
    color: str = "#3498db"  # Couleur pour l'affichage
    icon: str = "🎯"
    notes: str = ""
    created_at: str = ""
    linked_portfolio_id: Optional[int] = None  # Lier à un portefeuille

    @property
    def progress_pct(self) -> float:
        """Pourcentage de progression."""
        if self.target_amount == 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)

    @property
    def remaining_amount(self) -> float:
        """Montant restant à atteindre."""
        return max(0, self.target_amount - self.current_amount)

    @property
    def days_remaining(self) -> int:
        """Jours restants avant la date cible."""
        if not self.target_date:
            return -1
        target = datetime.strptime(self.target_date, '%Y-%m-%d').date()
        return (target - date.today()).days

    @property
    def months_remaining(self) -> float:
        """Mois restants avant la date cible."""
        days = self.days_remaining
        if days < 0:
            return 0
        return days / 30.44

    @property
    def required_monthly(self) -> float:
        """Versement mensuel requis pour atteindre l'objectif."""
        months = self.months_remaining
        if months <= 0:
            return self.remaining_amount
        return self.remaining_amount / months

    @property
    def is_on_track(self) -> bool:
        """Vérifie si on est sur la bonne trajectoire."""
        if self.monthly_contribution <= 0:
            return False
        return self.monthly_contribution >= self.required_monthly * 0.95

    @property
    def projected_completion_date(self) -> Optional[str]:
        """Date estimée de complétion avec les versements actuels."""
        if self.monthly_contribution <= 0:
            return None
        months_needed = self.remaining_amount / self.monthly_contribution
        completion = date.today() + timedelta(days=months_needed * 30.44)
        return completion.strftime('%Y-%m-%d')

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['category'] = self.category.value
        d['status'] = self.status.value
        d['progress_pct'] = self.progress_pct
        d['remaining_amount'] = self.remaining_amount
        d['days_remaining'] = self.days_remaining
        d['required_monthly'] = self.required_monthly
        d['is_on_track'] = self.is_on_track
        d['projected_completion_date'] = self.projected_completion_date
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'SavingsGoal':
        # Ignorer les propriétés calculées
        for key in ['progress_pct', 'remaining_amount', 'days_remaining',
                    'required_monthly', 'is_on_track', 'projected_completion_date', 'months_remaining']:
            data.pop(key, None)

        data['category'] = GoalCategory(data.get('category', 'autre'))
        data['status'] = GoalStatus(data.get('status', 'active'))

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class GoalContribution:
    """Un versement vers un objectif."""
    id: Optional[int] = None
    goal_id: int = 0
    date: str = ""
    amount: float = 0
    notes: str = ""


class SavingsGoalManager:
    """Gestionnaire des objectifs d'épargne."""

    def __init__(self, db_path: str = "data/goals.db"):
        """Initialise le gestionnaire."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                target_date TEXT,
                monthly_contribution REAL DEFAULT 0,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                color TEXT DEFAULT '#3498db',
                icon TEXT DEFAULT '🎯',
                notes TEXT,
                created_at TEXT,
                linked_portfolio_id INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY (goal_id) REFERENCES goals (id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_goal(self, goal: SavingsGoal) -> SavingsGoal:
        """Crée un nouvel objectif."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        goal.created_at = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO goals (name, category, target_amount, current_amount, target_date,
                              monthly_contribution, priority, status, color, icon, notes,
                              created_at, linked_portfolio_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (goal.name, goal.category.value, goal.target_amount, goal.current_amount,
              goal.target_date, goal.monthly_contribution, goal.priority, goal.status.value,
              goal.color, goal.icon, goal.notes, goal.created_at, goal.linked_portfolio_id))

        goal.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return goal

    def get_goal(self, goal_id: int) -> Optional[SavingsGoal]:
        """Récupère un objectif par ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_goal(row)

    def get_all_goals(self, status: Optional[GoalStatus] = None) -> List[SavingsGoal]:
        """Récupère tous les objectifs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute('SELECT * FROM goals WHERE status = ? ORDER BY priority, target_date',
                          (status.value,))
        else:
            cursor.execute('SELECT * FROM goals ORDER BY priority, target_date')

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_goal(row) for row in rows]

    def _row_to_goal(self, row) -> SavingsGoal:
        """Convertit une ligne SQL en SavingsGoal."""
        return SavingsGoal(
            id=row[0],
            name=row[1],
            category=GoalCategory(row[2]),
            target_amount=row[3],
            current_amount=row[4] or 0,
            target_date=row[5] or '',
            monthly_contribution=row[6] or 0,
            priority=row[7] or 1,
            status=GoalStatus(row[8]),
            color=row[9] or '#3498db',
            icon=row[10] or '🎯',
            notes=row[11] or '',
            created_at=row[12] or '',
            linked_portfolio_id=row[13]
        )

    def update_goal(self, goal: SavingsGoal) -> bool:
        """Met à jour un objectif."""
        if not goal.id:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE goals SET name = ?, category = ?, target_amount = ?, current_amount = ?,
                target_date = ?, monthly_contribution = ?, priority = ?, status = ?,
                color = ?, icon = ?, notes = ?, linked_portfolio_id = ?
            WHERE id = ?
        ''', (goal.name, goal.category.value, goal.target_amount, goal.current_amount,
              goal.target_date, goal.monthly_contribution, goal.priority, goal.status.value,
              goal.color, goal.icon, goal.notes, goal.linked_portfolio_id, goal.id))

        conn.commit()
        conn.close()
        return True

    def delete_goal(self, goal_id: int) -> bool:
        """Supprime un objectif."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM contributions WHERE goal_id = ?', (goal_id,))
        cursor.execute('DELETE FROM goals WHERE id = ?', (goal_id,))

        conn.commit()
        conn.close()
        return True

    def add_contribution(self, goal_id: int, amount: float,
                          date_str: str = None, notes: str = '') -> bool:
        """Ajoute un versement à un objectif."""
        goal = self.get_goal(goal_id)
        if not goal:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        date_str = date_str or date.today().strftime('%Y-%m-%d')

        # Enregistrer le versement
        cursor.execute('''
            INSERT INTO contributions (goal_id, date, amount, notes)
            VALUES (?, ?, ?, ?)
        ''', (goal_id, date_str, amount, notes))

        # Mettre à jour le montant actuel
        cursor.execute('''
            UPDATE goals SET current_amount = current_amount + ?
            WHERE id = ?
        ''', (amount, goal_id))

        # Vérifier si l'objectif est atteint
        cursor.execute('SELECT current_amount, target_amount FROM goals WHERE id = ?', (goal_id,))
        row = cursor.fetchone()
        if row and row[0] >= row[1]:
            cursor.execute('UPDATE goals SET status = ? WHERE id = ?',
                          (GoalStatus.COMPLETED.value, goal_id))

        conn.commit()
        conn.close()
        return True

    def get_contributions(self, goal_id: int) -> List[GoalContribution]:
        """Récupère l'historique des versements."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, goal_id, date, amount, notes
            FROM contributions WHERE goal_id = ?
            ORDER BY date DESC
        ''', (goal_id,))

        contributions = []
        for row in cursor.fetchall():
            contributions.append(GoalContribution(
                id=row[0], goal_id=row[1], date=row[2], amount=row[3], notes=row[4]
            ))

        conn.close()
        return contributions

    def get_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de tous les objectifs."""
        goals = self.get_all_goals()
        active_goals = [g for g in goals if g.status == GoalStatus.ACTIVE]

        total_target = sum(g.target_amount for g in active_goals)
        total_current = sum(g.current_amount for g in active_goals)
        total_monthly = sum(g.monthly_contribution for g in active_goals)

        on_track = sum(1 for g in active_goals if g.is_on_track)

        return {
            'total_goals': len(goals),
            'active_goals': len(active_goals),
            'completed_goals': sum(1 for g in goals if g.status == GoalStatus.COMPLETED),
            'total_target': total_target,
            'total_current': total_current,
            'total_progress_pct': (total_current / total_target * 100) if total_target > 0 else 0,
            'total_monthly_contributions': total_monthly,
            'goals_on_track': on_track,
            'goals_behind': len(active_goals) - on_track
        }

    def project_goal(self, goal: SavingsGoal, years: int = 5,
                      annual_return: float = 5) -> List[Dict[str, Any]]:
        """
        Projette l'évolution d'un objectif avec rendement.

        Args:
            goal: Objectif à projeter
            years: Nombre d'années de projection
            annual_return: Rendement annuel estimé (%)

        Returns:
            Liste de projections mensuelles
        """
        projections = []
        current = goal.current_amount
        monthly_return = (1 + annual_return / 100) ** (1 / 12) - 1

        for month in range(years * 12):
            # Appliquer le rendement
            current = current * (1 + monthly_return)
            # Ajouter le versement
            current += goal.monthly_contribution

            if month % 12 == 11 or current >= goal.target_amount:
                projections.append({
                    'month': month + 1,
                    'year': (month + 1) // 12,
                    'amount': current,
                    'progress_pct': min(100, current / goal.target_amount * 100),
                    'target_reached': current >= goal.target_amount
                })

            if current >= goal.target_amount:
                break

        return projections

    def suggest_monthly_contribution(self, target_amount: float, target_date: str,
                                      current_amount: float = 0,
                                      annual_return: float = 5) -> Dict[str, float]:
        """
        Suggère le versement mensuel optimal.

        Args:
            target_amount: Montant cible
            target_date: Date cible (YYYY-MM-DD)
            current_amount: Montant actuel
            annual_return: Rendement estimé (%)

        Returns:
            Dict avec suggestions sans/avec rendement
        """
        target = datetime.strptime(target_date, '%Y-%m-%d').date()
        months = (target - date.today()).days / 30.44

        if months <= 0:
            return {'without_return': target_amount - current_amount,
                    'with_return': target_amount - current_amount}

        remaining = target_amount - current_amount

        # Sans rendement
        without_return = remaining / months

        # Avec rendement (formule de versement pour atteindre un objectif)
        monthly_return = (1 + annual_return / 100) ** (1 / 12) - 1
        if monthly_return > 0:
            # FV = PMT * ((1+r)^n - 1) / r + PV * (1+r)^n
            # On résout pour PMT
            future_of_current = current_amount * ((1 + monthly_return) ** months)
            remaining_with_growth = target_amount - future_of_current
            factor = ((1 + monthly_return) ** months - 1) / monthly_return
            with_return = remaining_with_growth / factor if factor > 0 else without_return
        else:
            with_return = without_return

        return {
            'without_return': max(0, without_return),
            'with_return': max(0, with_return),
            'months_remaining': months,
            'savings_with_return': without_return - with_return
        }


# Objectifs prédéfinis
GOAL_PRESETS = {
    GoalCategory.EMERGENCY_FUND: {
        'name': "Fonds d'urgence",
        'icon': '🆘',
        'color': '#e74c3c',
        'suggested_months': 6  # 6 mois de dépenses
    },
    GoalCategory.RETIREMENT: {
        'name': "Retraite",
        'icon': '🏖️',
        'color': '#27ae60',
        'suggested_years': 20
    },
    GoalCategory.HOUSE: {
        'name': "Apport immobilier",
        'icon': '🏠',
        'color': '#3498db',
        'typical_amount': 50000
    },
    GoalCategory.TRAVEL: {
        'name': "Voyage",
        'icon': '✈️',
        'color': '#9b59b6',
        'typical_amount': 3000
    }
}


# Test
if __name__ == "__main__":
    print("=== Test Savings Goal Manager ===\n")

    manager = SavingsGoalManager("test_goals.db")

    # Créer un objectif
    goal = SavingsGoal(
        name="Apport maison",
        category=GoalCategory.HOUSE,
        target_amount=50000,
        current_amount=15000,
        target_date="2027-01-01",
        monthly_contribution=800,
        priority=1,
        icon="🏠",
        color="#3498db"
    )

    goal = manager.create_goal(goal)
    print(f"Objectif créé: {goal.name} (ID: {goal.id})")

    # Afficher les métriques
    print(f"\n=== Progression ===")
    print(f"Progression: {goal.progress_pct:.1f}%")
    print(f"Restant: {goal.remaining_amount:,.0f}€")
    print(f"Jours restants: {goal.days_remaining}")
    print(f"Versement requis: {goal.required_monthly:,.0f}€/mois")
    print(f"Sur la bonne voie: {'Oui' if goal.is_on_track else 'Non'}")
    print(f"Date estimée: {goal.projected_completion_date}")

    # Ajouter un versement
    manager.add_contribution(goal.id, 800, notes="Janvier 2025")
    goal = manager.get_goal(goal.id)
    print(f"\nAprès versement: {goal.current_amount:,.0f}€ ({goal.progress_pct:.1f}%)")

    # Suggestion
    suggestion = manager.suggest_monthly_contribution(50000, "2027-01-01", 15800)
    print(f"\n=== Suggestions ===")
    print(f"Sans rendement: {suggestion['without_return']:,.0f}€/mois")
    print(f"Avec 5% rendement: {suggestion['with_return']:,.0f}€/mois")
    print(f"Économie: {suggestion['savings_with_return']:,.0f}€/mois")

    # Résumé
    summary = manager.get_summary()
    print(f"\n=== Résumé ===")
    print(f"Objectifs actifs: {summary['active_goals']}")
    print(f"Total cible: {summary['total_target']:,.0f}€")
    print(f"Total actuel: {summary['total_current']:,.0f}€")

    # Nettoyage
    import os
    os.remove("test_goals.db")
    print("\n✅ Test terminé")
