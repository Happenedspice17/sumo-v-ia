"""Genera manual_ensamble.pdf, manual_uso.pdf y bom.csv.

Uso: python3 docs/generar_manuales.py
Usa las imagenes de chasis/img/ y atmega328p/img/.
"""
import csv
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
IMG = os.path.join(RAIZ, "chasis", "img")

# ---------- Estilos ----------
FUENTE, NEGRITA = "Helvetica", "Helvetica-Bold"
for f, n in (("DejaVuSans.ttf", "DV"), ("DejaVuSans-Bold.ttf", "DVB")):
    ruta = os.path.join("/usr/share/fonts/truetype/dejavu", f)
    if os.path.exists(ruta):
        pdfmetrics.registerFont(TTFont(n, ruta))
if "DV" in pdfmetrics.getRegisteredFontNames():
    FUENTE, NEGRITA = "DV", "DVB"

AZUL = colors.HexColor("#33415c")
GRIS = colors.HexColor("#f2f4f7")
AVISO = colors.HexColor("#fff4e5")

base = getSampleStyleSheet()
S = {
    "t": ParagraphStyle("t", parent=base["Title"], fontName=NEGRITA, fontSize=24, leading=28, textColor=AZUL),
    "st": ParagraphStyle("st", parent=base["Normal"], fontName=FUENTE, fontSize=12, leading=16,
                         textColor=colors.HexColor("#555"), alignment=TA_CENTER),
    "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=NEGRITA, fontSize=16, leading=20,
                         textColor=AZUL, spaceBefore=6, spaceAfter=6),
    "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=NEGRITA, fontSize=12.5, leading=16,
                         textColor=AZUL, spaceBefore=8, spaceAfter=4),
    "p": ParagraphStyle("p", parent=base["Normal"], fontName=FUENTE, fontSize=9.8, leading=13.5, spaceAfter=4),
    "li": ParagraphStyle("li", parent=base["Normal"], fontName=FUENTE, fontSize=9.8, leading=13.5,
                         leftIndent=12, bulletIndent=2, spaceAfter=2),
    "c": ParagraphStyle("c", parent=base["Normal"], fontName=FUENTE, fontSize=8.6, leading=11),
    "cb": ParagraphStyle("cb", parent=base["Normal"], fontName=NEGRITA, fontSize=8.6, leading=11,
                         textColor=colors.white),
    "pie": ParagraphStyle("pie", parent=base["Normal"], fontName=FUENTE, fontSize=8.5, leading=11,
                          textColor=colors.HexColor("#666"), alignment=TA_CENTER),
}


def p(t):
    return Paragraph(t, S["p"])


def h1(t):
    return Paragraph(t, S["h1"])


def h2(t):
    return Paragraph(t, S["h2"])


def lista(items, num=False):
    return [Paragraph(t, S["li"], bulletText=f"{i}." if num else "•") for i, t in enumerate(items, 1)]


def tabla(filas, anchos, cabecera=True):
    datos = [[Paragraph(str(c), S["cb"] if (cabecera and i == 0) else S["c"]) for c in f] for i, f in enumerate(filas)]
    t = Table(datos, colWidths=[a * mm for a in anchos], repeatRows=1 if cabecera else 0)
    estilo = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbb")),
              ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if cabecera:
        estilo.append(("BACKGROUND", (0, 0), (-1, 0), AZUL))
        estilo += [("BACKGROUND", (0, i), (-1, i), GRIS) for i in range(2, len(filas), 2)]
    t.setStyle(TableStyle(estilo))
    return t


