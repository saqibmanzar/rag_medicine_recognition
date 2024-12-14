import sys
import os
from io import BytesIO
from PyPDF2 import PdfWriter, PdfReader, PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import tempfile
import textwrap

# Function to write data to PDF using ReportLab
def write_to_pdf(data, filename):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        c = canvas.Canvas(temp_pdf.name, pagesize=letter)
        width, height = letter
        
        def draw_wrapped_text(text, x, y, max_width, font, font_size):
            c.setFont(font, font_size)
            wrapped_text = textwrap.wrap(text, width=max_width)
            for line in wrapped_text:
                c.drawString(x, y, line)
                y -= font_size + 2
                if y < 50:  # Add new page if needed
                    c.showPage()
                    c.setFont(font, font_size)
                    y = height - 50
            y -= 10  # Extra spacing after text block
            return y

        def draw_content(content, x, y, level=0):
            indent = 20 * level
            if isinstance(content, dict):
                for key, value in content.items():
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(x + indent, y, key)
                    y -= 20  # Extra space after header
                    if y < 50:
                        c.showPage()
                        y = height - 50
                    y = draw_content(value, x, y, level + 1)
            else:
                y = draw_wrapped_text(content, x + indent, y, max_width=80, font="Helvetica", font_size=10)
            y -= 10  # Extra space after each content block
            return y

        # Start drawing content
        start_x, start_y = 50, height - 50
        draw_content(data, start_x, start_y)
        c.save()

        # Merge the generated content into a single PDF
        pdf_writer = PdfWriter()
        pdf_reader = PdfReader(temp_pdf.name)
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)
        
        server_path = os.path.dirname(os.path.realpath(__file__))
        filepath = os.path.join(server_path, "../output_pdf", filename+".pdf")
        with open(filepath, "wb") as output_pdf:
            pdf_writer.write(output_pdf)
        
        print(f"Content saved to {filename}")
        print("----------------------------------------")

