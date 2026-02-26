"""
Gestionnaire de transactions récurrentes (DCA) pour Stock Advisor.
Enregistrer, planifier et suivre les versements automatiques.
"""
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class RecurrenceType(Enum):
    """Fréquence de récurrence."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TransactionType(Enum):
    """Type de transaction."""
    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


@dataclass
class RecurringTransaction:
    """Représente une transaction récurrente."""
    id: Optional[int] = None
    portfolio_id: int = 0
    ticker: Optional[str] = None  # None pour dépôt/retrait
    transaction_type: TransactionType = TransactionType.BUY
    amount: float = 0  # Montant ou quantité selon use_amount
    use_amount: bool = True  # True = montant fixe, False = quantité fixe
    recurrence: RecurrenceType = RecurrenceType.MONTHLY
    day_of_month: int = 1  # Jour d'exécution (1-28)
    start_date: str = ""  # YYYY-MM-DD
    end_date: Optional[str] = None  # YYYY-MM-DD ou None pour illimité
    next_execution: str = ""  # YYYY-MM-DD
    is_active: bool = True
    name: str = ""
    notes: str = ""
    created_at: str = ""
    execution_count: int = 0
    total_executed: float = 0

    @property
    def recurrence_label(self) -> str:
        """Libellé de la fréquence."""
        labels = {
            RecurrenceType.WEEKLY: "Hebdomadaire",
            RecurrenceType.BIWEEKLY: "Bi-hebdomadaire",
            RecurrenceType.MONTHLY: "Mensuel",
            RecurrenceType.QUARTERLY: "Trimestriel",
            RecurrenceType.YEARLY: "Annuel"
        }
        return labels.get(self.recurrence, "")

    @property
    def annual_projection(self) -> float:
        """Projection annuelle des versements."""
        multipliers = {
            RecurrenceType.WEEKLY: 52,
            RecurrenceType.BIWEEKLY: 26,
            RecurrenceType.MONTHLY: 12,
            RecurrenceType.QUARTERLY: 4,
            RecurrenceType.YEARLY: 1
        }
        return self.amount * multipliers.get(self.recurrence, 12)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['transaction_type'] = self.transaction_type.value
        d['recurrence'] = self.recurrence.value
        d['recurrence_label'] = self.recurrence_label
        d['annual_projection'] = self.annual_projection
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'RecurringTransaction':
        for key in ['recurrence_label', 'annual_projection']:
            data.pop(key, None)

        data['transaction_type'] = TransactionType(data.get('transaction_type', 'buy'))
        data['recurrence'] = RecurrenceType(data.get('recurrence', 'monthly'))

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionRecord:
    """Enregistrement d'une exécution."""
    id: Optional[int] = None
    recurring_id: int = 0
    execution_date: str = ""
    amount: float = 0
    price: Optional[float] = None
    quantity: Optional[float] = None
    status: str = "completed"  # completed, failed, skipped
    notes: str = ""


