"""
Système d'Alertes - Stock Advisor

Ce module gère:
- Alertes quand une action atteint le score d'achat (>55)
- Alertes quand une action tombe sous le seuil de vente (<40)
- Alertes sur mouvements Smart Money
- Notifications par email, webhook ou fichier local
- Scheduler pour vérifications périodiques
"""

import json
import logging
import smtplib
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Optional, Callable
import threading
import time

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Types d'alertes."""
    BUY_SIGNAL = "buy_signal"           # Score >= seuil d'achat
    SELL_SIGNAL = "sell_signal"         # Score < seuil de vente
    SMART_MONEY_BUY = "smart_money_buy" # Gourou achète
    SMART_MONEY_SELL = "smart_money_sell"  # Gourou vend
    PRICE_TARGET = "price_target"       # Prix atteint
    SCORE_CHANGE = "score_change"       # Changement significatif de score
    WATCHLIST = "watchlist"             # Action dans watchlist


class AlertPriority(Enum):
    """Priorité des alertes."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Alert:
    """Une alerte individuelle."""
    id: str
    alert_type: AlertType
    ticker: str
    title: str
    message: str
    priority: AlertPriority
    created_at: datetime = field(default_factory=datetime.now)
    data: dict = field(default_factory=dict)
    read: bool = False
    notified: bool = False


@dataclass
class AlertRule:
    """Règle pour déclencher une alerte."""
    id: str
    name: str
    alert_type: AlertType
    condition: str  # "score_above", "score_below", "price_above", etc.
    threshold: float
    tickers: list = field(default_factory=list)  # [] = toutes les actions
    enabled: bool = True
    cooldown_hours: int = 24  # Délai entre alertes répétées


class AlertNotifier:
    """Classe de base pour les notifications."""

    def send(self, alert: Alert) -> bool:
        raise NotImplementedError


class EmailNotifier(AlertNotifier):
    """Notification par email."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: list
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails

    def send(self, alert: Alert) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[Stock Advisor] {alert.title}"

            body = f"""
            {alert.message}

            ---
            Ticker: {alert.ticker}
            Type: {alert.alert_type.value}
            Priorité: {alert.priority.value}
            Date: {alert.created_at.strftime('%Y-%m-%d %H:%M')}

            ---
            Stock Advisor - Alertes automatiques
            """

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, self.to_emails, msg.as_string())

            logger.info(f"Email envoyé pour alerte {alert.id}")
            return True

        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False


class WebhookNotifier(AlertNotifier):
    """Notification par webhook (Discord, Slack, etc.)."""

    def __init__(self, webhook_url: str, platform: str = "discord"):
        self.webhook_url = webhook_url
        self.platform = platform

    def send(self, alert: Alert) -> bool:
        try:
            if self.platform == "discord":
                payload = self._format_discord(alert)
            elif self.platform == "slack":
                payload = self._format_slack(alert)
            else:
                payload = self._format_generic(alert)

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                logger.info(f"Webhook envoyé pour alerte {alert.id}")
                return True
            else:
                logger.warning(f"Webhook erreur {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Erreur webhook: {e}")
            return False

    def _format_discord(self, alert: Alert) -> dict:
        """Format pour Discord webhook."""
        color_map = {
            AlertPriority.LOW: 0x808080,      # Gris
            AlertPriority.MEDIUM: 0x3498db,   # Bleu
            AlertPriority.HIGH: 0xf39c12,     # Orange
            AlertPriority.URGENT: 0xe74c3c,   # Rouge
        }

        emoji_map = {
            AlertType.BUY_SIGNAL: "📈",
            AlertType.SELL_SIGNAL: "📉",
            AlertType.SMART_MONEY_BUY: "💰",
            AlertType.SMART_MONEY_SELL: "⚠️",
            AlertType.WATCHLIST: "👀",
        }

        emoji = emoji_map.get(alert.alert_type, "🔔")

        return {
            "embeds": [{
                "title": f"{emoji} {alert.title}",
                "description": alert.message,
                "color": color_map.get(alert.priority, 0x3498db),
                "fields": [
                    {"name": "Ticker", "value": alert.ticker, "inline": True},
                    {"name": "Type", "value": alert.alert_type.value, "inline": True},
                    {"name": "Priorité", "value": alert.priority.value, "inline": True},
                ],
                "timestamp": alert.created_at.isoformat(),
                "footer": {"text": "Stock Advisor"}
            }]
        }

    def _format_slack(self, alert: Alert) -> dict:
        """Format pour Slack webhook."""
        return {
            "text": f"*{alert.title}*",
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*{alert.title}*\n{alert.message}"}
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"*Ticker:* {alert.ticker}"},
                        {"type": "mrkdwn", "text": f"*Type:* {alert.alert_type.value}"},
                    ]
                }
            ]
        }

    def _format_generic(self, alert: Alert) -> dict:
        """Format générique JSON."""
        return asdict(alert)


