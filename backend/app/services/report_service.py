from pathlib import Path
from reportlab.pdfgen import canvas

def simple_pdf(path: Path, title: str, lines: list[str]):
    c = canvas.Canvas(str(path))
    c.setTitle(title)
    y = 800
    c.drawString(72, y, title)
    y -= 24
    for ln in lines:
        c.drawString(72, y, ln[:100])
        y -= 18
    c.save()