class RecurringTransactionManager:
    """Gestionnaire des transactions récurrentes."""

    def __init__(self, db_path: str = "data/recurring.db"):
        """Initialise le gestionnaire."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise la base de données."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                ticker TEXT,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                use_amount INTEGER DEFAULT 1,
                recurrence TEXT NOT NULL,
                day_of_month INTEGER DEFAULT 1,
                start_date TEXT NOT NULL,
                end_date TEXT,
                next_execution TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                name TEXT,
                notes TEXT,
                created_at TEXT,
                execution_count INTEGER DEFAULT 0,
                total_executed REAL DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recurring_id INTEGER NOT NULL,
                execution_date TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL,
                quantity REAL,
                status TEXT DEFAULT 'completed',
                notes TEXT,
                FOREIGN KEY (recurring_id) REFERENCES recurring_transactions (id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_recurring(self, transaction: RecurringTransaction) -> RecurringTransaction:
        """Crée une transaction récurrente."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        transaction.created_at = datetime.now().isoformat()

        # Calculer la prochaine exécution
        if not transaction.next_execution:
            transaction.next_execution = self._calculate_next_execution(
                transaction.start_date, transaction.recurrence, transaction.day_of_month
            )

        cursor.execute('''
            INSERT INTO recurring_transactions (portfolio_id, ticker, transaction_type, amount,
                use_amount, recurrence, day_of_month, start_date, end_date, next_execution,
                is_active, name, notes, created_at, execution_count, total_executed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction.portfolio_id, transaction.ticker, transaction.transaction_type.value,
              transaction.amount, 1 if transaction.use_amount else 0, transaction.recurrence.value,
              transaction.day_of_month, transaction.start_date, transaction.end_date,
              transaction.next_execution, 1 if transaction.is_active else 0,
              transaction.name, transaction.notes, transaction.created_at,
              transaction.execution_count, transaction.total_executed))

        transaction.id = cursor.lastrowid
        conn.commit()
        conn.close()

        return transaction

    def _calculate_next_execution(self, start_date: str, recurrence: RecurrenceType,
                                   day_of_month: int = 1) -> str:
        """Calcule la prochaine date d'exécution."""
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
        except Exception:
            start = date.today()

        today = date.today()

        if start > today:
            next_date = start
        else:
            if recurrence == RecurrenceType.WEEKLY:
                days_until = (7 - today.weekday()) % 7
                next_date = today + timedelta(days=days_until or 7)

            elif recurrence == RecurrenceType.BIWEEKLY:
                days_until = (7 - today.weekday()) % 7
                next_date = today + timedelta(days=days_until + 7)

            elif recurrence == RecurrenceType.MONTHLY:
                if today.day < day_of_month:
                    next_date = today.replace(day=min(day_of_month, 28))
                else:
                    next_month = today + relativedelta(months=1)
                    next_date = next_month.replace(day=min(day_of_month, 28))

            elif recurrence == RecurrenceType.QUARTERLY:
                next_month = today + relativedelta(months=3)
                next_date = next_month.replace(day=min(day_of_month, 28))

            elif recurrence == RecurrenceType.YEARLY:
                if today.month < start.month or (today.month == start.month and today.day < day_of_month):
                    next_date = today.replace(month=start.month, day=min(day_of_month, 28))
                else:
                    next_date = today.replace(year=today.year + 1, month=start.month, day=min(day_of_month, 28))

            else:
                next_date = today + timedelta(days=30)

        return next_date.strftime('%Y-%m-%d')

    def get_recurring(self, recurring_id: int) -> Optional[RecurringTransaction]:
        """Récupère une transaction récurrente par ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM recurring_transactions WHERE id = ?', (recurring_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_transaction(row)

    def get_all_recurring(self, portfolio_id: Optional[int] = None,
                           active_only: bool = False) -> List[RecurringTransaction]:
        """Récupère toutes les transactions récurrentes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT * FROM recurring_transactions WHERE 1=1'
        params = []

        if portfolio_id:
            query += ' AND portfolio_id = ?'
            params.append(portfolio_id)

        if active_only:
            query += ' AND is_active = 1'

        query += ' ORDER BY next_execution'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_transaction(row) for row in rows]

    def _row_to_transaction(self, row) -> RecurringTransaction:
        """Convertit une ligne SQL en RecurringTransaction."""
        return RecurringTransaction(
            id=row[0],
            portfolio_id=row[1],
            ticker=row[2],
            transaction_type=TransactionType(row[3]),
            amount=row[4],
            use_amount=bool(row[5]),
            recurrence=RecurrenceType(row[6]),
            day_of_month=row[7],
            start_date=row[8],
            end_date=row[9],
            next_execution=row[10],
            is_active=bool(row[11]),
            name=row[12] or '',
            notes=row[13] or '',
            created_at=row[14] or '',
            execution_count=row[15] or 0,
            total_executed=row[16] or 0
        )

    def update_recurring(self, transaction: RecurringTransaction) -> bool:
        """Met à jour une transaction récurrente."""
        if not transaction.id:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE recurring_transactions SET portfolio_id = ?, ticker = ?, transaction_type = ?,
                amount = ?, use_amount = ?, recurrence = ?, day_of_month = ?, start_date = ?,
                end_date = ?, next_execution = ?, is_active = ?, name = ?, notes = ?
            WHERE id = ?
        ''', (transaction.portfolio_id, transaction.ticker, transaction.transaction_type.value,
              transaction.amount, 1 if transaction.use_amount else 0, transaction.recurrence.value,
              transaction.day_of_month, transaction.start_date, transaction.end_date,
              transaction.next_execution, 1 if transaction.is_active else 0,
              transaction.name, transaction.notes, transaction.id))

        conn.commit()
        conn.close()
        return True

    def delete_recurring(self, recurring_id: int) -> bool:
        """Supprime une transaction récurrente."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM execution_history WHERE recurring_id = ?', (recurring_id,))
        cursor.execute('DELETE FROM recurring_transactions WHERE id = ?', (recurring_id,))

        conn.commit()
        conn.close()
        return True

    def pause_recurring(self, recurring_id: int) -> bool:
        """Met en pause une transaction récurrente."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('UPDATE recurring_transactions SET is_active = 0 WHERE id = ?', (recurring_id,))

        conn.commit()
        conn.close()
        return True

    def resume_recurring(self, recurring_id: int) -> bool:
        """Reprend une transaction récurrente."""
        transaction = self.get_recurring(recurring_id)
        if not transaction:
            return False

        # Recalculer la prochaine exécution
        next_exec = self._calculate_next_execution(
            date.today().strftime('%Y-%m-%d'),
            transaction.recurrence,
            transaction.day_of_month
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE recurring_transactions SET is_active = 1, next_execution = ?
            WHERE id = ?
        ''', (next_exec, recurring_id))

        conn.commit()
        conn.close()
        return True

    def record_execution(self, recurring_id: int, amount: float,
                          price: float = None, quantity: float = None,
                          status: str = 'completed', notes: str = '') -> bool:
        """Enregistre l'exécution d'une transaction récurrente."""
        transaction = self.get_recurring(recurring_id)
        if not transaction:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        execution_date = date.today().strftime('%Y-%m-%d')

        # Enregistrer l'exécution
        cursor.execute('''
            INSERT INTO execution_history (recurring_id, execution_date, amount, price, quantity, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (recurring_id, execution_date, amount, price, quantity, status, notes))

        # Calculer la prochaine exécution
        next_exec = self._calculate_next_execution(
            execution_date, transaction.recurrence, transaction.day_of_month
        )

        # Vérifier si on doit désactiver (date de fin atteinte)
        should_deactivate = False
        if transaction.end_date:
            end = datetime.strptime(transaction.end_date, '%Y-%m-%d').date()
            next_date = datetime.strptime(next_exec, '%Y-%m-%d').date()
            if next_date > end:
                should_deactivate = True

        # Mettre à jour la transaction
        cursor.execute('''
            UPDATE recurring_transactions SET
                next_execution = ?,
                execution_count = execution_count + 1,
                total_executed = total_executed + ?,
                is_active = ?
            WHERE id = ?
        ''', (next_exec, amount, 0 if should_deactivate else 1, recurring_id))

        conn.commit()
        conn.close()
        return True

    def get_execution_history(self, recurring_id: int) -> List[ExecutionRecord]:
        """Récupère l'historique d'exécution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, recurring_id, execution_date, amount, price, quantity, status, notes
            FROM execution_history WHERE recurring_id = ?
            ORDER BY execution_date DESC
        ''', (recurring_id,))

        records = []
        for row in cursor.fetchall():
            records.append(ExecutionRecord(
                id=row[0], recurring_id=row[1], execution_date=row[2],
                amount=row[3], price=row[4], quantity=row[5],
                status=row[6], notes=row[7]
            ))

        conn.close()
        return records

    def get_due_transactions(self) -> List[RecurringTransaction]:
        """Récupère les transactions à exécuter (date dépassée)."""
        today = date.today().strftime('%Y-%m-%d')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM recurring_transactions
            WHERE is_active = 1 AND next_execution <= ?
            ORDER BY next_execution
        ''', (today,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_transaction(row) for row in rows]

    def get_upcoming_transactions(self, days: int = 30) -> List[Dict]:
        """Récupère les transactions prévues dans les N prochains jours."""
        today = date.today()
        end_date = today + timedelta(days=days)

        active = self.get_all_recurring(active_only=True)
        upcoming = []

        for trans in active:
            next_date = datetime.strptime(trans.next_execution, '%Y-%m-%d').date()
            while next_date <= end_date:
                if next_date >= today:
                    upcoming.append({
                        'date': next_date.strftime('%Y-%m-%d'),
                        'transaction': trans,
                        'amount': trans.amount,
                        'ticker': trans.ticker,
                        'type': trans.transaction_type.value
                    })

                # Calculer la suivante
                if trans.recurrence == RecurrenceType.WEEKLY:
                    next_date += timedelta(weeks=1)
                elif trans.recurrence == RecurrenceType.BIWEEKLY:
                    next_date += timedelta(weeks=2)
                elif trans.recurrence == RecurrenceType.MONTHLY:
                    next_date += relativedelta(months=1)
                elif trans.recurrence == RecurrenceType.QUARTERLY:
                    next_date += relativedelta(months=3)
                elif trans.recurrence == RecurrenceType.YEARLY:
                    next_date += relativedelta(years=1)

        return sorted(upcoming, key=lambda x: x['date'])

    def get_summary(self, portfolio_id: Optional[int] = None) -> Dict[str, Any]:
        """Retourne un résumé des transactions récurrentes."""
        transactions = self.get_all_recurring(portfolio_id, active_only=True)

        total_monthly = 0
        for t in transactions:
            if t.recurrence == RecurrenceType.WEEKLY:
                total_monthly += t.amount * 4.33
            elif t.recurrence == RecurrenceType.BIWEEKLY:
                total_monthly += t.amount * 2.17
            elif t.recurrence == RecurrenceType.MONTHLY:
                total_monthly += t.amount
            elif t.recurrence == RecurrenceType.QUARTERLY:
                total_monthly += t.amount / 3
            elif t.recurrence == RecurrenceType.YEARLY:
                total_monthly += t.amount / 12

        due = self.get_due_transactions()

        return {
            'active_count': len(transactions),
            'total_monthly': total_monthly,
            'total_annual': total_monthly * 12,
            'due_count': len(due),
            'total_due': sum(t.amount for t in due),
            'total_executed': sum(t.total_executed for t in transactions)
        }


# Test
if __name__ == "__main__":
    print("=== Test Recurring Transactions ===\n")

    manager = RecurringTransactionManager("test_recurring.db")

    # Créer un DCA mensuel
    dca = RecurringTransaction(
        portfolio_id=1,
        ticker="MSFT",
        transaction_type=TransactionType.BUY,
        amount=500,
        use_amount=True,
        recurrence=RecurrenceType.MONTHLY,
        day_of_month=15,
        start_date="2025-01-15",
        name="DCA Microsoft",
        notes="Achat automatique mensuel"
    )

    dca = manager.create_recurring(dca)
    print(f"DCA créé: {dca.name} (ID: {dca.id})")
    print(f"  Montant: {dca.amount}€ / {dca.recurrence_label}")
    print(f"  Prochaine exécution: {dca.next_execution}")
    print(f"  Projection annuelle: {dca.annual_projection:,.0f}€")

    # Simuler une exécution
    manager.record_execution(dca.id, 500, price=420.50, quantity=1.19)
    dca = manager.get_recurring(dca.id)
    print(f"\nAprès exécution:")
    print(f"  Exécutions: {dca.execution_count}")
    print(f"  Total exécuté: {dca.total_executed:,.0f}€")
    print(f"  Prochaine: {dca.next_execution}")

    # Résumé
    summary = manager.get_summary()
    print(f"\n=== Résumé ===")
    print(f"Transactions actives: {summary['active_count']}")
    print(f"Versement mensuel: {summary['total_monthly']:,.0f}€")
    print(f"Projection annuelle: {summary['total_annual']:,.0f}€")

    # Nettoyage
    import os
    os.remove("test_recurring.db")
    print("\n✅ Test terminé")
