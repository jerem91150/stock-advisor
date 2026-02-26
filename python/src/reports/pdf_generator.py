"""
Générateur de rapports PDF pour Stock Advisor.
Rapports mensuels, synthèse portefeuille, performance.
"""
import io
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

# Imports conditionnels pour PDF
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, ListFlowable, ListItem
    )
    from reportlab.graphics.shapes import Drawing, Line
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.widgets.markers import makeMarker
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Classes factices pour éviter les erreurs d'import
    class TableStyle:
        pass
    class colors:
        HexColor = lambda x: None
        whitesmoke = None
        black = None
        white = None


class ReportType(Enum):
    """Types de rapports disponibles."""
    MONTHLY = "monthly"          # Rapport mensuel
    PORTFOLIO_SUMMARY = "portfolio"  # Synthèse portefeuille
    PERFORMANCE = "performance"  # Performance détaillée
    DIVIDENDS = "dividends"      # Rapport dividendes
    TAX = "tax"                  # Rapport fiscal
    FULL = "full"                # Rapport complet


class PDFReportGenerator:
    """Générateur de rapports PDF."""

    def __init__(self, output_dir: str = "data/reports"):
        """
        Initialise le générateur.

        Args:
            output_dir: Dossier de sortie pour les rapports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Configure les styles personnalisés."""
        # Titre principal
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=1  # Centre
        ))

        # Sous-titre
        self.styles.add(ParagraphStyle(
            name='SubTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#16213e')
        ))

        # Section
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#0f3460')
        ))

        # Texte normal
        self.styles.add(ParagraphStyle(
            name='BodyTextCustom',
            parent=self.styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))

        # Positive
        self.styles.add(ParagraphStyle(
            name='Positive',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#27ae60')
        ))

        # Negative
        self.styles.add(ParagraphStyle(
            name='Negative',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#e74c3c')
        ))

    def _format_currency(self, value: float, symbol: str = "€") -> str:
        """Formate une valeur monétaire."""
        return f"{value:,.2f} {symbol}".replace(",", " ")

    def _format_percentage(self, value: float, with_sign: bool = True) -> str:
        """Formate un pourcentage."""
        if with_sign and value > 0:
            return f"+{value:.2f}%"
        return f"{value:.2f}%"

    def _create_table_style(self, header_color: str = '#1a1a2e') -> TableStyle:
        """Crée un style de tableau standard."""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ])

    def generate_portfolio_summary(self, portfolio_data: Dict[str, Any],
                                    filename: Optional[str] = None) -> str:
        """
        Génère un rapport de synthèse du portefeuille.

        Args:
            portfolio_data: Données du portefeuille avec:
                - name: Nom du portefeuille
                - total_value: Valeur totale
                - total_invested: Montant investi
                - gain_loss: Plus/moins-value
                - gain_loss_pct: % de gain/perte
                - positions: Liste des positions
                - allocations: Répartition sectorielle

        Returns:
            Chemin du fichier PDF généré
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        if filename is None:
            filename = f"portfolio_summary_{datetime.now().strftime('%Y%m%d')}.pdf"

        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)

        elements = []

        # Titre
        elements.append(Paragraph(
            f"Synthèse Portefeuille: {portfolio_data.get('name', 'Mon Portefeuille')}",
            self.styles['MainTitle']
        ))
        elements.append(Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            self.styles['BodyTextCustom']
        ))
        elements.append(Spacer(1, 20))

        # Résumé financier
        elements.append(Paragraph("Vue d'ensemble", self.styles['SectionTitle']))

        total_value = portfolio_data.get('total_value', 0)
        total_invested = portfolio_data.get('total_invested', 0)
        gain_loss = portfolio_data.get('gain_loss', 0)
        gain_loss_pct = portfolio_data.get('gain_loss_pct', 0)

        summary_data = [
            ['Métrique', 'Valeur'],
            ['Valeur totale', self._format_currency(total_value)],
            ['Montant investi', self._format_currency(total_invested)],
            ['Plus/Moins-value', self._format_currency(gain_loss)],
            ['Performance', self._format_percentage(gain_loss_pct)],
        ]

        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(self._create_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Positions
        if 'positions' in portfolio_data and portfolio_data['positions']:
            elements.append(Paragraph("Détail des Positions", self.styles['SectionTitle']))

            positions_data = [['Ticker', 'Nom', 'Quantité', 'PRU', 'Prix actuel', '+/- Value', '%']]

            for pos in portfolio_data['positions']:
                gain_value = pos.get('gain_loss', 0)
                gain_pct = pos.get('gain_loss_pct', 0)

                positions_data.append([
                    pos.get('ticker', ''),
                    pos.get('name', '')[:20],  # Tronquer le nom
                    str(pos.get('quantity', 0)),
                    self._format_currency(pos.get('avg_price', 0)),
                    self._format_currency(pos.get('current_price', 0)),
                    self._format_currency(gain_value),
                    self._format_percentage(gain_pct)
                ])

            positions_table = Table(positions_data,
                                   colWidths=[50, 100, 50, 70, 70, 70, 50])
            positions_table.setStyle(self._create_table_style())
            elements.append(positions_table)

        elements.append(Spacer(1, 20))

        # Répartition
        if 'allocations' in portfolio_data and portfolio_data['allocations']:
            elements.append(Paragraph("Répartition Sectorielle", self.styles['SectionTitle']))

            alloc_data = [['Secteur', 'Poids', 'Valeur']]
            for sector, data in portfolio_data['allocations'].items():
                alloc_data.append([
                    sector,
                    self._format_percentage(data.get('weight', 0), False),
                    self._format_currency(data.get('value', 0))
                ])

            alloc_table = Table(alloc_data, colWidths=[150, 100, 150])
            alloc_table.setStyle(self._create_table_style())
            elements.append(alloc_table)

        doc.build(elements)
        return str(filepath)

    def generate_monthly_report(self, data: Dict[str, Any],
                                 month: int = None, year: int = None,
                                 filename: Optional[str] = None) -> str:
        """
        Génère un rapport mensuel.

        Args:
            data: Données incluant:
                - portfolio_value: Valeur fin de mois
                - month_start_value: Valeur début de mois
                - monthly_return: Rendement mensuel
                - ytd_return: Performance depuis début d'année
                - dividends_received: Dividendes reçus
                - transactions: Transactions du mois
                - top_performers: Meilleures performances
                - worst_performers: Pires performances
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        now = datetime.now()
        month = month or now.month
        year = year or now.year
        month_name = datetime(year, month, 1).strftime('%B %Y')

        if filename is None:
            filename = f"rapport_mensuel_{year}_{month:02d}.pdf"

        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)

        elements = []

        # Titre
        elements.append(Paragraph(
            f"Rapport Mensuel - {month_name}",
            self.styles['MainTitle']
        ))
        elements.append(Spacer(1, 20))

        # Performance du mois
        elements.append(Paragraph("Performance du Mois", self.styles['SectionTitle']))

        monthly_return = data.get('monthly_return', 0)
        perf_style = 'Positive' if monthly_return >= 0 else 'Negative'

        perf_data = [
            ['Métrique', 'Valeur'],
            ['Valeur début de mois', self._format_currency(data.get('month_start_value', 0))],
            ['Valeur fin de mois', self._format_currency(data.get('portfolio_value', 0))],
            ['Rendement mensuel', self._format_percentage(monthly_return)],
            ['Performance YTD', self._format_percentage(data.get('ytd_return', 0))],
        ]

        perf_table = Table(perf_data, colWidths=[200, 200])
        perf_table.setStyle(self._create_table_style())
        elements.append(perf_table)
        elements.append(Spacer(1, 20))

        # Dividendes
        if data.get('dividends_received'):
            elements.append(Paragraph("Dividendes Reçus", self.styles['SectionTitle']))

            div_data = [['Action', 'Date', 'Montant']]
            for div in data['dividends_received']:
                div_data.append([
                    div.get('ticker', ''),
                    div.get('date', ''),
                    self._format_currency(div.get('amount', 0))
                ])

            div_table = Table(div_data, colWidths=[100, 150, 150])
            div_table.setStyle(self._create_table_style())
            elements.append(div_table)
            elements.append(Spacer(1, 20))

        # Meilleures/Pires performances
        if data.get('top_performers'):
            elements.append(Paragraph("Top Performances", self.styles['SectionTitle']))

            top_data = [['Action', 'Performance']]
            for stock in data['top_performers'][:5]:
                top_data.append([
                    stock.get('ticker', ''),
                    self._format_percentage(stock.get('return', 0))
                ])

            top_table = Table(top_data, colWidths=[200, 200])
            top_table.setStyle(self._create_table_style('#27ae60'))
            elements.append(top_table)
            elements.append(Spacer(1, 15))

        if data.get('worst_performers'):
            elements.append(Paragraph("Moins Bonnes Performances", self.styles['SectionTitle']))

            worst_data = [['Action', 'Performance']]
            for stock in data['worst_performers'][:5]:
                worst_data.append([
                    stock.get('ticker', ''),
                    self._format_percentage(stock.get('return', 0))
                ])

            worst_table = Table(worst_data, colWidths=[200, 200])
            worst_table.setStyle(self._create_table_style('#e74c3c'))
            elements.append(worst_table)

        doc.build(elements)
        return str(filepath)

    def generate_dividend_report(self, dividends: List[Dict],
                                  year: int = None,
                                  filename: Optional[str] = None) -> str:
        """
        Génère un rapport des dividendes.

        Args:
            dividends: Liste des dividendes avec:
                - ticker, name, date, amount, tax_withheld
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        year = year or datetime.now().year

        if filename is None:
            filename = f"rapport_dividendes_{year}.pdf"

        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)

        elements = []

        # Titre
        elements.append(Paragraph(
            f"Rapport des Dividendes - {year}",
            self.styles['MainTitle']
        ))
        elements.append(Spacer(1, 20))

        # Résumé
        total_gross = sum(d.get('amount', 0) for d in dividends)
        total_tax = sum(d.get('tax_withheld', 0) for d in dividends)
        total_net = total_gross - total_tax

        summary_data = [
            ['Métrique', 'Montant'],
            ['Dividendes bruts', self._format_currency(total_gross)],
            ['Impôts retenus', self._format_currency(total_tax)],
            ['Dividendes nets', self._format_currency(total_net)],
            ['Nombre de versements', str(len(dividends))],
        ]

        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(self._create_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))

        # Détail par action
        elements.append(Paragraph("Détail des Versements", self.styles['SectionTitle']))

        if dividends:
            div_data = [['Date', 'Action', 'Brut', 'Impôt', 'Net']]
            for d in sorted(dividends, key=lambda x: x.get('date', '')):
                net = d.get('amount', 0) - d.get('tax_withheld', 0)
                div_data.append([
                    d.get('date', ''),
                    d.get('ticker', ''),
                    self._format_currency(d.get('amount', 0)),
                    self._format_currency(d.get('tax_withheld', 0)),
                    self._format_currency(net)
                ])

            div_table = Table(div_data, colWidths=[80, 80, 80, 80, 80])
            div_table.setStyle(self._create_table_style())
            elements.append(div_table)
        else:
            elements.append(Paragraph("Aucun dividende reçu cette année.",
                                      self.styles['BodyTextCustom']))

        doc.build(elements)
        return str(filepath)

    def generate_tax_report(self, data: Dict[str, Any],
                             year: int = None,
                             filename: Optional[str] = None) -> str:
        """
        Génère un rapport fiscal (plus/moins-values).

        Args:
            data: Données fiscales incluant:
                - realized_gains: Plus-values réalisées
                - realized_losses: Moins-values réalisées
                - dividends_received: Total dividendes
                - transactions: Liste des ventes
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        year = year or datetime.now().year

        if filename is None:
            filename = f"rapport_fiscal_{year}.pdf"

        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)

        elements = []

        # Titre
        elements.append(Paragraph(
            f"Rapport Fiscal - {year}",
            self.styles['MainTitle']
        ))
        elements.append(Paragraph(
            "Document à titre informatif - Consultez votre conseiller fiscal",
            self.styles['BodyTextCustom']
        ))
        elements.append(Spacer(1, 20))

        # Résumé fiscal
        elements.append(Paragraph("Synthèse Fiscale", self.styles['SectionTitle']))

        gains = data.get('realized_gains', 0)
        losses = data.get('realized_losses', 0)
        net_gain = gains - abs(losses)
        dividends = data.get('dividends_received', 0)

        # Calcul impôt (PFU 30%)
        taxable = max(0, net_gain + dividends)
        estimated_tax = taxable * 0.30

        tax_data = [
            ['Catégorie', 'Montant'],
            ['Plus-values réalisées', self._format_currency(gains)],
            ['Moins-values réalisées', self._format_currency(losses)],
            ['Plus-value nette', self._format_currency(net_gain)],
            ['Dividendes bruts', self._format_currency(dividends)],
            ['Base imposable', self._format_currency(taxable)],
            ['Impôt estimé (PFU 30%)', self._format_currency(estimated_tax)],
        ]

        tax_table = Table(tax_data, colWidths=[200, 200])
        tax_table.setStyle(self._create_table_style())
        elements.append(tax_table)
        elements.append(Spacer(1, 20))

        # Détail des ventes
        if data.get('transactions'):
            elements.append(Paragraph("Détail des Cessions", self.styles['SectionTitle']))

            trans_data = [['Date', 'Action', 'Qté', 'Prix achat', 'Prix vente', '+/- Value']]
            for t in data['transactions']:
                pv = (t.get('sell_price', 0) - t.get('buy_price', 0)) * t.get('quantity', 0)
                trans_data.append([
                    t.get('date', ''),
                    t.get('ticker', ''),
                    str(t.get('quantity', 0)),
                    self._format_currency(t.get('buy_price', 0)),
                    self._format_currency(t.get('sell_price', 0)),
                    self._format_currency(pv)
                ])

            trans_table = Table(trans_data, colWidths=[70, 70, 40, 70, 70, 80])
            trans_table.setStyle(self._create_table_style())
            elements.append(trans_table)

        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            "Note: Ce rapport est fourni à titre indicatif. Les calculs sont basés sur "
            "le Prélèvement Forfaitaire Unique (PFU) de 30%. Votre situation personnelle "
            "peut différer. Consultez un professionnel pour votre déclaration d'impôts.",
            self.styles['BodyTextCustom']
        ))

        doc.build(elements)
        return str(filepath)

    def generate_full_report(self, portfolio_data: Dict,
                              filename: Optional[str] = None) -> str:
        """
        Génère un rapport complet combinant tous les rapports.

        Args:
            portfolio_data: Toutes les données du portefeuille
        """
        if not REPORTLAB_AVAILABLE:
            return ""

        if filename is None:
            filename = f"rapport_complet_{datetime.now().strftime('%Y%m%d')}.pdf"

        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)

        elements = []

        # Page de titre
        elements.append(Spacer(1, 100))
        elements.append(Paragraph("Stock Advisor", self.styles['MainTitle']))
        elements.append(Paragraph("Rapport Complet", self.styles['SubTitle']))
        elements.append(Spacer(1, 50))
        elements.append(Paragraph(
            f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            self.styles['BodyTextCustom']
        ))
        elements.append(PageBreak())

        # Table des matières
        elements.append(Paragraph("Table des Matières", self.styles['SubTitle']))
        elements.append(Spacer(1, 20))
        toc = [
            "1. Synthèse du Portefeuille",
            "2. Performance et Benchmark",
            "3. Détail des Positions",
            "4. Dividendes",
            "5. Analyse Fiscale",
            "6. Recommandations"
        ]
        for item in toc:
            elements.append(Paragraph(item, self.styles['BodyTextCustom']))
        elements.append(PageBreak())

        # Section 1: Synthèse
        elements.append(Paragraph("1. Synthèse du Portefeuille", self.styles['SubTitle']))
        elements.append(Spacer(1, 20))

        summary_data = [
            ['Métrique', 'Valeur'],
            ['Valeur totale', self._format_currency(portfolio_data.get('total_value', 0))],
            ['Montant investi', self._format_currency(portfolio_data.get('total_invested', 0))],
            ['Performance globale', self._format_percentage(portfolio_data.get('total_return_pct', 0))],
            ['Nombre de positions', str(len(portfolio_data.get('positions', [])))],
        ]
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(self._create_table_style())
        elements.append(summary_table)
        elements.append(PageBreak())

        # Section 2: Performance
        elements.append(Paragraph("2. Performance et Benchmark", self.styles['SubTitle']))
        elements.append(Spacer(1, 20))

        if 'benchmark_comparison' in portfolio_data:
            bench = portfolio_data['benchmark_comparison']
            bench_data = [
                ['Benchmark', 'Portfolio', 'Benchmark', 'Alpha'],
                [bench.get('name', 'S&P 500'),
                 self._format_percentage(bench.get('portfolio_return', 0)),
                 self._format_percentage(bench.get('benchmark_return', 0)),
                 self._format_percentage(bench.get('alpha', 0))],
            ]
            bench_table = Table(bench_data, colWidths=[100, 100, 100, 100])
            bench_table.setStyle(self._create_table_style())
            elements.append(bench_table)
        elements.append(PageBreak())

        # Section 3: Positions
        elements.append(Paragraph("3. Détail des Positions", self.styles['SubTitle']))
        elements.append(Spacer(1, 20))

        if portfolio_data.get('positions'):
            pos_data = [['Ticker', 'Qté', 'PRU', 'Prix', '+/- Value', '%']]
            for pos in portfolio_data['positions']:
                pos_data.append([
                    pos.get('ticker', ''),
                    str(pos.get('quantity', 0)),
                    self._format_currency(pos.get('avg_price', 0)),
                    self._format_currency(pos.get('current_price', 0)),
                    self._format_currency(pos.get('gain_loss', 0)),
                    self._format_percentage(pos.get('gain_loss_pct', 0))
                ])
            pos_table = Table(pos_data, colWidths=[60, 50, 70, 70, 80, 60])
            pos_table.setStyle(self._create_table_style())
            elements.append(pos_table)

        doc.build(elements)
        return str(filepath)


# Test
if __name__ == "__main__":
    print("=== Test PDF Generator ===\n")

    if not REPORTLAB_AVAILABLE:
        print("ReportLab non installé. Test impossible.")
    else:
        generator = PDFReportGenerator()

        # Test synthèse portefeuille
        portfolio_data = {
            'name': 'Mon PEA',
            'total_value': 25680.50,
            'total_invested': 20000,
            'gain_loss': 5680.50,
            'gain_loss_pct': 28.4,
            'positions': [
                {'ticker': 'AAPL', 'name': 'Apple Inc.', 'quantity': 10,
                 'avg_price': 150, 'current_price': 178.50, 'gain_loss': 285, 'gain_loss_pct': 19},
                {'ticker': 'MSFT', 'name': 'Microsoft Corp.', 'quantity': 5,
                 'avg_price': 300, 'current_price': 380, 'gain_loss': 400, 'gain_loss_pct': 26.7},
            ],
            'allocations': {
                'Technology': {'weight': 45, 'value': 11556},
                'Healthcare': {'weight': 25, 'value': 6420},
                'Finance': {'weight': 30, 'value': 7704},
            }
        }

        filepath = generator.generate_portfolio_summary(portfolio_data)
        print(f"✅ Rapport généré: {filepath}")
