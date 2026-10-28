import os
from datetime import datetime
import mensaje as mb

from zyntra_ui import APP_NAME
from dinero import formato_dinero


def carpeta_etiquetas():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reportes", "etiquetas"))
    os.makedirs(path, exist_ok=True)
    return path


def _barcode_png(codigo, dest_sin_ext):
    try:
        import barcode
        from barcode.writer import ImageWriter
    except ImportError as error:
        raise RuntimeError("Instale python-barcode y Pillow: pip install python-barcode pillow") from error

    valor = str(codigo).zfill(8) if str(codigo).isdigit() else str(codigo)
    writer = ImageWriter()
    opciones = {
        "module_width": 0.4,
        "module_height": 18,
        "font_size": 8,
        "text_distance": 3,
        "quiet_zone": 2,
        "write_text": True,
    }
    code128 = barcode.get("code128", valor, writer=writer)
    return code128.save(dest_sin_ext, opciones)


def generar_etiqueta(codigo, nombre, precio):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as error:
        raise RuntimeError("Instale Pillow: pip install pillow") from error

    barcode_base = os.path.join(carpeta_etiquetas(), f"bc_{codigo}")
    barcode_path = _barcode_png(codigo, barcode_base)
    barra = Image.open(barcode_path).convert("RGB")

    ancho, alto = 460, 280
    img = Image.new("RGB", (ancho, alto), "white")
    draw = ImageDraw.Draw(img)
    try:
        font_b = ImageFont.truetype("arial.ttf", 18)
        font_p = ImageFont.truetype("arial.ttf", 22)
        font_s = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        font_b = font_p = font_s = ImageFont.load_default()

    draw.text((16, 10), APP_NAME, fill="#1E5AD6", font=font_s)
    titulo = str(nombre or f"Producto {codigo}")[:42]
    draw.text((16, 32), titulo, fill="black", font=font_b)
    draw.text((16, 62), formato_dinero(precio or 0), fill="black", font=font_p)

    bw, bh = barra.size
    escala = min((ancho - 40) / bw, 140 / bh)
    barra = barra.resize((max(1, int(bw * escala)), max(1, int(bh * escala))))
    x = (ancho - barra.size[0]) // 2
    img.paste(barra, (x, 100))
    draw.text((16, 250), f"Cód. {codigo}   {datetime.now().strftime('%d/%m/%Y')}", fill="#444444", font=font_s)

    salida = os.path.join(carpeta_etiquetas(), f"etiqueta_{codigo}_{datetime.now().strftime('%H%M%S')}.png")
    img.save(salida, "PNG")
    return salida


def imprimir_etiqueta(codigo, nombre, precio, parent=None):
    path = generar_etiqueta(codigo, nombre, precio)
    try:
        os.startfile(path, "print")
        mb.showinfo("Etiqueta", f"Etiqueta enviada a la impresora.\n{path}", parent=parent)
    except OSError:
        os.startfile(path)
        mb.showinfo("Etiqueta", f"Se abrió la etiqueta para imprimir.\n{path}", parent=parent)
    return path
