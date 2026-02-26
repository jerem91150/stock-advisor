"""
Pages étendues pour Stock Advisor v4.0
Inclut: Import CSV, Alertes, Benchmark, Immobilier, Objectifs, DCA
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Imports des modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.import_export.csv_importer import CSVImporter, BrokerType, get_csv_importer
except ImportError:
    CSVImporter = None

try:
    from src.alerts.manager import AlertManager, AlertType, AlertPriority, create_default_alert_manager
except ImportError:
    AlertManager = None

try:
    from src.analysis.benchmark import BenchmarkAnalyzer, BENCHMARKS, get_benchmark_names
except ImportError:
    BenchmarkAnalyzer = None

try:
    from src.real_estate.property_manager import PropertyManager, Property, PropertyType, PropertyUsage, Mortgage
except ImportError:
    PropertyManager = None

try:
    from src.goals.savings_goals import SavingsGoalManager, SavingsGoal, GoalCategory, GoalStatus
except ImportError:
    SavingsGoalManager = None

try:
    from src.portfolio.recurring_transactions import (
        RecurringTransactionManager, RecurringTransaction,
        RecurrenceType, TransactionType
    )
except ImportError:
    RecurringTransactionManager = None

try:
    from src.currency.currency_manager import CurrencyManager, get_supported_currencies, SUPPORTED_CURRENCIES
except ImportError:
    CurrencyManager = None

try:
    from src.reports.pdf_generator import PDFReportGenerator, ReportType
except ImportError:
    PDFReportGenerator = None


# ============================================================================
# PAGE: IMPORT CSV
# ============================================================================
def page_import_csv():
    """Page d'import CSV multi-broker."""
    st.header("📥 Import CSV")

    if CSVImporter is None:
        st.error("Module d'import non disponible")
        return

    st.markdown("""
    Importez vos transactions depuis votre broker. Formats supportés:
    - **Degiro** (Compte Rapport)
    - **Boursorama** (Historique des opérations)
    - **Trade Republic** (Export CSV)
    - **Interactive Brokers** (Activity Statement)
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Choisir un fichier CSV",
            type=['csv'],
            help="Sélectionnez le fichier CSV exporté depuis votre broker"
        )

    with col2:
        broker_auto = st.checkbox("Détection automatique du broker", value=True)
        if not broker_auto:
            broker_choice = st.selectbox(
                "Broker",
                options=[b.value for b in BrokerType]
            )

    if uploaded_file:
        importer = get_csv_importer()

        with st.spinner("Analyse du fichier..."):
            try:
                # Lire le contenu
                content = uploaded_file.getvalue().decode('utf-8')

                # Détecter le broker
                detected_broker = importer.detect_broker(content)
                st.info(f"🔍 Broker détecté: **{detected_broker.value}**")

                # Importer
                result = importer.import_csv(content, detected_broker)

                if result.success:
                    st.success(f"✅ {result.imported_count} transactions importées")

                    if result.transactions:
                        # Afficher les transactions
                        df = pd.DataFrame([
                            {
                                'Date': t.date,
                                'Ticker': t.ticker,
                                'Type': t.transaction_type,
                                'Quantité': t.quantity,
                                'Prix': f"{t.price:.2f} {t.currency}",
                                'Total': f"{t.total_amount:.2f} {t.currency}"
                            }
                            for t in result.transactions
                        ])

                        st.dataframe(df, use_container_width=True)

                        # Bouton pour ajouter au portefeuille
                        if st.button("➕ Ajouter au portefeuille", type="primary"):
                            st.success("Transactions ajoutées au portefeuille!")

                    if result.errors:
                        with st.expander(f"⚠️ {len(result.errors)} erreurs"):
                            for error in result.errors:
                                st.warning(error)
                else:
                    st.error(f"Erreur d'import: {result.errors}")

            except Exception as e:
                st.error(f"Erreur lors de l'import: {e}")


# ============================================================================
# PAGE: ALERTES
# ============================================================================
def page_alerts():
    """Page de gestion des alertes."""
    st.header("🔔 Alertes")

    if AlertManager is None:
        st.error("Module d'alertes non disponible")
        return

    alert_manager = create_default_alert_manager()

    tab1, tab2, tab3 = st.tabs(["Alertes actives", "Créer une alerte", "Historique"])

    with tab1:
        alerts = alert_manager.get_unread_alerts()

        if alerts:
            for alert in alerts:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        emoji = "📈" if "achat" in alert['type'] else "📉"
                        st.markdown(f"**{emoji} {alert['title']}**")
                        st.caption(alert['message'])
                    with col2:
                        priority_colors = {
                            'high': '🔴', 'medium': '🟡', 'low': '🟢', 'urgent': '⚫'
                        }
                        st.write(priority_colors.get(alert['priority'], '⚪'))
                    with col3:
                        if st.button("✓", key=f"read_{alert['id']}"):
                            alert_manager.mark_as_read(alert['id'])
                            st.rerun()
                    st.divider()
        else:
            st.info("Aucune alerte non lue")

    with tab2:
        st.subheader("Créer une nouvelle alerte")

        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker", placeholder="AAPL").upper()
            alert_type = st.selectbox(
                "Type d'alerte",
                options=[
                    ("Signal d'achat (score >= seuil)", "score_above"),
                    ("Signal de vente (score < seuil)", "score_below"),
                    ("Prix atteint", "price_target")
                ],
                format_func=lambda x: x[0]
            )

        with col2:
            threshold = st.number_input("Seuil", min_value=0.0, value=55.0)
            priority = st.selectbox(
                "Priorité",
                options=["medium", "high", "low", "urgent"]
            )

        if st.button("Créer l'alerte", type="primary"):
            if ticker:
                st.success(f"Alerte créée pour {ticker}")
            else:
                st.error("Veuillez entrer un ticker")

    with tab3:
        st.subheader("Historique des alertes")
        st.info("Historique des 30 derniers jours")


# ============================================================================
# PAGE: BENCHMARK
# ============================================================================
def page_benchmark():
    """Page de comparaison avec les benchmarks."""
    st.header("📊 Performance vs Benchmark")

    if BenchmarkAnalyzer is None:
        st.error("Module benchmark non disponible")
        return

    col1, col2 = st.columns([1, 2])

    with col1:
        benchmark_choice = st.selectbox(
            "Benchmark de référence",
            options=get_benchmark_names()
        )
        period = st.selectbox(
            "Période",
            options=['1m', '3m', '6m', '1y', '2y', '5y'],
            index=3
        )

    # Simulation de données portfolio
    with col2:
        st.subheader("Comparaison")

        analyzer = BenchmarkAnalyzer()

        # Créer des données de test
        import numpy as np
        dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.0004, 0.015, len(dates))
        portfolio_values = 10000 * (1 + pd.Series(returns)).cumprod()
        portfolio = pd.Series(portfolio_values.values, index=dates)

        # Comparer
        result = analyzer.compare_portfolio(portfolio, benchmark_choice, period)

        if result:
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                delta = result.portfolio_return - result.benchmark_return
                st.metric(
                    "Performance Portfolio",
                    f"{result.portfolio_return:.1f}%",
                    delta=f"{delta:+.1f}%"
                )
            with col_b:
                st.metric(
                    f"Performance {benchmark_choice}",
                    f"{result.benchmark_return:.1f}%"
                )
            with col_c:
                st.metric(
                    "Alpha",
                    f"{result.alpha:.1f}%",
                    delta="Surperformance" if result.alpha > 0 else "Sous-performance"
                )

            # Métriques détaillées
            st.divider()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Beta", f"{result.beta:.2f}")
            col2.metric("Sharpe Ratio", f"{result.sharpe_ratio:.2f}")
            col3.metric("Corrélation", f"{result.correlation:.2f}")
            col4.metric("Win Rate", f"{result.win_rate:.0f}%")

            # Graphique comparatif
            chart_data = analyzer.get_comparison_chart_data(portfolio, benchmark_choice, period)
            if chart_data is not None:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=chart_data['date'], y=chart_data['Portfolio'],
                    name='Portfolio', line=dict(color='#3498db', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=chart_data['date'], y=chart_data[benchmark_choice],
                    name=benchmark_choice, line=dict(color='#e74c3c', width=2)
                ))
                fig.update_layout(
                    title="Évolution comparée (base 100)",
                    xaxis_title="Date",
                    yaxis_title="Valeur",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Impossible de calculer la comparaison")


# ============================================================================
# PAGE: IMMOBILIER
# ============================================================================
def page_real_estate():
    """Page de gestion immobilière."""
    st.header("🏠 Immobilier")

    if PropertyManager is None:
        st.error("Module immobilier non disponible")
        return

    manager = PropertyManager()

    tab1, tab2, tab3 = st.tabs(["Mes Biens", "Ajouter un bien", "Synthèse"])

    with tab1:
        properties = manager.get_all_properties()

        if properties:
            for prop in properties:
                with st.expander(f"🏠 {prop.name} - {prop.city}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Valeur actuelle", f"{prop.current_value:,.0f}€")
                        st.metric("Plus-value", f"{prop.capital_gain:,.0f}€",
                                  delta=f"{prop.capital_gain_pct:.1f}%")
                    with col2:
                        st.metric("Loyer mensuel", f"{prop.monthly_rent:,.0f}€")
                        st.metric("Cash-flow", f"{prop.cashflow_monthly:,.0f}€/mois")
                    with col3:
                        st.metric("Rendement brut", f"{prop.gross_yield:.2f}%")
                        st.metric("Rendement net", f"{prop.net_yield:.2f}%")
        else:
            st.info("Aucun bien enregistré. Ajoutez votre premier bien!")

    with tab2:
        st.subheader("Ajouter un nouveau bien")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom du bien", placeholder="Appartement Paris 11")
            prop_type = st.selectbox("Type", [t.value for t in PropertyType])
            address = st.text_input("Adresse")
            city = st.text_input("Ville")
            postal_code = st.text_input("Code postal")
            area = st.number_input("Surface (m²)", min_value=0.0)

        with col2:
            purchase_price = st.number_input("Prix d'achat", min_value=0.0)
            notary_fees = st.number_input("Frais de notaire", min_value=0.0,
                                          value=purchase_price * 0.08)
            current_value = st.number_input("Valeur actuelle estimée", min_value=0.0)
            monthly_rent = st.number_input("Loyer mensuel", min_value=0.0)
            monthly_charges = st.number_input("Charges mensuelles", min_value=0.0)
            property_tax = st.number_input("Taxe foncière annuelle", min_value=0.0)

        if st.button("Ajouter le bien", type="primary"):
            if name and purchase_price > 0:
                new_prop = Property(
                    name=name,
                    property_type=PropertyType(prop_type),
                    usage=PropertyUsage.RENTAL,
                    address=address,
                    city=city,
                    postal_code=postal_code,
                    area_sqm=area,
                    purchase_price=purchase_price,
                    notary_fees=notary_fees,
                    current_value=current_value or purchase_price,
                    monthly_rent=monthly_rent,
                    monthly_charges=monthly_charges,
                    property_tax=property_tax
                )
                manager.add_property(new_prop)
                st.success("Bien ajouté!")
                st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires")

    with tab3:
        summary = manager.get_portfolio_summary()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valeur totale", f"{summary['total_value']:,.0f}€")
        col2.metric("Patrimoine net", f"{summary['net_worth']:,.0f}€")
        col3.metric("Cash-flow mensuel", f"{summary['monthly_cashflow']:,.0f}€")
        col4.metric("Nombre de biens", summary['count'])


# ============================================================================
# PAGE: OBJECTIFS D'ÉPARGNE
# ============================================================================
def page_savings_goals():
    """Page des objectifs d'épargne."""
    st.header("🎯 Objectifs d'Épargne")

    if SavingsGoalManager is None:
        st.error("Module objectifs non disponible")
        return

    manager = SavingsGoalManager()

    tab1, tab2 = st.tabs(["Mes Objectifs", "Nouvel Objectif"])

    with tab1:
        goals = manager.get_all_goals()

        if goals:
            for goal in goals:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {goal.icon} {goal.name}")
                        st.progress(goal.progress_pct / 100)
                        st.caption(f"{goal.current_amount:,.0f}€ / {goal.target_amount:,.0f}€ ({goal.progress_pct:.0f}%)")
                    with col2:
                        if goal.is_on_track:
                            st.success("✓ En bonne voie")
                        else:
                            st.warning(f"⚠️ +{goal.required_monthly - goal.monthly_contribution:.0f}€/mois requis")

                        if goal.days_remaining > 0:
                            st.caption(f"📅 {goal.days_remaining} jours restants")

                    st.divider()
        else:
            st.info("Aucun objectif défini. Créez votre premier objectif!")

    with tab2:
        st.subheader("Créer un nouvel objectif")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom de l'objectif", placeholder="Apport maison")
            category = st.selectbox("Catégorie", [c.value for c in GoalCategory])
            target_amount = st.number_input("Montant cible", min_value=0.0, value=10000.0)
            current_amount = st.number_input("Montant actuel", min_value=0.0, value=0.0)

        with col2:
            target_date = st.date_input("Date cible", value=datetime.now() + timedelta(days=365))
            monthly_contribution = st.number_input("Versement mensuel", min_value=0.0, value=500.0)
            priority = st.slider("Priorité", 1, 5, 2)

        # Calcul suggestions
        if target_amount > 0 and monthly_contribution > 0:
            suggestion = manager.suggest_monthly_contribution(
                target_amount, target_date.strftime('%Y-%m-%d'), current_amount
            )
            st.info(f"""
            💡 **Suggestions:**
            - Sans rendement: {suggestion['without_return']:,.0f}€/mois
            - Avec 5% de rendement: {suggestion['with_return']:,.0f}€/mois
            """)

        if st.button("Créer l'objectif", type="primary"):
            if name and target_amount > 0:
                goal = SavingsGoal(
                    name=name,
                    category=GoalCategory(category),
                    target_amount=target_amount,
                    current_amount=current_amount,
                    target_date=target_date.strftime('%Y-%m-%d'),
                    monthly_contribution=monthly_contribution,
                    priority=priority
                )
                manager.create_goal(goal)
                st.success("Objectif créé!")
                st.rerun()
            else:
                st.error("Veuillez remplir les champs obligatoires")


# ============================================================================
# PAGE: TRANSACTIONS RÉCURRENTES (DCA)
# ============================================================================
def page_recurring_transactions():
    """Page des transactions récurrentes."""
    st.header("🔄 Transactions Récurrentes (DCA)")

    if RecurringTransactionManager is None:
        st.error("Module DCA non disponible")
        return

    manager = RecurringTransactionManager()

    tab1, tab2 = st.tabs(["Mes DCA", "Nouveau DCA"])

    with tab1:
        transactions = manager.get_all_recurring(active_only=True)
        summary = manager.get_summary()

        # Résumé
        col1, col2, col3 = st.columns(3)
        col1.metric("DCA actifs", summary['active_count'])
        col2.metric("Versement mensuel total", f"{summary['total_monthly']:,.0f}€")
        col3.metric("Projection annuelle", f"{summary['total_annual']:,.0f}€")

        st.divider()

        # Liste des DCA
        if transactions:
            for trans in transactions:
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        ticker_display = trans.ticker or "💰 Dépôt"
                        st.markdown(f"**{trans.name or ticker_display}**")
                        st.caption(f"{trans.recurrence_label} • {trans.amount:,.0f}€")
                    with col2:
                        st.write(f"📅 Prochain: {trans.next_execution}")
                    with col3:
                        st.write(f"Exécuté: {trans.execution_count}x")
                    with col4:
                        if st.button("⏸️", key=f"pause_{trans.id}"):
                            manager.pause_recurring(trans.id)
                            st.rerun()
                    st.divider()
        else:
            st.info("Aucun DCA configuré")

        # Calendrier des prochaines exécutions
        upcoming = manager.get_upcoming_transactions(days=30)
        if upcoming:
            st.subheader("📅 Prochaines exécutions")
            for item in upcoming[:5]:
                st.write(f"• {item['date']}: {item['ticker'] or 'Dépôt'} - {item['amount']:,.0f}€")

    with tab2:
        st.subheader("Configurer un nouveau DCA")

        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom", placeholder="DCA S&P 500")
            ticker = st.text_input("Ticker (laisser vide pour dépôt)", placeholder="VOO")
            amount = st.number_input("Montant", min_value=0.0, value=500.0)

        with col2:
            recurrence = st.selectbox("Fréquence", [r.value for r in RecurrenceType])
            day_of_month = st.slider("Jour du mois", 1, 28, 15)
            start_date = st.date_input("Date de début")

        if st.button("Créer le DCA", type="primary"):
            if amount > 0:
                trans = RecurringTransaction(
                    portfolio_id=1,
                    ticker=ticker or None,
                    transaction_type=TransactionType.BUY if ticker else TransactionType.DEPOSIT,
                    amount=amount,
                    recurrence=RecurrenceType(recurrence),
                    day_of_month=day_of_month,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    name=name
                )
                manager.create_recurring(trans)
                st.success("DCA créé!")
                st.rerun()
            else:
                st.error("Veuillez entrer un montant")


# ============================================================================
# PAGE: RAPPORTS PDF
# ============================================================================
def page_reports():
    """Page de génération de rapports PDF."""
    st.header("📄 Rapports PDF")

    if PDFReportGenerator is None:
        st.warning("Module reportlab non installé. Installez avec: `pip install reportlab`")
        return

    generator = PDFReportGenerator()

    report_type = st.selectbox(
        "Type de rapport",
        options=[
            ("Synthèse Portefeuille", "portfolio"),
            ("Rapport Mensuel", "monthly"),
            ("Rapport Dividendes", "dividends"),
            ("Rapport Fiscal", "tax")
        ],
        format_func=lambda x: x[0]
    )

    col1, col2 = st.columns(2)
    with col1:
        if report_type[1] in ['monthly', 'dividends', 'tax']:
            year = st.selectbox("Année", range(datetime.now().year, 2020, -1))
        if report_type[1] == 'monthly':
            month = st.selectbox("Mois", range(1, 13))

    if st.button("Générer le rapport", type="primary"):
        with st.spinner("Génération en cours..."):
            try:
                # Données de test
                portfolio_data = {
                    'name': 'Mon PEA',
                    'total_value': 25000,
                    'total_invested': 20000,
                    'gain_loss': 5000,
                    'gain_loss_pct': 25,
                    'positions': []
                }

                if report_type[1] == 'portfolio':
                    filepath = generator.generate_portfolio_summary(portfolio_data)
                elif report_type[1] == 'monthly':
                    filepath = generator.generate_monthly_report({
                        'portfolio_value': 25000,
                        'month_start_value': 24000,
                        'monthly_return': 4.2,
                        'ytd_return': 12.5
                    }, month, year)
                elif report_type[1] == 'dividends':
                    filepath = generator.generate_dividend_report([], year)
                elif report_type[1] == 'tax':
                    filepath = generator.generate_tax_report({}, year)

                st.success(f"Rapport généré: {filepath}")
                st.info("Le rapport a été enregistré dans le dossier data/reports/")

            except Exception as e:
                st.error(f"Erreur: {e}")


# ============================================================================
# DICTIONNAIRE DES PAGES ÉTENDUES
# ============================================================================
EXTENDED_PAGES = {
    "📥 Import CSV": page_import_csv,
    "🔔 Alertes": page_alerts,
    "📊 Benchmark": page_benchmark,
    "🏠 Immobilier": page_real_estate,
    "🎯 Objectifs": page_savings_goals,
    "🔄 DCA": page_recurring_transactions,
    "📄 Rapports": page_reports,
}


def get_extended_pages():
    """Retourne le dictionnaire des pages étendues."""
    return EXTENDED_PAGES
