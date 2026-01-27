from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.db.models import PropertyTax
from app.core.config import settings
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Create PDF directory if it doesn't exist
Path(settings.PDF_DIR).mkdir(parents=True, exist_ok=True)

def generate_property_tax_pdf(tax_record: PropertyTax) -> str:
    """Generate PDF for property tax record and return file path"""
    try:
        filename = f"property_tax_{tax_record.property_id}.pdf"
        filepath = os.path.join(settings.PDF_DIR, filename)
        
        # Create PDF document
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        story = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#283593'),
            spaceAfter=12
        )
        
        normal_style = styles['Normal']
        
        # Title
        story.append(Paragraph("VMC Property Tax Receipt", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Property Details
        story.append(Paragraph("Property Details", heading_style))
        details_data = [
            ["Property ID:", tax_record.property_id],
            ["Owner Name:", tax_record.owner_name],
            ["Address:", tax_record.address],
            ["Year:", str(tax_record.year)],
            ["Amount:", f"Rs. {tax_record.amount:,.2f}"],
            ["Status:", tax_record.status.value.upper()],
        ]
        
        if tax_record.bill_no:
            details_data.append(["Bill No:", tax_record.bill_no])
        if tax_record.receipt_no:
            details_data.append(["Receipt No:", tax_record.receipt_no])
        
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Status message
        status_messages = {
            "paid": "✅ This property tax has been paid successfully.",
            "due": "⚠️ This property tax is due. Please pay at the earliest.",
            "pending": "⏳ This property tax is pending verification."
        }
        
        status_msg = status_messages.get(tax_record.status.value, "")
        if status_msg:
            story.append(Paragraph(status_msg, normal_style))
            story.append(Spacer(1, 0.2*inch))
        
        # Footer
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph("This is a system-generated document.", 
                              ParagraphStyle('Footer', parent=normal_style, fontSize=8, 
                                           textColor=colors.grey, alignment=1)))
        
        # Build PDF
        doc.build(story)
        
        logger.info(f"PDF generated: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise
