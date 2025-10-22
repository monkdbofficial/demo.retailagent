"""
PDF Exporter Module
Generate professional PDF reports with charts and insights.
"""

import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from datetime import datetime
from typing import Dict, Any, List
import os

logger = logging.getLogger(__name__)

class PDFExporter:
    """
    Professional PDF report generator with polished styling.
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.styles = getSampleStyleSheet()

        # Enhanced custom styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#003366'),
            spaceAfter=36,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#004080'),
            spaceAfter=18,
            spaceBefore=18,
            fontName='Helvetica-Bold'
        )

        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['BodyText'],
            fontSize=12,
            alignment=TA_JUSTIFY,
            spaceAfter=14
        )

        self.footer_style = ParagraphStyle(
            'Footer',
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceBefore=0
        )

    def _footer(self, canvas, doc):
        canvas.saveState()
        footer_text = f"Page {doc.page}"
        width, height = letter
        canvas.setFont('Helvetica', 9)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(width / 2.0, 0.5 * inch, footer_text)
        canvas.restoreState()

    def generate_report(self, insights: Dict[str, Any], 
                        chart_paths: List[str] = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"product_analysis_report_{timestamp}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        try:
            doc = SimpleDocTemplate(filepath, pagesize=letter,
                                    rightMargin=0.75*inch,leftMargin=0.75*inch,
                                    topMargin=1*inch,bottomMargin=1*inch)

            story = []

            # Cover Page
            story.append(Spacer(1, 2*inch))
            cover_title = Paragraph("Product Analytics Report", self.title_style)
            story.append(cover_title)
            report_date = datetime.now().strftime('%B %d, %Y at %H:%M')
            story.append(Spacer(1, 0.25*inch))
            cover_subtitle = Paragraph(f"Generated on: {report_date}", self.body_style)
            story.append(cover_subtitle)
            story.append(PageBreak())

            # Executive Summary
            story.append(Paragraph("Executive Summary", self.heading_style))
            summary = insights.get('executive_summary', 'No summary available.')
            story.append(Paragraph(summary, self.body_style))
            story.append(Spacer(1, 0.3*inch))

            # Key Metrics as table
            story.append(Paragraph("Key Metrics", self.heading_style))
            metrics = insights.get('summary_stats', {})
            if metrics:
                data = [
                    ['Metric', 'Value'],
                    ['Total Products', f"{metrics.get('total_products', 0):,}"],
                    ['Total Brands', f"{metrics.get('total_brands', 0):,}"],
                    ['Average Price', f"₹{metrics.get('avg_price', 0):.2f}"],
                    ['Average Rating', f"{metrics.get('avg_rating', 0):.2f}"],
                    ['Average Discount', f"{metrics.get('avg_discount', 0):.1f}%"]
                ]
                table = Table(data, colWidths=[3*inch, 2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0073b2')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 13),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.5*inch))

            # AI Insights
            story.append(Paragraph("AI-Generated Insights", self.heading_style))
            ai_insights = insights.get('ai_insights', 'No insights available.')
            story.append(Paragraph(ai_insights, self.body_style))
            story.append(Spacer(1, 0.4*inch))

            # Chart Section
            if chart_paths:
                story.append(PageBreak())
                story.append(Paragraph("Data Visualizations", self.heading_style))
                for chart_path in chart_paths:
                    if os.path.exists(chart_path):
                        try:
                            img = Image(chart_path, width=6*inch, height=4*inch)
                            story.append(img)
                            story.append(Spacer(1, 0.25*inch))
                        except Exception as e:
                            logger.warning(f"Could not add chart {chart_path}: {e}")

            # Build with footer
            doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)

            logger.info(f"✅ PDF report generated: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"❌ PDF generation failed: {e}")
            return ""
