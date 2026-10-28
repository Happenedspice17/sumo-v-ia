"""Genera manual_ensamble.pdf (manual de armado), manual_uso.pdf, bom.csv y cables.csv.

Uso: python3 docs/generar_manuales.py
Usa las imagenes de chasis/img/ (python3 chasis/renders.py) y la lista de cables que
chasis.scad imprime con openscad. Si no hay openscad, usa docs/cables.csv.
"""
import csv
import os
import re
import shutil
import subprocess
import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
IMG = os.path.join(RAIZ, "chasis", "img")
SCAD = os.path.join(RAIZ, "chasis", "chasis.scad")

# ---------- Estilos ----------
FUENTE, NEGRITA, CURSIVA = "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
for f, n in (("DejaVuSans.ttf", "DV"), ("DejaVuSans-Bold.ttf", "DVB"), ("DejaVuSans-Oblique.ttf", "DVI")):
    ruta = os.path.join("/usr/share/fonts/truetype/dejavu", f)
    if os.path.exists(ruta):
        pdfmetrics.registerFont(TTFont(n, ruta))
if "DV" in pdfmetrics.getRegisteredFontNames():
    FUENTE, NEGRITA = "DV", "DVB"
    CURSIVA = "DVI" if "DVI" in pdfmetrics.getRegisteredFontNames() else "DV"
    pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic=CURSIVA, boldItalic="DVB")

AZUL = colors.HexColor("#1f4e79")
AZUL_OSC = colors.HexColor("#14213d")
ORO = colors.HexColor("#c8902a")
FILA = colors.HexColor("#f3f5f8")
REJILLA = colors.HexColor("#c3c9d2")
VERIFICA = colors.HexColor("#e8eef9")
AVISO = colors.HexColor("#fff4e5")
ANCHO = 176 * mm

base = getSampleStyleSheet()
S = {
    "t": ParagraphStyle("t", parent=base["Title"], fontName=NEGRITA, fontSize=30, leading=36, textColor=AZUL,
                        alignment=0, spaceAfter=4),
    "st": ParagraphStyle("st", parent=base["Normal"], fontName=FUENTE, fontSize=14, leading=19, textColor=AZUL_OSC),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=NEGRITA, fontSize=19, leading=24,
                         textColor=AZUL, spaceBefore=8, spaceAfter=6),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=NEGRITA, fontSize=13, leading=17,
                         textColor=AZUL_OSC, spaceBefore=8, spaceAfter=4),
    "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName=NEGRITA, fontSize=11.5, leading=15,
                         textColor=AZUL_OSC, spaceBefore=6, spaceAfter=3),
    "p": ParagraphStyle("p", parent=base["Normal"], fontName=FUENTE, fontSize=10, leading=14, spaceAfter=4),
    "pz": ParagraphStyle("pz", parent=base["Normal"], fontName=FUENTE, fontSize=8.6, leading=11.5, spaceAfter=4),
    "li": ParagraphStyle("li", parent=base["Normal"], fontName=FUENTE, fontSize=10, leading=14,
                         leftIndent=14, bulletIndent=2, spaceAfter=3),
    "c": ParagraphStyle("c", parent=base["Normal"], fontName=FUENTE, fontSize=8.6, leading=11),
    "cb": ParagraphStyle("cb", parent=base["Normal"], fontName=NEGRITA, fontSize=8.6, leading=11,
                         textColor=colors.white),
    "fig": ParagraphStyle("fig", parent=base["Normal"], fontName=CURSIVA, fontSize=9, leading=12,
                          textColor=AZUL_OSC, alignment=1, spaceAfter=6),
    "pie": ParagraphStyle("pie", parent=base["Normal"], fontName=FUENTE, fontSize=8.5, leading=11,
                          textColor=colors.HexColor("#666"), alignment=1),
}


def p(t):
    return Paragraph(t, S["p"])


def h1(t):
    return Paragraph(t, S["h1"])


def h2(t):
    return Paragraph(t, S["h2"])


def h3(t):
    return Paragraph(t, S["h3"])


def fig(t):
    return Paragraph(t, S["fig"])


def lista(items, num=False):
    return [Paragraph(t, S["li"], bulletText=f"{i}." if num else "•") for i, t in enumerate(items, 1)]


def tabla(filas, anchos, cabecera=True):
    datos = [[Paragraph(str(c), S["cb"] if (cabecera and i == 0) else S["c"]) for c in f] for i, f in enumerate(filas)]
    escala = ANCHO / (sum(anchos) * mm) if sum(anchos) * mm > ANCHO else 1
    t = Table(datos, colWidths=[a * mm * escala for a in anchos], repeatRows=1 if cabecera else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.5, REJILLA),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if cabecera:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
        estilo += [("BACKGROUND", (0, i), (-1, i), FILA) for i in range(2, len(filas), 2)]
    t.setStyle(TableStyle(estilo))
    return t


def caja(texto, color=AVISO, ancho=ANCHO, borde=colors.HexColor("#e0a050")):
    t = Table([[Paragraph(texto, S["p"])]], colWidths=[ancho])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), 0.5, borde),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def verifica(texto, ancho=ANCHO):
    t = Table([[Paragraph("<b>Verifica:</b> " + texto, S["p"])]], colWidths=[ancho])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERIFICA),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def img(ruta, ancho_mm, alto_max_mm=None):
    if not os.path.isabs(ruta):
        ruta = os.path.join(IMG, ruta)
    if not os.path.exists(ruta):
        return p(f"[falta imagen {os.path.basename(ruta)}]")
    i = Image(ruta)
    escala = ancho_mm * mm / i.imageWidth
    if alto_max_mm and i.imageHeight * escala > alto_max_mm * mm:
        escala = alto_max_mm * mm / i.imageHeight
    i.drawWidth, i.drawHeight = i.imageWidth * escala, i.imageHeight * escala
    return i