def caja(texto, color=AVISO):
    t = Table([[Paragraph(texto, S["p"])]], colWidths=[170 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0a050")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def img(ruta, ancho_mm, recorte=None):
    if not os.path.exists(ruta):
        return p(f"[falta imagen {os.path.basename(ruta)}]")
    if recorte:
        from PIL import Image as PImage
        im = PImage.open(ruta).crop(recorte)
        tmp = os.path.join(AQUI, ".tmp_" + os.path.basename(ruta))
        im.save(tmp)
        ruta = tmp
    i = Image(ruta)
    escala = ancho_mm * mm / i.imageWidth
    i.drawWidth, i.drawHeight = i.imageWidth * escala, i.imageHeight * escala
    return i


def pie_pagina(titulo):
    def dibujar(c, doc):
        c.saveState()
        c.setFont(FUENTE, 8)
        c.setFillColor(colors.HexColor("#888"))
        c.drawString(20 * mm, 10 * mm, f"Robot laberinto · {titulo}")
        c.drawRightString(190 * mm, 10 * mm, f"{doc.page}")
        c.restoreState()
    return dibujar


def construir(nombre, titulo, historia):
    doc = SimpleDocTemplate(os.path.join(AQUI, nombre), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm, title=titulo, author="Equipo robot laberinto")
    doc.build(historia, onFirstPage=pie_pagina(titulo), onLaterPages=pie_pagina(titulo))
    print("Generado", nombre)


# ---------- Datos ----------
BOM_ELEC = [
    ["Arduino Nano USB-C (ATmega328P, CH340) + cable USB-C de datos", "1", "Cerebro del robot"],
    ["Motorreductor N20, 6 V, 300–500 RPM, sin encoder", "2", "Mismo modelo los dos"],
    ["Rueda para N20, Ø34 × 20 mm, eje D de 3 mm", "2", "Si es otra medida, cambiar D_RUEDA en chasis.scad"],
    ["Puente H L298N (Steren)", "1", "Quitar jumpers ENA/ENB"],
    ["Sensor de color TCS34725 (módulo morado)", "1", "Se usa el pin VIN"],
    ["Sensor de distancia VL53L0X (CJVL53L0XV2)", "3", "Izquierdo, frente y derecho"],
    ["Pantalla OLED SSD1306 0.96\" I2C (0x3C)", "1", "4 pines: GND VCC SCL SDA"],
    ["Botón de panel Ø7 mm, normalmente abierto", "1", "Botón de arranque"],
    ["Interruptor de palanca MTS-102 (Ø6 mm)", "1", "Encendido/apagado"],
    ["Batería 2S 18650, 7.4 V, 3000 mAh, conector T", "1", "Con balanceo JST-XH de 3 pines"],
    ["Conector T (Deans) hembra con cables", "1", "Para conectar la batería al robot"],
    ["Cargador balanceador 2S (JST-XH 3 pines)", "1", "USB 2S o tipo B3 / IMAX B6"],
    ["Mini protoboard 170 puntos", "2", "Una para el Nano, otra para el bus I2C"],
    ["Capacitor cerámico 100 nF", "2", "Uno soldado en cada motor"],
    ["Cables dupont macho-macho y macho-hembra (20 cm)", "20 + 20", ""],
    ["Cable calibre 22, rojo y negro", "1 m c/u", "Batería, interruptor, motores"],
]
BOM_TORN = [
    ["Separador M3 hembra-hembra 35 mm", "4", "Piso 1 → piso 2"],
    ["Tornillo M3 × 8 cabeza cilíndrica", "8", "Separadores: 4 abajo, 4 arriba"],
    ["Tornillo M3 × 16 cabeza cilíndrica", "4", "L298N"],
    ["Tornillo M3 × 20 cabeza cilíndrica", "4", "Cunas de motor"],
    ["Tornillo M3 × 10 avellanado (cabeza plana)", "3", "Capucha de color (2) y patín (1)"],
    ["Tuerca M3", "10", "8 se usan; sobran 2"],
    ["Velcro adhesivo 3 × 5 cm", "1", "Bajo la batería"],
    ["Cinchos de plástico chicos", "10", "Ordenar cables"],
]
BOM_IMP = [
    ["piso1", "1", "Plano", "Base, soportes de VL53L0X y topes de batería integrados"],
    ["piso2", "1", "Plano", "Marcos de protoboards y OLED integrados"],
    ["cuna_motor", "2", "Plano (base abajo)", "Sujeta cada N20"],
    ["capucha_color", "1", "Orejas abajo", "TCS34725 deslizable y patín delantero. Mejor en negro"],
    ["patin", "1", "Domo arriba", "Apoyo trasero"],
    ["espaciador", "4", "De pie", "L298N"],
    ["prueba", "1", "Plano", "Imprimir primero"],
]
HERRAMIENTAS = ["Cautín y soldadura", "Desarmador de cruz chico", "Llave o pinzas para tuerca M3 (5.5 mm)",
                "Multímetro", "Pinzas de corte y pelacables",
                "Computadora con Microchip Studio 7 y avrdude (viene con Arduino IDE)"]
PINES = [
    ["L298N", "ENA / ENB", "D5 / D6"],
    ["L298N", "IN1 / IN2 / IN3 / IN4", "D7 / D8 / D9 / D10"],
    ["L298N", "12V", "Batería + (después del interruptor)"],
    ["L298N", "GND", "GND común"],
    ["L298N", "OUT1-OUT2 / OUT3-OUT4", "Motor izquierdo / motor derecho"],
    ["VL53L0X izq / frente / der", "XSHUT", "A0 / A1 / A2"],
    ["VL53L0X ×3, TCS34725, OLED", "SDA / SCL", "Bus col. 7 / col. 10 → A4 / A5"],
    ["VL53L0X ×3 (VCC), TCS34725 (VIN), OLED (VCC)", "Alimentación", "Bus col. 1 → 5V del Nano"],
    ["Todos los módulos", "GND", "Bus col. 4 → GND"],
    ["VL53L0X", "GPIO1", "Sin conectar"],
    ["TCS34725", "LED, INT, 3V3", "Sin conectar"],
    ["Botón", "Una pata / la otra", "D2 / GND"],
    ["Arduino Nano", "VIN", "Batería + (después del interruptor)"],
]


def escribir_csv():
    with open(os.path.join(AQUI, "bom.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Categoria", "Componente", "Cantidad", "Notas"])
        for cat, filas in (("Electronica", BOM_ELEC), ("Tornilleria", BOM_TORN)):
            for r in filas:
                w.writerow([cat, *r])
        for r in BOM_IMP:
            w.writerow(["Impresa 3D", r[0], r[1], r[3]])
    print("Generado bom.csv")


# ---------- Manual de ensamble ----------
def manual_ensamble():
    H = []
    H += [Spacer(1, 30 * mm), Paragraph("Manual de ensamble", S["t"]),
          Paragraph("Robot de laberinto · Arduino Nano (ATmega328P)", S["st"]), Spacer(1, 8 * mm),
          img(os.path.join(IMG, "iso.png"), 150, (200, 120, 1250, 1000)), Spacer(1, 8 * mm),
          tabla([["Sección", "Contenido"],
                 ["1. Lista de material", "Electrónica, tornillería, piezas impresas y herramientas"],
                 ["2. Impresión 3D", "Ajustes, orientación y tolerancias"],
                 ["3. Preparación", "Medir, soldar y probar en la mesa"],
                 ["4. Ensamble", "Cuatro pasos, de abajo hacia arriba"],
                 ["5. Cableado", "Diagrama, tabla de pines y protoboard"],
                 ["6. Verificación", "Antes de conectar la batería por primera vez"]], [45, 125]),
          PageBreak()]

    H += [h1("1. Lista de material"), h2("Electrónica"),
          tabla([["Componente", "Cant.", "Notas"], *BOM_ELEC], [92, 18, 60]),
          h2("Tornillería y sujeción"), tabla([["Pieza", "Cant.", "Dónde va"], *BOM_TORN], [92, 18, 60]),
          h2("Piezas impresas (chasis/stl/)"), tabla([["Archivo", "Cant.", "Orientación", "Para qué"], *BOM_IMP],
                                                       [35, 15, 40, 80]),
          h2("Herramientas"), *lista(HERRAMIENTAS),
          p("La misma lista está en <b>docs/bom.csv</b> para abrirla en Excel."), PageBreak()]

    H += [h1("2. Impresión 3D (Bambu Lab X2D)"),
          caja("No tengo las especificaciones exactas de la X2D. Estos ajustes son los de cualquier Bambu Lab con "
               "boquilla de 0.4 mm en Bambu Studio. Por eso lo primero es imprimir la <b>pieza de prueba</b> "
               "y revisar que todo entre."),
          h2("Ajustes en Bambu Studio"),
          tabla([["Ajuste", "Valor", "Por qué"],
                 ["Material", "PLA o PETG", "PETG aguanta mejor golpes y calor; PLA es más fácil"],
                 ["Boquilla / capa", "0.4 mm / 0.2 mm", "Perfil estándar"],
                 ["Paredes", "4", "Los pisos de 3 mm quedan casi sólidos y no se doblan"],
                 ["Capas superior / inferior", "4 / 4", ""],
                 ["Relleno", "25 % giroide", ""],
                 ["Soportes", "No", "Ninguna pieza los necesita en la orientación indicada"],
                 ["Costura (seam)", "Atrás / alineada", "Que no quede dentro de las ranuras de los sensores"],
                 ["Compensación de pata de elefante", "0.15 mm", "Si no, la primera capa cierra los agujeros"],
                 ["Compensación X-Y de agujeros", "0", "Las holguras ya vienen en el modelo"],
                 ["Placa", "Textured PEI", "La pieza más grande mide 120 × 120 mm"]], [52, 38, 80]),
          h2("Tolerancias que ya trae el modelo"),
          tabla([["Elemento", "Medida nominal", "Medida impresa", "Variable en chasis.scad"],
                 ["Agujero M3 pasante", "3.0", "3.4", "M3_PASO"],
                 ["M3 roscado en plástico", "3.0", "2.8", "M3_ROSCA"],
                 ["Ranura de PCB (VL53L0X, TCS34725)", "1.6", "2.0", "RANURA"],
                 ["Ancho del VL53L0X en su soporte", "25.0", "25.4", "TOF + HOLGURA × 2"],
                 ["Ranura del TCS34725", "20.5", "20.9", "COLOR_MOD + HOLGURA × 2"],
                 ["Marco de protoboard", "35 × 47", "35.6 × 47.6", "PROTO + 0.3 × 2"],
                 ["Marco del OLED", "27.3 × 27.8", "27.9 × 28.4", "OLED + 0.3 × 2"],
                 ["Cuna del motor (ancho)", "12.0", "12.4", "HOLGURA × 2"],
                 ["Cuna del motor (alto)", "10.0", "9.7 (aprieta)", "MOT_H − 0.3"],
                 ["Botón de panel", "7.0", "7.3", "D_BOTON"],
                 ["Interruptor MTS-102", "6.0", "6.3", "D_SWITCH"]], [55, 30, 30, 55]),
          h2("Pieza de prueba"),
          img(os.path.join(IMG, "pieza_prueba.png"), 80, (150, 150, 1250, 950)),
          *lista([
              "Imprímela con los mismos ajustes: <b>PIEZA=\"prueba\"</b> (o chasis/stl/prueba.stl).",
              "Agujeros de arriba: M3 de 3.2, 3.4 y 3.6. El tornillo debe pasar libre en el de 3.4.",
              "Agujeros de abajo: 2.8 y 3.0. El M3 debe roscar apretado en el de 2.8.",
              "Agujeros grandes: botón (7.3) e interruptor (6.3).",
              "Bloque de la derecha: el N20 debe entrar empujando con el dedo, sin quedar flojo.",
              "Soporte de abajo: mete un VL53L0X desde arriba. Debe bajar sin forzar y no bailar. Si entra "
              "apretado, sube RANURA a 2.1; si baila, bájala a 1.9.",
              "Si algo queda apretado, sube HOLGURA a 0.25 o M3_PASO a 3.6 en chasis.scad y vuelve a exportar.",
              "Mide también tu TCS34725 y tu OLED con vernier: si difieren más de 0.3 mm del modelo, cambia "
              "COLOR_MOD u OLED antes de imprimir.",
          ]),
          h2("Exportar los STL"),
          p("Ya están en <b>chasis/stl/</b>. Si cambias una medida, abre chasis.scad en OpenSCAD, pon PIEZA con el "
            "nombre de la pieza, F6 y File → Export → STL. Desde terminal:"),
          Paragraph("<font face='Courier'>openscad -D 'PIEZA=\"piso1\"' -o piso1.stl chasis/chasis.scad</font>", S["p"]),
          PageBreak()]

    H += [h1("3. Preparación"),
          h2("Medir antes de imprimir"),
          tabla([["Qué medir", "Valor del modelo", "Variable"],
                 ["Diámetro y ancho de la rueda", "34 × 20 mm", "D_RUEDA, A_RUEDA"],
                 ["Separación de agujeros del L298N", "37 mm", "L298_AG"],
                 ["VL53L0X (ancho × alto del PCB)", "25 × 10.7 mm", "TOF"],
                 ["Lado del TCS34725", "20.5 mm", "COLOR_MOD"],
                 ["PCB del OLED", "27.3 × 27.8 mm", "OLED"],
                 ["Batería (largo × ancho)", "65 × 37 mm", "BAT"]], [70, 40, 60]),
          h2("Soldar"),
          *lista([
              "<b>Motores:</b> un capacitor de 100 nF entre las dos terminales de cada motor y dos cables de 20 cm.",
              "<b>TCS34725:</b> suelda 4 cables de 25 cm <b>directo</b> a VIN, GND, SDA y SCL, del lado de "
              "los componentes y saliendo hacia el borde de los pines. No lleva header: entra deslizando en una ranura.",
              "<b>VL53L0X:</b> header recto del lado <b>contrario</b> al sensor, con los pines apuntando hacia "
              "atrás. Quedan arriba al meterlo en su soporte.",
              "<b>OLED:</b> el header de fábrica, con los pines hacia atrás de la pantalla.",
              "<b>Interruptor:</b> un cable del + del conector T al interruptor y otro de salida de 30 cm.",
              "<b>Botón:</b> dos cables de 20 cm.",
          ]),
          h2("Probar en la mesa"),
          *lista([
              "Carga la batería (ver manual de uso).",
              "Conecta todo en la mesa siguiendo la sección 5, sin chasis.",
              "Pon el Nano en su protoboard, sube el código (manual de uso, sección 2) y enciende sosteniendo el botón: entras al modo calibración.",
              "Revisa que la OLED muestre el color y tres distancias que cambien al acercar la mano.",
              "Si sale <b>SIN SENSOR COLOR</b> o <b>SIN VL53L0X</b>, revisa ese cableado antes de ensamblar.",
          ], num=True),
          caja("Probar todo en la mesa toma 20 minutos y evita desarmar el robot completo por un cable flojo."),
          PageBreak()]

    pasos = [
        ("Paso 1 · Motores y ruedas", "paso1.png", None, [
            "Mete cada N20 en su cuna, con el eje hacia afuera.",
            "Presenta la cuna bajo el piso 1. Atornilla 2 M3 × 20 desde abajo, con tuerca arriba. Aprieta hasta que el "
            "motor no gire dentro de la cuna.",
            "Presiona cada rueda en su eje. Debe quedar a 1–2 mm del hueco del piso, sin rozar.",
            "Gira las ruedas con la mano: deben moverse libres.",
        ]),
        ("Paso 2 · Capucha de color y patín (vista de abajo)", "paso2.png", None, [
            "Atornilla la capucha con 2 M3 × 10 avellanados desde arriba del piso 1. Roscan directo en sus orejas.",
            "Atornilla el patín trasero con 1 M3 × 10 avellanado desde arriba.",
            "Desliza el TCS34725 en la capucha por la abertura de atrás, con el LED hacia el suelo y los cables "
            "hacia atrás, hasta que tope al frente. No necesita tornillos ni silicón.",
            "Lleva sus cables por debajo del piso 1 hasta el paso central y súbelos.",
            "Pon el robot en el suelo: se apoya en las dos ruedas; los patines quedan a 0.5 mm.",
        ]),
        ("Paso 3 · L298N, batería, VL53L0X y separadores", "paso3.png", None, [
            "Pon el L298N atrás, sobre 4 espaciadores, con 4 M3 × 16 desde arriba y tuerca abajo.",
            "Quita los jumpers ENA y ENB del L298N. Motor izquierdo a OUT1-OUT2 y derecho a OUT3-OUT4.",
            "Pega el velcro y acomoda la batería entre sus topes, acostada a lo ancho.",
            "Baja cada VL53L0X por las ranuras de su soporte: chip hacia afuera, pines arriba. Entra solo, sin tornillos.",
            "Atornilla los 4 separadores de 35 mm con M3 × 8 desde abajo del piso 1.",
        ]),
        ("Paso 4 · Piso 2: Nano, bus I2C, OLED, botón e interruptor", "paso4.png", None, [
            "Pega las 2 mini protoboards dentro de su marco: la izquierda para el Nano (USB-C hacia atrás), "
            "la derecha para el bus I2C.",
            "Pasa el header del OLED por la ranura del marco y acuéstalo, pantalla arriba.",
            "Mete el botón y el interruptor en sus agujeros y apriétalos con su tuerca.",
            "Sube los cables del piso 1 por las ranuras y conecta el OLED por debajo.",
            "Atornilla el piso 2 con 4 M3 × 8 sobre los separadores y haz el cableado de la sección 5.",
        ]),
    ]
    H.append(h1("4. Ensamble"))
    for titulo, im, _, items in pasos:
        H.append(KeepTogether([h2(titulo), img(os.path.join(IMG, im), 105, (150, 120, 1050, 900)), *lista(items, num=True)]))
    H.append(PageBreak())

    H += [h1("5. Cableado"),
          img(os.path.join(RAIZ, "atmega328p", "img", "conexiones_nano.png"), 170), Spacer(1, 4 * mm),
          tabla([["Módulo", "Pin", "Va a"], *PINES], [60, 45, 65]),
          h2("Protoboards"),
          p("<b>Izquierda:</b> el Nano montado cruzando el canal; cada pin queda con 2 o 3 hoyos libres para sus "
            "cables. <b>Derecha (bus):</b> no tiene rieles. Cada línea usa las dos mitades de una columna, unidas "
            "con un puente corto que cruza el canal central. Así quedan 8 hoyos libres por línea."),
          tabla([["Columna", "Línea", "Conexiones"],
                 ["1", "5V", "5V del Nano, VCC de los 3 VL53L0X, VIN del TCS34725, VCC de la OLED"],
                 ["4", "GND", "GND del Nano y de los 5 módulos"],
                 ["7", "SDA", "A4 y SDA de los 5 módulos"],
                 ["10", "SCL", "A5 y SCL de los 5 módulos"]], [20, 20, 130]),
          h2("Alimentación"),
          *lista([
              "Batería + → interruptor → L298N 12V y VIN del Nano.",
              "Batería − → L298N GND y GND del Nano. Todos los GND unidos.",
              "No uses la salida de 5V del L298N. Los módulos toman 5V del pin 5V del Nano.",
          ]),
          PageBreak()]

    H += [h1("6. Verificación"),
          tabla([["", "Revisión"],
                 ["☐", "Con el multímetro en continuidad y la batería desconectada: no hay pitido entre + y GND."],
                 ["☐", "Las ruedas giran libres y no rozan el chasis."],
                 ["☐", "El robot mide 120 × 120 mm o menos, incluidas las ruedas."],
                 ["☐", "Ningún cable cuelga bajo el piso 1 ni toca las ruedas."],
                 ["☐", "Primer encendido con el robot levantado: la OLED dice LABERINTO LISTO."],
                 ["☐", "Modo calibración: las tres distancias y el color responden."],
                 ["☐", "Avance de prueba (botón corto en calibración): las dos ruedas giran hacia adelante. Si una "
                       "gira al revés, intercambia sus dos cables en el L298N."],
                 ["☐", "Giro de prueba (botón largo): gira a la derecha. Si gira a la izquierda, intercambia los "
                       "motores en el L298N."]], [10, 160]),
          Spacer(1, 6 * mm), p("Con todo marcado, sigue con la calibración del <b>manual de uso</b>.")]
    construir("manual_ensamble.pdf", "Manual de ensamble", H)


# ---------- Manual de uso ----------
def manual_uso():
    H = []
    H += [Spacer(1, 30 * mm), Paragraph("Manual de uso", S["t"]),
          Paragraph("Robot de laberinto · Arduino Nano (ATmega328P)", S["st"]), Spacer(1, 10 * mm),
          img(os.path.join(IMG, "iso.png"), 130, (200, 120, 1250, 1000)), Spacer(1, 8 * mm),
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