class FileNotifier(AlertNotifier):
    """Notification par fichier local (pour tests ou logs)."""

    def __init__(self, file_path: str = "alerts.json"):
        self.file_path = Path(file_path)

    def send(self, alert: Alert) -> bool:
        try:
            alerts = []
            if self.file_path.exists():
                with open(self.file_path, 'r') as f:
                    alerts = json.load(f)

            alert_dict = {
                'id': alert.id,
                'type': alert.alert_type.value,
                'ticker': alert.ticker,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority.value,
                'created_at': alert.created_at.isoformat(),
                'data': alert.data
            }
            alerts.append(alert_dict)

            with open(self.file_path, 'w') as f:
                json.dump(alerts, f, indent=2)

            logger.info(f"Alerte {alert.id} écrite dans {self.file_path}")
            return True

        except Exception as e:
            logger.error(f"Erreur écriture fichier: {e}")
            return False


class AlertManager:
    """
    Gestionnaire principal des alertes.
    """

    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self.notifiers: list[AlertNotifier] = []
        self.rules: list[AlertRule] = []
        self._last_alerts: dict = {}  # Pour cooldown
        self._init_db()

        # Ajouter un notifier fichier par défaut
        self.add_notifier(FileNotifier("data/alerts.json"))

    def _init_db(self):
        """Initialise la base de données SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT,
                ticker TEXT,
                title TEXT,
                message TEXT,
                priority TEXT,
                created_at TEXT,
                data TEXT,
                read INTEGER DEFAULT 0,
                notified INTEGER DEFAULT 0
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rules (
                id TEXT PRIMARY KEY,
                name TEXT,
                alert_type TEXT,
                condition TEXT,
                threshold REAL,
                tickers TEXT,
                enabled INTEGER DEFAULT 1,
                cooldown_hours INTEGER DEFAULT 24
            )
        ''')

        conn.commit()
        conn.close()

    def add_notifier(self, notifier: AlertNotifier):
        """Ajoute un canal de notification."""
        self.notifiers.append(notifier)

    def add_rule(self, rule: AlertRule):
        """Ajoute une règle d'alerte."""
        self.rules.append(rule)
        self._save_rule(rule)

    def _save_rule(self, rule: AlertRule):
        """Sauvegarde une règle en base."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO rules
            (id, name, alert_type, condition, threshold, tickers, enabled, cooldown_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.id,
            rule.name,
            rule.alert_type.value,
            rule.condition,
            rule.threshold,
            json.dumps(rule.tickers),
            1 if rule.enabled else 0,
            rule.cooldown_hours
        ))

        conn.commit()
        conn.close()

    def create_alert(
        self,
        alert_type: AlertType,
        ticker: str,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        data: dict = None
    ) -> Alert:
        """Crée et enregistre une alerte."""
        alert_id = f"{alert_type.value}_{ticker}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            ticker=ticker,
            title=title,
            message=message,
            priority=priority,
            data=data or {}
        )

        # Vérifier le cooldown
        cooldown_key = f"{alert_type.value}_{ticker}"
        if cooldown_key in self._last_alerts:
            last_time = self._last_alerts[cooldown_key]
            if datetime.now() - last_time < timedelta(hours=24):
                logger.debug(f"Alerte {cooldown_key} en cooldown")
                return alert

        # Sauvegarder
        self._save_alert(alert)
        self._last_alerts[cooldown_key] = datetime.now()

        # Notifier
        self._notify(alert)

        return alert

    def _save_alert(self, alert: Alert):
        """Sauvegarde une alerte en base."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alerts
            (id, alert_type, ticker, title, message, priority, created_at, data, read, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.id,
            alert.alert_type.value,
            alert.ticker,
            alert.title,
            alert.message,
            alert.priority.value,
            alert.created_at.isoformat(),
            json.dumps(alert.data),
            0,
            0
        ))

        conn.commit()
        conn.close()

    def _notify(self, alert: Alert):
        """Envoie l'alerte à tous les notifiers."""
        for notifier in self.notifiers:
            try:
                success = notifier.send(alert)
                if success:
                    alert.notified = True
            except Exception as e:
                logger.error(f"Erreur notification: {e}")

    def get_unread_alerts(self, limit: int = 50) -> list[dict]:
        """Récupère les alertes non lues."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, alert_type, ticker, title, message, priority, created_at, data
            FROM alerts
            WHERE read = 0
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'id': row[0],
                'type': row[1],
                'ticker': row[2],
                'title': row[3],
                'message': row[4],
                'priority': row[5],
                'created_at': row[6],
                'data': json.loads(row[7]) if row[7] else {}
            })

        conn.close()
        return alerts

    def mark_as_read(self, alert_id: str):
        """Marque une alerte comme lue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE alerts SET read = 1 WHERE id = ?', (alert_id,))
        conn.commit()
        conn.close()

    def check_stock(self, ticker: str, score: float, price: float = None):
        """
        Vérifie si une action doit déclencher une alerte.

        Args:
            ticker: Symbole de l'action
            score: Score global actuel (0-100)
            price: Prix actuel (optionnel)
        """
        # Vérifier les règles
        for rule in self.rules:
            if not rule.enabled:
                continue

            # Vérifier si le ticker est concerné
            if rule.tickers and ticker not in rule.tickers:
                continue

            # Vérifier les conditions
            if rule.condition == "score_above" and score >= rule.threshold:
                self.create_alert(
                    alert_type=AlertType.BUY_SIGNAL,
                    ticker=ticker,
                    title=f"Signal d'achat - {ticker}",
                    message=f"{ticker} a atteint un score de {score:.0f}/100 (seuil: {rule.threshold})",
                    priority=AlertPriority.HIGH if score >= 70 else AlertPriority.MEDIUM,
                    data={'score': score, 'threshold': rule.threshold}
                )

            elif rule.condition == "score_below" and score < rule.threshold:
                self.create_alert(
                    alert_type=AlertType.SELL_SIGNAL,
                    ticker=ticker,
                    title=f"Signal de vente - {ticker}",
                    message=f"{ticker} est tombé à un score de {score:.0f}/100 (seuil: {rule.threshold})",
                    priority=AlertPriority.HIGH,
                    data={'score': score, 'threshold': rule.threshold}
                )