def lado_a_lado(izq, der, a_izq=96, a_der=80):
    """Texto a la izquierda, imagen a la derecha (como en el manual de la prensa)."""
    t = Table([[izq, der]], colWidths=[a_izq * mm, a_der * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (1, 0), (1, 0), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t


def raya():
    t = Table([[""]], colWidths=[ANCHO], rowHeights=[2])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#d5d9de"))]))
    return t


def bloque(izq, imagen, a_img, alto_img):
    """Texto completo y debajo la imagen con sus etiquetas, centrada."""
    if not imagen:
        return [*izq, Spacer(1, 4), raya(), Spacer(1, 2)]
    i = img(imagen, a_img, alto_img)
    t = Table([[i]], colWidths=[ANCHO], style=[("ALIGN", (0, 0), (-1, -1), "CENTER")])
    return [KeepTogether([*izq, Spacer(1, 3), t]), Spacer(1, 4), raya(), Spacer(1, 2)]


def paso(titulo, piezas, items, nota_ver, imagen, herramienta=None, a_img=165, alto_img=100, extra=None):
    izq = [Paragraph(titulo, S["h2"])]
    linea = f"<b>Piezas:</b> {piezas}"
    if herramienta:
        linea += f" <b>Herramienta:</b> {herramienta}"
    izq.append(Paragraph(linea, S["pz"]))
    izq += lista(items, num=True)
    if extra:
        izq += extra
    if nota_ver:
        izq += [Spacer(1, 3), verifica(nota_ver)]
    return bloque(izq, imagen, a_img, alto_img)


def sub(titulo, items, nota_ver, imagen, a_img=165, alto_img=95, num=True, intro=None):
    izq = [Paragraph(titulo, S["h3"])]
    if intro:
        izq.append(p(intro))
    izq += lista(items, num=num)
    if nota_ver:
        izq += [Spacer(1, 3), verifica(nota_ver)]
    return bloque(izq, imagen, a_img, alto_img)


def marco(titulo):
    def dibujar(c, doc):
        c.saveState()
        an, al = doc.pagesize
        c.setStrokeColor(ORO)
        c.setLineWidth(1.2)
        c.line(20 * mm, al - 13 * mm, an - 20 * mm, al - 13 * mm)
        c.setFont(FUENTE, 8)
        c.setFillColor(AZUL_OSC)
        c.drawString(20 * mm, 10 * mm, f"{titulo} · Robot de laberinto")
        c.drawRightString(an - 20 * mm, 10 * mm, f"{doc.page}")
        c.restoreState()
    return dibujar


def construir(nombre, titulo, historia):
    doc = SimpleDocTemplate(os.path.join(AQUI, nombre), pagesize=letter, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=20 * mm, bottomMargin=18 * mm, title=titulo, author="Equipo robot laberinto")
    doc.build(historia, onFirstPage=marco(titulo), onLaterPages=marco(titulo))
    print("Generado", nombre)


# ---------- Datos ----------
BOM_IMP = [
    # pieza, material, proceso, cant
    ["Piso 1 (base, columnas, postes del L298N, soportes de VL53L0X y topes)", "PETG o PLA", "Impresión 3D", "1"],
    ["Piso 2 (marcos de protoboards y OLED)", "PETG o PLA", "Impresión 3D", "1"],
    ["Cuna de motor", "PETG o PLA", "Impresión 3D", "2"],
    ["Capucha del sensor de color con patín delantero", "PLA negro", "Impresión 3D", "1"],
    ["Patín trasero", "PETG o PLA", "Impresión 3D", "1"],
    ["Pieza de prueba de tolerancias", "El mismo de las demás", "Impresión 3D (primero)", "1"],
]
BOM_ELEC = [
    ["Arduino Nano USB-C", "ATmega328P, CH340, con headers soldados; cable USB-C de datos", "1"],
    ["Motorreductor N20", "6 V, 300–500 RPM, sin encoder", "2"],
    ["Rueda para N20", "Ø34 × 20 mm, eje D de 3 mm", "2"],
    ["Puente H L298N", "Módulo rojo 43 × 43 mm con disipador", "1"],
    ["Sensor de color TCS34725", "Módulo morado 20.5 × 20.5 mm", "1"],
    ["Sensor de distancia VL53L0X", "CJVL53L0XV2, 25 × 10.7 mm", "3"],
    ["Pantalla OLED SSD1306", "0.96\", I2C, dirección 0x3C, 4 pines", "1"],
    ["Botón de panel", "Ø7 mm, normalmente abierto", "1"],
    ["Interruptor de palanca", "MTS-102, Ø6 mm", "1"],
    ["Batería 2S 18650", "7.4 V, 3000 mAh, conector T y balanceo JST-XH", "1"],
    ["Conector T (Deans) hembra", "Con 10 cm de cable calibre 14–16", "1"],
    ["Cargador balanceador 2S", "Entrada JST-XH de 3 pines", "1"],
    ["Mini protoboard", "170 puntos, 35 × 47 mm, con adhesivo", "2"],
    ["Capacitor cerámico", "100 nF (104)", "2"],
    ["Header macho recto", "2.54 mm, tira de 40 (los rectos de siempre)", "1"],
]
BOM_CABLES = [
    ["Dupont hembra-macho 30 cm", "VL53L0X (3 × 5), OLED (4), L298N lógica (6) + 2 de repuesto", "27"],
    ["Dupont macho-macho 30 cm", "Se les corta un extremo: TCS34725 (4) y botón (2)", "6"],
    ["Cable calibre 22 de silicón, rojo, negro, amarillo, blanco y naranja", "Motores, interruptor, batería y Nano", "1 m en total por color"],
    ["Jumpers rígidos de protoboard", "Puentes del bus y del Nano al bus", "8"],
    ["Cinchos chicos y termofit de 3 mm", "Ordenar cables y aislar soldaduras", "10 / 30 cm"],
]
BOM_TORN = [
    ["Inserto de calor M3 (latón)", "16", "Columnas (4) y postes del L298N (4) del piso 1, cunas (4), capucha (2), patín (2)"],
    ["Tornillo Allen M3 × 8", "12", "L298N (4), piso 2 (4), capucha (2), patín (2)"],
    ["Tornillo Allen M3 × 12", "4", "Cunas de motor"],
    ["Velcro adhesivo 3 × 5 cm", "1", "Bajo la batería"],
    ["Nota", "—", "Del kit M2–M5 solo se usan Allen M3 de 8 y 12 mm; sin tuercas, rondanas ni separadores"],
]
HERRAMIENTAS = [
    ["Imprimir", "Bambu Lab A2L o X2D, boquilla de 0.4 mm, PETG o PLA, Bambu Studio"],
    ["Soldar", "Cautín de 30–60 W con punta fina, soldadura 60/40 de 0.8 mm, termofit, encendedor o pistola de calor"],
    ["Cables", "Pinzas de corte, pelacables calibre 22, pinzas de punta"],
    ["Insertos", "El mismo cautín con punta cónica o punta para insertos M3"],
    ["Armado", "Llave Allen de 2.5 mm (M3), desarmador plano de 2.5 mm (bornes del L298N)"],
    ["Medir", "Multímetro, vernier"],
    ["Programar", "Computadora con Microchip Studio 7 y avrdude (manual de uso)"],
]

TIPO = [  # prefijo del nombre del cable -> tipo y largo a cortar
    ("Motor", "Calibre 22 soldado al motor"),
    ("Conector T", "Calibre 22 (viene con el conector T)"),
    ("Interruptor", "Calibre 22 soldado al interruptor"),
    ("L298N GND", "Calibre 22"),
    ("L298N", "Dupont hembra-macho 30 cm"),
    ("VL53L0X", "Dupont hembra-macho 30 cm"),
    ("OLED", "Dupont hembra-macho 30 cm"),
    ("TCS34725", "Dupont macho-macho 30 cm sin un extremo, soldado"),
    ("Boton", "Dupont macho-macho 30 cm sin un extremo, soldado"),
    ("Puente", "Jumper rígido de protoboard"),
]
COLOR_ES = {"red": "rojo", "black": "negro", "orange": "naranja", "yellow": "amarillo", "white": "blanco",
            "cyan": "cian", "royalblue": "azul", "green": "verde", "hotpink": "rosa", "mediumpurple": "morado",
            "sienna": "café"}


def leer_cables():
    """Lista de cables desde chasis.scad (echo de cable()); se guarda en cables.csv."""
    csv_ruta = os.path.join(AQUI, "cables.csv")
    if shutil.which("openscad"):
        with tempfile.TemporaryDirectory() as tmp:
            eco = os.path.join(tmp, "e.echo")
            subprocess.run(["openscad", "-o", eco, SCAD], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            crudos = [re.match(r'ECHO: "CABLE\|(.*)\|(.*)\|(\d+)"', l) for l in open(eco)]
        crudos = [(m[1], m[2], int(m[3])) for m in crudos if m]
        completos = {n: [n, c, mm_] for n, c, mm_ in crudos if not n.endswith(" (abajo)")}
        for n, c, mm_ in crudos:
            if n.endswith(" (abajo)"):
                b = n[:-len(" (abajo)")]
                dest = completos.get(b) or next(v for k, v in completos.items() if k.startswith(b + " -> "))
                dest[2] += mm_
        filas = []
        for n, c, mm_ in completos.values():
            de, a = n.split(" -> ") if " -> " in n else (n, "otra mitad de su columna")
            tipo = next(t for pre, t in TIPO if n.startswith(pre))
            filas.append([de.replace("Boton", "Botón"), a, COLOR_ES.get(c, c), tipo, mm_])
        orden = ["Motor", "Conector", "Interruptor", "L298N GND", "L298N", "VL53L0X izq", "VL53L0X frente",
                 "VL53L0X der", "TCS", "OLED", "Botón", "Puente"]
        filas.sort(key=lambda f: next(i for i, o in enumerate(orden) if f[0].startswith(o)))
        with open(csv_ruta, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["De", "A", "Color", "Tipo", "Largo en el modelo (mm)"])
            w.writerows(filas)
        print("Generado cables.csv")
    with open(csv_ruta, encoding="utf-8") as f:
        return [r[:4] + [int(r[4])] for r in list(csv.reader(f))[1:]]


def escribir_csv():
    with open(os.path.join(AQUI, "bom.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Categoria", "Componente", "Especificacion / donde va", "Cantidad"])
        for r in BOM_IMP:
            w.writerow(["Impresa 3D", r[0], r[1], r[3]])
        for r in BOM_ELEC:
            w.writerow(["Electronica", r[0], r[1], r[2]])
        for r in BOM_CABLES:
            w.writerow(["Cables", r[0], r[1], r[2]])
        for r in BOM_TORN[:-1]:
            w.writerow(["Tornilleria", r[0], r[2], r[1]])
    print("Generado bom.csv")


# ---------- Manual de armado ----------
def manual_ensamble():
    cables = leer_cables()
    H = []

    # Portada
    H += [Spacer(1, 22 * mm), Paragraph("Manual de armado", S["t"]),
          Paragraph("Robot de laberinto — Arduino Nano (ATmega328P), chasis impreso de 120 × 120 mm en dos pisos, "
                    "sensores I2C deslizables y cableado completo", S["st"]),
          Spacer(1, 8 * mm), img("iso.png", 150, 120), Spacer(1, 10 * mm),
          p("<b>Equipo:</b> ______________________________________________________________"),
          Paragraph("Microcontroladores 2 · Archivos de referencia: <i>chasis/chasis.scad</i>, <i>chasis/stl/</i>, "
                    "<i>docs/bom.csv</i> y <i>docs/cables.csv</i>", S["pz"]),
          PageBreak()]

    # 1. Como funciona
    H += [h1("1. Cómo funciona"),
          p("Tres VL53L0X miden las paredes a la izquierda, al frente y a la derecha; el Arduino Nano guarda el mapa del "
            "laberinto y elige el camino con flood-fill. Las dos ruedas con motor N20 las mueve el puente H L298N, con "
            "PWM del Timer0. Un TCS34725 mira el piso por una capucha y cuenta las marcas de color, que se ven en la "
            "OLED. Todos los sensores y la OLED comparten un solo bus I2C armado en una mini protoboard. Abajo van "
            "motores, batería y L298N; arriba, la electrónica de control."),
          Table([[img("iso.png", 62, 60), img("fig_atras.png", 56, 60), img("fig_lado.png", 52, 60)]],
                colWidths=[63 * mm, 58 * mm, 55 * mm],
                style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]),
          fig("Fig. 1. Robot completo con todos sus cables: frente, atrás y lado."),
          tabla([["Dato", "Valor"],
                 ["Huella", "120 × 120 mm con ruedas (esquinas de R30 para girar en pasillos de 180 mm)"],
                 ["Alto", "≈ 95 mm con los dupont parados en las protoboards"],
                 ["Pisos", "Piso 1 a 22 mm del suelo; piso 2 sobre 4 columnas impresas de 35 mm"],
                 ["Alimentación", "Batería 2S 18650 (7.4 V) → interruptor → L298N (12V) y VIN del Nano"],
                 ["Bus I2C", "VL53L0X × 3 (direcciones 0x30–0x32), TCS34725 (0x29), OLED (0x3C), 400 kHz"],
                 ["Piezas", "≈ 125 en total: 7 impresas, 16 tornillos, 16 insertos, 85 cables"]], [45, 131]),
          h1("2. Herramientas"),
          tabla([["Para", "Herramienta"], *HERRAMIENTAS], [30, 146]),
          PageBreak()]

    # 3. Lista de piezas
    H += [h1("3. Lista de piezas"), h2("Piezas a fabricar"),
          tabla([["Pieza", "Material", "Proceso", "Cant."], *BOM_IMP], [85, 35, 42, 14]),
          h2("Componentes comerciales"),
          tabla([["Componente", "Especificación", "Cant."], *BOM_ELEC], [52, 110, 14]),
          h2("Cables"),
          tabla([["Cable", "Para qué", "Cant."], *BOM_CABLES], [70, 80, 26]),
          p("La lista completa, cable por cable, con su color y su largo, está en el <b>Anexo A</b>."),
          h2("Tornillería"),
          tabla([["Elemento", "Cant.", "Dónde va"], *BOM_TORN], [58, 14, 104]),
          PageBreak()]

    # 4. Preparacion de piezas
    H += [h1("4. Preparación de piezas"), h2("4.1 Impresión 3D"),
          p("Las holguras del modelo están ajustadas para la <b>Bambu Lab A2L</b> (cama móvil, boquilla de 0.4 mm): "
            "ahí los agujeros salen unos 0.1 mm chicos y las ranuras unos 0.15 mm angostas. Todas las piezas caben "
            "en una sola placa de <b>256 × 256 mm</b>, la cama de la <b>X2D</b>: archivo "
            "<i>chasis/stl/placa_x2d.stl</i> (en Bambu Studio: clic derecho → <i>Dividir en objetos</i>)."),
          lado_a_lado([
              tabla([["Ajuste", "Valor"],
                     ["Boquilla / capa", "0.4 mm / 0.2 mm"],
                     ["Paredes / capas sup. e inf.", "4 / 4"],
                     ["Relleno", "25 % giroide"],
                     ["Soportes", "No"],
                     ["Pata de elefante", "0.15 mm"],
                     ["Compensación X-Y de agujeros", "0 (ya está en el modelo)"],
                     ["Costura", "Atrás, alineada"],
                     ["Placa", "Textured PEI"]], [42, 50])],
              [img("placa_x2d.png", 76, 76), fig("Fig. 2. Placa completa en la cama de 256 × 256 de la X2D.")], 96, 80),
          Spacer(1, 4),
          tabla([["Pieza", "Orientación en la cama", "Ajustes sugeridos", "Soportes"],
                 ["Piso 1", "Plano, columnas hacia arriba", "PETG, 4 paredes, 25 %", "No"],
                 ["Piso 2", "Plano, marcos hacia arriba", "PETG, 4 paredes, 25 %", "No"],
                 ["Cuna de motor (2)", "Base abajo, hueco del motor arriba", "PETG, 4 paredes, 40 %", "No"],
                 ["Capucha de color", "Orejas sobre la cama, patín arriba", "PLA negro, 4 paredes, 30 %", "No"],
                 ["Patín trasero", "Barra sobre la cama, domo arriba", "PETG, 4 paredes, 40 %", "No"]], [36, 62, 52, 26]),
          *lista([
              "Imprime primero la <b>pieza de prueba</b> (<i>chasis/stl/prueba.stl</i>), sola, con los mismos ajustes.",
              "Agujeros de arriba: M3 de 3.2, 3.4 y 3.6. El tornillo debe pasar libre en el de 3.4.",
              "Bloque de insertos: agujeros de 3.8, 4.0 y 4.2. Usa el que deja el inserto firme y a ras; si no es "
              "el de 4.0, cambia INSERTO en chasis.scad y exporta otra vez.",
              "Agujeros grandes: botón (7.3) e interruptor (6.3). Bloque: el N20 entra empujando con el dedo.",
              "Soporte de VL53L0X: el sensor, ya con sus dupont, baja sin forzar y no baila. Si entra apretado, sube "
              "RANURA a 2.1 en chasis.scad; si baila, bájala a 1.9.",
              "Si cambias algo, exporta otra vez: <font face='Courier' size='8'>openscad -D 'PIEZA=\"placa\"' "
              "-o placa_x2d.stl chasis/chasis.scad</font>.",
          ]),
          CondPageBreak(60 * mm),
          h2("4.2 Insertos de calor"),
          p("Todos los tornillos roscan en insertos de latón M3: se ponen antes de armar, con las piezas frías."),
          *lista([
              "Cautín a 220 °C para PLA o 245 °C para PETG, con punta cónica.",
              "Pon el inserto derecho en la boca del agujero, lado angosto abajo.",
              "Empuja sin forzar: entra solo con el calor en 5–10 s. Para cuando quede a ras.",
              "Antes de que enfríe, aplánalo con algo metálico frío para dejarlo parejo.",
              "Piso 1: arriba de las 4 columnas y de los 4 postes del L298N. Cunas: en la cara de las orejas. "
              "Capucha y patín: en la cara que va contra el piso 1.",
          ], num=True),
          img("det_insertos.png", 165, 85), fig("Fig. 3. Los 16 insertos (dorados)."),
          CondPageBreak(60 * mm),
          h2("4.3 Soldadura"),
          *lista([
              "<b>Motores:</b> suelda un capacitor de 100 nF entre las dos terminales de cada N20. Luego un cable "
              "amarillo (+) y uno blanco (−) de 10 cm a cada motor. Termofit en cada terminal.",
              "<b>VL53L0X (3):</b> header recto de 6 pines con el <b>plástico del lado sin chip</b>; las puntas cortas se "
              "sueldan del lado del chip. Recorta lo que sobresalga más de 1.5 mm.",
              "<b>TCS34725:</b> a 4 dupont macho-macho de 30 cm córtales un extremo. Suelda las puntas cortadas a VIN (rojo), GND "
              "(negro), SCL (cian) y SDA (azul), saliendo hacia el borde de los pines. No lleva header.",
              "<b>Botón:</b> igual, un dupont rosa y uno negro sin un extremo, uno en cada pata.",
              "<b>Interruptor (arnés de potencia):</b> rojo del conector T hembra a una pata exterior; a la pata "
              "central, dos cables naranjas de 10 cm (uno al L298N y otro al Nano). Termofit en las tres patas.",
              "<b>Conector T hembra:</b> su cable negro va directo al L298N; el rojo es el que se soldó al interruptor.",
          ]),
          h2("4.4 Preparar cables"),
          *lista([
              "Pela 6 mm de cada cable calibre 22 que va a un borne y estáñalo.",
              "Para la protoboard, el naranja de VIN y el negro de GND del Nano: pela 8 mm y estáñalos para que entren rectos.",
              "Respeta los colores de la Fig. 4: así revisar el cableado al final es comparar colores.",
          ]),
          img(os.path.join(RAIZ, "atmega328p", "img", "conexiones_nano.png"), 170),
          fig("Fig. 4. Diagrama de conexiones. Los colores son los mismos que los de los cables del modelo."),
          PageBreak()]

    # 5. Armado paso a paso
    H += [h1("5. Armado paso a paso"),
          Paragraph("En cada imagen, las piezas en color son las que se agregan en ese paso; lo ya armado aparece en gris.",
                    S["pz"]), Spacer(1, 2)]
    H += paso("Paso 1. Motores y cunas",
              "piso 1, 2 cunas de motor con insertos, 2 motores N20 con capacitor y cables, 4 Allen M3×12",
              ["Voltea el piso 1. Mete cada N20 en su cuna con el eje hacia afuera y las terminales hacia el centro.",
               "Presenta la cuna bajo el piso 1 y atornilla 2 M3×12 desde arriba, uno atrás y otro adelante de la batería.",
               "Pasa los dos cables de cada motor por la ranura de 10 × 10 de su lado, junto a donde irá el L298N.",
               "Aprieta hasta que el motor no gire dentro de la cuna."],
              "ninguna cabeza queda en el hueco de la batería y los cables no tocan el suelo.",
              "paso1.png")
    H += paso("Paso 2. Ruedas, capucha de color y patín",
              "2 ruedas, capucha de color y patín trasero con insertos, TCS34725 con sus 4 cables, 4 Allen M3×8",
              ["Presiona cada rueda en su eje; debe quedar a 1–2 mm del hueco del piso.",
               "Atornilla la capucha con 2 M3×8 desde arriba y el patín con otros 2 (a los lados del L298N).",
               "Desliza el TCS34725 en la capucha por la abertura de atrás, LED hacia el suelo, hasta que tope.",
               "Sube sus 4 cables por dentro de la capucha y sácalos por la ranura de 14 × 6 del piso 1."],
              "en el suelo, el robot se apoya en las ruedas y los patines quedan a 0.5 mm.",
              "paso2.png")
    H += sub("3.1 Reconoce el L298N",
             ["<b>OUT1-OUT2</b> (izquierda) y <b>OUT3-OUT4</b> (derecha): motores.",
              "Borne de potencia al frente: <b>12V</b>, <b>GND</b> y 5V (el 5V no se usa).",
              "Header de lógica: <b>ENA IN1 IN2 IN3 IN4 ENB</b>. Quita los jumpers de ENA y ENB; deja el de 5V-EN.",
              "El disipador va hacia atrás del robot; el header y los bornes de potencia, hacia la batería."],
             None, "det_l298.png", intro="Antes de montarlo, ubica sus conexiones (vista desde arriba, frente del robot arriba).",
             num=False)
    H += paso("Paso 3. Puente H L298N y cables de motores",
              "L298N, 4 Allen M3×8",
              ["Pon el L298N sobre los 4 postes de atrás del piso 1, disipador hacia atrás.",
               "Atornilla 4 M3×8 desde arriba a los insertos de los postes.",
               "Motor izquierdo: amarillo a OUT1 y blanco a OUT2. Motor derecho: amarillo a OUT3 y blanco a OUT4.",
               "Aprieta los bornes con el desarmador plano y jala cada cable suave: no debe salir."],
              "ningún cable de motor queda colgando bajo el piso 1 ni cerca de las ruedas.",
              "paso3.png")
    H += paso("Paso 4. Batería",
              "batería 2S con su conector T macho, velcro",
              ["Pega el velcro en el piso 1, entre los topes.",
               "Acuesta la batería a lo ancho, sobre el eje, con sus cables hacia la izquierda.",
               "Deja el conector T macho acostado sobre la batería, apuntando a la derecha. <b>No lo conectes todavía.</b>",
               "El cable de balanceo (blanco) queda encima, a la izquierda; solo se usa para cargar."],
              "entre la batería y el borde del L298N quedan ~4.5 mm libres para doblar los cables de potencia.",
              "paso4.png")
    H += paso("Paso 5. Sensores de distancia VL53L0X",
              "3 VL53L0X con header, 15 dupont hembra-macho",
              ["Conecta 5 dupont a cada sensor <b>antes</b> de meterlo: VIN rojo, GND negro, SCL cian, SDA azul y "
               "XSHUT verde. GPIO1 queda libre.",
               "Baja cada sensor por las ranuras de su soporte: chip hacia afuera, pines arriba apuntando hacia adentro.",
               "Dobla los cables hacia arriba justo al final del dupont.",
               "El cable del frente va por debajo del OLED hacia la ranura derecha; los laterales suben derecho."],
              "cada sensor tocó el fondo de su soporte y detrás de él quedan ~27 mm libres.",
              "paso5.png")
    H += paso("Paso 6. Cables de lógica del L298N",
              "6 dupont hembra-macho",
              ["Conecta un dupont a cada pin del header del L298N: ENA y ENB morados, IN1 a IN4 cafés.",
               "Sube los 6 cables juntos, por encima de la batería, hacia el centro del robot."],
              "los dupont están en la fila de adelante del header, no en la de 5V.",
              "paso6.png")
    H += paso("Paso 7. Piso 2 en la mesa",
              "piso 2, 2 mini protoboards, Arduino Nano, 8 jumpers rígidos, OLED con 4 dupont, botón, interruptor con su arnés",
              ["Pega las protoboards en su marco: izquierda para el Nano, derecha para el bus.",
               "Clava el Nano con el USB hacia atrás, en las columnas 2 a 16 (contando desde adelante).",
               "Bus: columna 1 GND, 4 5V, 7 SCL y 10 SDA. Une las dos mitades de cada una con un jumper.",
               "Jumpers del Nano al bus: GND, 5V, A5 (SCL) y A4 (SDA); no se cruzan.",
               "Pasa el header del OLED por su ranura (pines hacia atrás) y conecta sus 4 dupont por abajo.",
               "Mete el botón y el interruptor en sus agujeros y apriétalos con su tuerca."],
              "con el multímetro, cada columna del bus tiene continuidad de punta a punta y no con las demás.",
              "paso7.png", a_img=165)
    H += sub("7.1 Pines del OLED",
             ["El plástico del header queda dentro de la ranura del piso 2.",
              "Los 4 pines salen hacia abajo; ahí se conectan los dupont: GND negro, VCC rojo, SCL cian y SDA azul.",
              "Los cables van a la ranura derecha y suben al bus."],
             None, "detalle_oled.png", alto_img=70)
    H += sub("8.1 Arnés de potencia",
             ["Acerca el piso 2 por atrás, inclinado, con el arnés colgando.",
              "Naranja corto del interruptor al <b>12V</b> del L298N.",
              "Negro del conector T y negro largo (al Nano) juntos, torcidos, al <b>GND</b> del L298N.",
              "Dobla los cables hacia arriba entre la batería y el L298N.",
              "El otro naranja y el negro largo suben por la ranura central del piso 2."],
             "jala cada cable del borne: ninguno sale. El conector T hembra sigue <b>sin conectar</b>.",
             "det_arnes.png", intro="Los bornes quedan bajo el piso 2: se aprietan antes de cerrarlo.")
    H += paso("Paso 8. Montar el piso 2",
              "conjunto del paso 7, 4 Allen M3×8",
              ["Baja el piso 2 sobre las 4 columnas pasando los cables: sensores izquierdos y TCS34725 por la ranura "
               "izquierda; VL53L0X derecho, frontal y OLED por la derecha; L298N, botón y potencia por la central.",
               "Revisa que ningún cable quede pellizcado entre columna y piso.",
               "Atornilla 4 M3×8 a los insertos de las columnas."],
              "el piso 2 asienta plano en las 4 columnas y los cables de abajo no tocan las ruedas.",
              "paso8.png")
    H += paso("Paso 9. Conexiones en las protoboards",
              "los cables que salen por las ranuras",
              ["Cada sensor va a su hoyo del bus por color: rojo a 5V, negro a GND, azul a SDA y cian a SCL.",
               "XSHUT verdes: izquierdo a A0, frente a A1 y derecho a A2 (fila de pines A, junto al canal).",
               "L298N: ENA→D5, ENB→D6, IN1→D7, IN2→D8, IN3→D9, IN4→D10 (fila D, lado de afuera).",
               "Botón: rosa a D2 y negro a GND de la fila D.",
               "Naranja rígido a VIN y negro rígido a GND de la fila A del Nano.",
               "Agrupa con cinchos los cables de cada sensor; usa el Anexo A como lista de revisión."],
              "compara cable por cable con la Fig. 4 y el Anexo A antes de seguir.",
              "paso9.png")
    H += paso("Paso 10. Primera conexión de la batería",
              "conector T",
              ["Haz todas las revisiones de la sección 6.1.",
               "Pon el interruptor en OFF y levanta el robot para que las ruedas giren en el aire.",
               "Une el conector T macho de la batería con la hembra del robot y acuéstalo sobre la batería.",
               "Enciende: la OLED debe decir LABERINTO LISTO."],
              "nada se calienta en el primer minuto. Si algo huele o se calienta, apaga y desconecta el T.",
              "paso10.png")
    H.append(PageBreak())

    # 6. Ajustes y pruebas
    H += [h1("6. Ajustes y pruebas"), h2("6.1 Antes de conectar la batería"),
          tabla([["", "Revisión"],
                 ["☐", "Continuidad (batería desconectada): no hay pitido entre 12V y GND del L298N ni entre 5V y GND del Nano."],
                 ["☐", "El interruptor en ON une el rojo del T con los dos naranjas; en OFF, no."],
                 ["☐", "Los jumpers ENA y ENB del L298N están quitados; el de 5V-EN está puesto."],
                 ["☐", "Nada usa la salida de 5V del L298N."],
                 ["☐", "Las ruedas giran libres y ningún cable las toca."],
                 ["☐", "El robot mide 120 × 120 mm o menos con las ruedas."]], [10, 166]),
          h2("6.2 Primer encendido"),
          *lista([
              "Sube el código (manual de uso, sección 2) con el interruptor en OFF.",
              "Enciende sosteniendo el botón: modo calibración. La OLED muestra el color y las tres distancias.",
              "Acerca la mano a cada VL53L0X: su distancia debe bajar. Si sale <b>SIN VL53L0X</b>, revisa su XSHUT.",
              "Botón corto: las dos ruedas avanzan. Si una gira al revés, intercambia sus dos cables en el L298N.",
              "Botón largo: gira a la derecha. Si gira a la izquierda, intercambia OUT1-2 con OUT3-4.",
          ], num=True),
          h2("6.3 Aprietes sugeridos"),
          tabla([["Unión", "Apriete"],
                 ["Allen M3 en inserto (todos)", "Firme con el lado corto de la llave; si el inserto gira, cambió de agujero: reponlo"],
                 ["Bornes del L298N", "Firme; jalar cada cable para comprobar"],
                 ["Tuercas del botón y del interruptor", "Con los dedos y un cuarto de vuelta con pinzas"]], [80, 96]),
          h1("7. Solución de problemas"),
          tabla([["Síntoma", "Causa probable", "Qué hacer"],
                 ["La OLED no prende", "Interruptor, VIN o bus I2C", "Mide 7–8 V en VIN; revisa los puentes del bus"],
                 ["SIN SENSOR COLOR", "Cable del TCS34725 suelto", "Revisa sus 4 soldaduras y su hoyo en el bus"],
                 ["SIN VL53L0X", "XSHUT o VIN de un sensor", "Revisa A0/A1/A2 y que el dupont siga en el pin"],
                 ["El Nano se reinicia al arrancar", "Ruido de motores o batería baja", "Capacitores de 100 nF; carga la batería"],
                 ["Un motor no gira", "Borne flojo o ENA/ENB", "Aprieta OUT y revisa D5/D6"],
                 ["Una rueda roza", "Cable de motor o rueda muy adentro", "Acomoda el cable; saca la rueda 1 mm"],
                 ["El sensor de color baila", "Ranura grande", "Calza con cinta; reimprime con RANURA menor"]],
                [48, 56, 72]),
          h1("8. Uso seguro"),
          *lista([
              "La batería es de litio: cárgala con cargador balanceador, sin dejarla sola y nunca por debajo de 6.4 V.",
              "Desconecta el conector T para guardar el robot, programarlo con cambios de cableado o soldar.",
              "No cortocircuites el conector T: un corto en una 2S calienta los cables en segundos.",
              "Revisa cada semana que los bornes estén apretados y que ningún forro de cable esté pelado.",
          ]),
          PageBreak()]

    # Anexo A
    H += [h1("Anexo A. Lista de cables"),
          p("Sale del modelo 3D (chasis.scad): cada cable tiene una ruta y este es su largo, sin contar los conectores. Los dupont de "
            "30 cm alcanzan para todos con holgura (el más largo mide 22 cm). Para los cables de calibre 22, corta el largo de la tabla más 30 mm."),
          tabla([["De", "A", "Color", "Tipo", "Largo (mm)"], *[[c[0], c[1], c[2], c[3], c[4]] for c in cables]],
                [44, 32, 18, 62, 20])]
    construir("manual_ensamble.pdf", "Manual de armado", H)


# ---------- Manual de uso ----------
def manual_uso():
    H = []
    H += [Spacer(1, 30 * mm), Paragraph("Manual de uso", S["t"]),
          Paragraph("Robot de laberinto · Arduino Nano (ATmega328P)", S["st"]), Spacer(1, 10 * mm),
          img("iso.png", 130, 110), Spacer(1, 8 * mm),
          tabla([["Sección", "Contenido"],
                 ["1. Cómo funciona", "Qué hace el robot y cómo cuenta las marcas"],
                 ["2. Programarlo", "Microchip Studio y carga con avrdude"],
                 ["3. Controles", "Interruptor, botón y pantalla"],
                 ["4. Calibración", "Colores, distancias y tiempos, con hoja para llenar"],
                 ["5. En la competencia", "Paso a paso de cada corrida"],
                 ["6. Batería", "Carga y cuidados"],
                 ["7. Problemas", "Qué hacer si algo falla"]], [45, 125]),
          PageBreak()]

    H += [h1("1. Cómo funciona"),
          *lista([
              "<b>Sensores de distancia:</b> los 3 VL53L0X ven paredes a la izquierda, al frente y a la derecha. "
              "Mantienen el robot centrado en el pasillo y lo frenan al llegar a una pared.",
              "<b>Mapa:</b> el robot guarda en la EEPROM las paredes de cada celda que visita (laberinto de 16 × 16). "
              "El mapa no se borra al apagarlo.",
              "<b>Algoritmo:</b> flood-fill. Calcula la distancia de cada celda a la meta y siempre avanza a la celda "
              "más cercana. Si encuentra una pared nueva, recalcula.",
              "<b>Movimiento:</b> los motores no tienen encoder. El avance y los giros se miden por tiempo con el "
              "Timer1 (interrupción de 1 ms, tick de 10 ms). Por eso hay que calibrar con la batería cargada.",
              "<b>Marcas de color:</b> el TCS34725 lee el piso cada 30 ms. Una marca cuenta si el color se sostiene en "
              "3 lecturas seguidas después de haber visto piso. Además se guarda la celda, así que pasar otra vez "
              "por la misma marca no la vuelve a contar, ni en otra corrida.",
          ]),
          h2("Tipos de corrida"),
          tabla([["Situación", "Qué hace", "Pantalla"],
                 ["No conoce un camino a la meta", "Explora hasta la meta y luego regresa solo al inicio explorando más",
                  "EXPLORA → REGRESO → LISTO"],
                 ["Ya conoce un camino", "Va directo por la ruta más corta, con rectas largas a velocidad alta",
                  "RAPIDO → META"]], [50, 80, 40]),
          PageBreak()]

    H += [h1("2. Programarlo"),
          p("El código está en C++ sin librerías de Arduino, en <b>atmega328p/laberinto/</b>. Maneja el ATmega328P "
            "por registros: TWI (I2C) en twi.cpp, Timer0 (PWM de motores) en motores.cpp y Timer1 (base de tiempo "
            "por interrupción) en tiempo.cpp. Se compila en Microchip Studio y se carga por USB con avrdude, "
            "usando el bootloader que ya trae el Nano."),
          h2("Una sola vez"),
          *lista([
              "Instala <b>Microchip Studio 7</b> y <b>Arduino IDE 2</b> (solo para tener avrdude). En Arduino IDE "
              "instala una vez la placa Arduino AVR Boards.",
              "Instala el driver <b>CH340</b> si Windows no reconoce el Nano. En el Administrador de dispositivos anota "
              "el puerto (por ejemplo COM5).",
              "Microchip Studio: File → New → Project → <b>GCC C++ Executable Project</b>, nombre <b>laberinto</b>, "
              "dispositivo <b>ATmega328P</b>.",
              "Borra el main.cpp que crea. Clic derecho en el proyecto → Add → Existing Item… y agrega todos los "
              ".cpp y .h de atmega328p/laberinto/.",
              "Arriba elige la configuración <b>Release</b> (optimiza a -Os).",
              "Tools → External Tools… → Add. Title: <b>Cargar Nano</b>. Command: la ruta de avrdude.exe, por ejemplo "
              "<font face='Courier' size='8'>%LOCALAPPDATA%\\Arduino15\\packages\\arduino\\tools\\avrdude\\"
              "6.3.0-arduino17\\bin\\avrdude.exe</font>. Arguments:",
          ], num=True),
          Paragraph("<font face='Courier' size='7.5'>-C \"...\\etc\\avrdude.conf\" -p atmega328p -c arduino -P COM5 "
                    "-b 115200 -U flash:w:\"$(TargetDir)$(TargetName).hex\":i</font>", S["p"]),
          p("Marca <b>Use Output window</b>. El avrdude.conf está en la carpeta etc junto a bin."),
          h2("Cada vez que cambies algo"),
          *lista([
              "Edita el valor en <b>config.h</b> (pines, laberinto y calibración están ahí).",
              "Build → Build Solution (F7). Debe terminar sin errores; usa unos 14 KB de flash y 1 KB de RAM.",
              "Conecta el Nano por USB-C con el interruptor del robot <b>apagado</b> y usa Tools → Cargar Nano.",
          ], num=True),
          caja("Si avrdude dice <b>not in sync</b>, tu Nano tiene el bootloader viejo: cambia -b 115200 por "
               "<b>-b 57600</b>. Desde Linux o Mac también sirve el Makefile: <font face='Courier'>make cargar "
               "PUERTO=/dev/ttyUSB0</font>."),
          caja("Al subir código nuevo no se borra el mapa: está en la EEPROM. Para borrarlo usa el botón sostenido "
               "(sección 3)."),
          h2("Dónde poner el laberinto en el código (config.h)"),
          tabla([["Constante", "Valor", "Qué es"],
                 ["N", "16", "Celdas por lado (3 m / 18 cm ≈ 16)"],
                 ["INI_X, INI_Y", "0, 0", "Celda de inicio"],
                 ["INI_R", "0", "Hacia dónde mira al inicio (0 = norte)"],
                 ["META_X, META_Y", "7, 7", "Esquina inferior izquierda de la meta de 2 × 2 (centro)"]], [40, 25, 105]),
          p("El robot cuenta desde la esquina de inicio: x crece a su derecha y y hacia adelante. Si la salida está "
            "en una esquina con la pared exterior a la <b>derecha</b> del robot, usa INI_X = 15. Si la meta no está en "
            "el centro, cambia META_X y META_Y el día de la competencia."),
          PageBreak()]

    H += [h1("3. Controles"),
          tabla([["Acción", "Resultado"],
                 ["Interruptor", "Enciende y apaga todo"],
                 ["Botón corto (menos de 2 s)", "Empieza una corrida medio segundo después de soltarlo"],
                 ["Botón sostenido más de 2 s", "Borra mapa y conteo. Pantalla: BORRADO"],
                 ["Encender con el botón presionado", "Modo calibración (para salir, apaga y prende)"],
                 ["En calibración: botón corto", "Avanza una celda"],
                 ["En calibración: botón de más de 1 s", "Gira 90° a la derecha"]], [65, 105]),
          h2("Pantalla"),
          tabla([["Mensaje", "Significado"],
                 ["LABERINTO LISTO", "Esperando el botón"],
                 ["EXPLORA", "Primera corrida, buscando la meta"],
                 ["REGRESO", "Volviendo solo al inicio. No lo levantes"],
                 ["RAPIDO", "Corrida rápida por la ruta conocida"],
                 ["META", "Llegó a la meta en corrida rápida"],
                 ["BORRADO", "Mapa y conteo en cero"],
                 ["ROJO / VERDE / AZUL / AMAR + número", "Marcas contadas de cada color; T = total"],
                 ["SIN SENSOR COLOR", "No encuentra el TCS34725: revisa VIN, GND, SDA, SCL"],
                 ["SIN VL53L0X", "Falla algún sensor de distancia: revisa su XSHUT y alimentación"]], [65, 105]),
          PageBreak()]

    H += [h1("4. Calibración"),
          p("Hazla en el orden de la tabla, con la batería cargada (más de 8.0 V) y sobre un piso igual al de la "
            "competencia. Todos los valores están en config.h."),
          h2("4.1 Colores"),
          *lista([
              "Enciende con el botón presionado. La OLED muestra r, g, b (proporciones), c (brillo) y el color que reconoce.",
              "Pon el robot sobre el piso y anota r, g, b y c en la fila PISO de la hoja.",
              "Repite sobre cada marca de color.",
              "Copia los valores al arreglo <b>refs[]</b> y sube el código.",
              "Comprueba que la OLED muestre el nombre correcto sobre cada color. Si confunde dos colores, baja "
              "DIST_MAX; si no reconoce ninguno, súbelo.",
          ], num=True),
          h2("4.2 Distancias"),
          *lista([
              "Siempre en modo calibración, centra el robot a mano en una celda con paredes a los lados y enfrente.",
              "La última línea de la OLED muestra: izquierda, frente, derecha (mm).",
              "D_LADO = promedio de izquierda y derecha. D_FRENTE = el valor del frente.",
          ], num=True),
          h2("4.3 Avance y giro"),
          *lista([
              "Pon el robot en un pasillo largo, sin pared enfrente.",
              "Botón corto: avanza una celda. Debe recorrer 180 mm. Si se queda corto, sube T_CELDA (cada unidad "
              "son 10 ms); si se pasa, bájalo.",
              "Botón de más de 1 s: gira 90°. Ajusta T_90 igual.",
              "Si se va de lado al avanzar sin paredes, ajusta AJUSTE_DER (positivo si se va a la derecha).",
              "T_RAPIDA: igual que T_CELDA, pero en una corrida rápida de varias celdas.",
          ], num=True),
          h2("Hoja de calibración"),
          tabla([["Valor", "Fábrica", "Medido 1", "Medido 2", "Final"],
                 ["PISO r / g / b / c", "0.33/0.33/0.33/900", "", "", ""],
                 ["ROJO r / g / b / c", "0.58/0.22/0.20/400", "", "", ""],
                 ["VERDE r / g / b / c", "0.26/0.46/0.28/350", "", "", ""],
                 ["AZUL r / g / b / c", "0.20/0.32/0.48/300", "", "", ""],
                 ["AMAR r / g / b / c", "0.42/0.40/0.18/700", "", "", ""],
                 ["D_LADO (mm)", "38", "", "", ""],
                 ["D_FRENTE (mm)", "34", "", "", ""],
                 ["T_CELDA (× 10 ms)", "60", "", "", ""],
                 ["T_90 (× 10 ms)", "25", "", "", ""],
                 ["T_RAPIDA (× 10 ms)", "40", "", "", ""],
                 ["AJUSTE_DER", "0", "", "", ""],
                 ["VEL_EXPLORA / VEL_RAPIDA", "140 / 220", "", "", ""]], [45, 38, 29, 29, 29]),
          PageBreak()]

    H += [h1("5. En la competencia"),
          h2("Antes de empezar"),
          *lista([
              "Batería cargada (más de 8.0 V).",
              "Ajusta INI_X, INI_R, META_X y META_Y si el laberinto lo pide, y sube el código.",
              "Enciende y <b>sostén el botón 2 s</b> para borrar el mapa del laberinto anterior.",
          ], num=True),
          h2("Corrida 1: exploración"),
          *lista([
              "Pon el robot en la celda de inicio, centrado, mirando hacia adelante.",
              "Botón corto y quita la mano.",
              "El robot llega a la meta y regresa solo al inicio. <b>No lo levantes</b> hasta que la pantalla diga LISTO.",
              "Revisa el conteo de marcas en la pantalla.",
          ], num=True),
          h2("Corridas 2 y 3: rápidas"),
          *lista([
              "Pon el robot en el inicio, igual que antes.",
              "Botón corto. Va directo a la meta (RAPIDO → META).",
              "Levántalo y regrésalo al inicio para la siguiente.",
          ], num=True),
          caja("Si en la corrida 1 se atora o lo tienes que levantar, sostén el botón 2 s para borrar y empieza la "
               "exploración otra vez. Un mapa con paredes falsas hace que la corrida rápida falle."),
          h2("Laberinto nuevo (ronda final)"),
          p("Sostén el botón 2 s para borrar y empieza otra vez con la corrida 1."),
          PageBreak()]

    H += [h1("6. Batería"),
          tabla([["Voltaje (total)", "Estado"],
                 ["8.4 V", "Llena"],
                 ["7.6 V", "Media; así se guarda si no se usa en días"],
                 ["7.0 V", "Recargar"],
                 ["6.4 V", "Mínimo absoluto; por debajo se daña"]], [50, 120]),
          *lista([
              "Se carga por el conector blanco de 3 pines (balanceo) con el cargador 2S.",
              "Carga sobre una superficie que no se queme y sin dejarla sola.",
              "Mide con el multímetro entre corridas. Con menos de 7.6 V los tiempos de avance cambian.",
              "Si se infla o se calienta mucho, no la uses.",
          ]),
          h1("7. Problemas"),
          tabla([["Síntoma", "Causa probable", "Solución"],
                 ["Pantalla apagada", "Batería, interruptor o I2C", "Mide voltaje en VIN; revisa SDA/SCL de la OLED"],
                 ["avrdude: not in sync", "Bootloader viejo o puerto mal", "Usa -b 57600; revisa el COM y el driver CH340"],
                 ["SIN SENSOR COLOR", "TCS34725 sin conexión", "Revisa sus cables y que esté metido hasta el fondo de la capucha"],
                 ["SIN VL53L0X", "Un VL53L0X sin alimentación o XSHUT", "Revisa VCC y XSHUT de cada uno (A0, A1, A2) y que su dupont no se haya salido"],
                 ["Una rueda gira al revés", "Cables del motor invertidos", "Intercambia sus 2 cables en el L298N"],
                 ["Gira al lado contrario", "Motores cruzados", "Intercambia OUT1-2 con OUT3-4"],
                 ["Choca con paredes", "Mal calibrado o batería baja", "Carga la batería; revisa T_CELDA, T_90, AJUSTE_DER"],
                 ["Se queda corto o se pasa de celda", "T_CELDA", "Calibración 4.3"],
                 ["Cuenta una marca dos veces", "Mal ubicada la celda", "Revisa OFF_COLOR (0.2 de fábrica)"],
                 ["No cuenta una marca", "Referencia de color mala", "Calibración 4.1; sube DIST_MAX"],
                 ["Se reinicia al arrancar los motores", "Ruido o batería baja", "Capacitores de 100 nF en los motores; carga la batería"],
                 ["Corrida rápida falla", "Mapa con paredes falsas", "Borra (botón 2 s) y explora otra vez"],
                 ["Se detiene en la corrida 1 sin llegar", "Meta o inicio mal configurados", "Revisa N, INI_X, INI_R, META_X, META_Y"]],
                [45, 50, 75])]
    construir("manual_uso.pdf", "Manual de uso", H)


if __name__ == "__main__":
    escribir_csv()
    manual_ensamble()
    manual_uso()
    for f in os.listdir(AQUI):
        if f.startswith(".tmp_"):
            os.remove(os.path.join(AQUI, f))