class AlertScheduler:
    """
    Planificateur pour vérifications périodiques.
    """

    def __init__(self, alert_manager: AlertManager, check_interval_minutes: int = 60):
        self.alert_manager = alert_manager
        self.check_interval = check_interval_minutes * 60
        self._running = False
        self._thread = None
        self._check_callback: Optional[Callable] = None

    def set_check_callback(self, callback: Callable):
        """
        Définit la fonction de vérification.
        callback(ticker) -> (score, price)
        """
        self._check_callback = callback

    def start(self, tickers: list):
        """Démarre le scheduler."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(tickers,),
            daemon=True
        )
        self._thread.start()
        logger.info(f"Scheduler démarré - vérification toutes les {self.check_interval // 60} minutes")

    def stop(self):
        """Arrête le scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler arrêté")

    def _run_loop(self, tickers: list):
        """Boucle principale du scheduler."""
        while self._running:
            try:
                self._check_all(tickers)
            except Exception as e:
                logger.error(f"Erreur vérification: {e}")

            time.sleep(self.check_interval)

    def _check_all(self, tickers: list):
        """Vérifie toutes les actions."""
        if not self._check_callback:
            logger.warning("Pas de callback défini")
            return

        logger.info(f"Vérification de {len(tickers)} actions...")

        for ticker in tickers:
            try:
                result = self._check_callback(ticker)
                if result:
                    score, price = result
                    self.alert_manager.check_stock(ticker, score, price)
            except Exception as e:
                logger.debug(f"Erreur vérification {ticker}: {e}")


# Règles par défaut
DEFAULT_RULES = [
    AlertRule(
        id="buy_signal_55",
        name="Signal d'achat (score >= 55)",
        alert_type=AlertType.BUY_SIGNAL,
        condition="score_above",
        threshold=55
    ),
    AlertRule(
        id="strong_buy_70",
        name="Achat fort (score >= 70)",
        alert_type=AlertType.BUY_SIGNAL,
        condition="score_above",
        threshold=70
    ),
    AlertRule(
        id="sell_signal_40",
        name="Signal de vente (score < 40)",
        alert_type=AlertType.SELL_SIGNAL,
        condition="score_below",
        threshold=40
    ),
]


def create_default_alert_manager() -> AlertManager:
    """Crée un AlertManager avec les règles par défaut."""
    manager = AlertManager()

    for rule in DEFAULT_RULES:
        manager.add_rule(rule)

    return manager


# Test
if __name__ == "__main__":
    print("=== Test Système d'Alertes ===")

    # Créer le manager
    manager = create_default_alert_manager()

    # Simuler une vérification
    print("\nTest: Action avec score élevé")
    manager.check_stock("AAPL", score=72.5, price=178.50)

    print("\nTest: Action avec score faible")
    manager.check_stock("INTC", score=35.0, price=42.10)

    # Afficher les alertes
    print("\n=== Alertes non lues ===")
    alerts = manager.get_unread_alerts()
    for alert in alerts:
        print(f"  [{alert['priority']}] {alert['title']}")
        print(f"     {alert['message']}")
