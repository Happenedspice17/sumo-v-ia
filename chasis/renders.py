"""Genera las imagenes del manual (chasis/img/) desde chasis.scad, con etiquetas.

Uso: python3 chasis/renders.py [nombre ...]   (sin nombres: todas)
Necesita openscad y xvfb-run. Cada etiqueta se ubica renderizando una esfera en su punto 3D con la
misma camara, asi que la flecha siempre cae donde esta la pieza.
"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
SCAD = os.path.join(AQUI, "chasis.scad")
IMG = os.path.join(AQUI, "img")
TAM = (1400, 1100)
ZOOM = {"placa_x2d": 1, "det_l298": 1, "iso": 1.25, "fig_atras": 1.25, "fig_lado": 1.3, "paso10": 1.35, "det_arnes": 0.95, "paso9": 0.85, "det_q_usb": 1.25}
FONDO_TOL = 12

FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
NEGRITA = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Camaras: ojo, centro
FRENTE = (190, 260, 230, 0, 0, 45)
ATRAS = (60, -250, 210, 0, -18, 35)
ABAJO_ATRAS = (170, -230, -170, 0, -5, 18)
ABAJO_FRENTE = (150, 230, -170, 0, 5, 15)
ARRIBA = (0, -25, 430, 0, 0, 60)
LADO = (330, 0, 60, 0, 0, 45)

# Puntos de referencia (mm, coordenadas del robot)
Z1, ESP, SEP = 22, 3, 35
Z2 = Z1 + ESP + SEP
ZP = Z2 + ESP + 9.5
L298_Y = -37.5
BORNE_Z = Z1 + ESP + 5 + 1.6 + 4
XP = 35 / 2 + 1.1


def hx(c, k):
    return c + (1 if k > 0 else -1) * (3.81 + 2.54 * (abs(k) - 1))


def hy(j):
    return -32.6 + (j - 8) * 2.54


def pin_nano(i):
    return hy(1 + i)


# UNO: headers, protoboard del shield y alturas (mismas formulas que chasis.scad)
UNO_X0, UNO_Y0 = -34.29, -58.0
UNO_H = [["SCL", "SDA", "AREF", "GND", "D13", "D12", "D11", "D10", "D9", "D8"], ["D7", "D6", "D5", "D4", "D3", "D2", "D1", "D0"],
         ["NC", "IOREF", "RESET", "3V3", "5V", "GND2", "GND3", "VIN"], ["A0", "A1", "A2", "A3", "A4", "A5"]]
UNO_HX = [19.05, 19.05 + 9 * 2.54 + 4.064, 27.94, 50.8]
UNO_HY = [50.8, 50.8, 2.54, 2.54]


def pin(n):
    for h in range(4):
        if n in UNO_H[h]:
            return UNO_X0 + UNO_HX[h] + UNO_H[h].index(n) * 2.54, UNO_Y0 + UNO_HY[h]
    raise KeyError(n)


def shield_z(placa):
    return 70.6 + (11.5 if placa == "uno_r3" else 8.5)


def zhd(placa):
    return shield_z(placa) + 1.6 + 8.5


def zbb(placa):
    return shield_z(placa) + 1.6 + 9.5


def bb(i, j):
    """hoyo de la mini protoboard: columna i (0..16), fila j (0..9)"""
    return (i - 8) * 2.54, -31.33 + (-(3.81 + (4 - j) * 2.54) if j < 5 else 3.81 + (j - 5) * 2.54)


VISTAS = {
    # nombre: (defs, camara, [(texto, punto, (dx, dy))])
    "iso": ({"PASO": 0, "PLACA": "nano"}, FRENTE, []),
    "fig_atras": ({"PASO": 0, "PLACA": "nano"}, ATRAS, []),
    "fig_lado": ({"PASO": 0, "PLACA": "nano"}, LADO, []),
    "paso1": ({"PASO": 1}, ABAJO_ATRAS, [
        ("Cuna del motor", (26.5, -12, 13), (230, 120)),
        ("Motor N20", (-30, -6, 14), (-260, 60)),
        ("Capacitor 100 nF\nentre terminales", (-12.5, 0, 19.5), (-250, -150)),
        ("Cables por la\nranura de 10 × 10", (-27, -27, 30), (-180, -170)),
        ("Oreja con inserto;\nM3×12 desde arriba", (26.5, 29, 10.5), (180, -160)),
    ]),
    "paso2": ({"PASO": 2}, ABAJO_FRENTE, [
        ("TCS34725: entra deslizando\npor atrás, LED al suelo", (0, 28, 6), (280, 200)),
        ("Capucha (2 M3×8)", (-14, 46, 8), (-300, 140)),
        ("Patín delantero", (0, 48.5, 2.5), (-120, 230)),
        ("Patín trasero (2 M3×8)", (0, -52, 2), (230, -40)),
        ("Rueda a presión\nen el eje", (-50, 8, 10), (-260, -80)),
    ]),
    "paso3": ({"PASO": 3}, ATRAS, [
        ("OUT1-OUT2\nmotor izquierdo", (-21.5, -32.5, BORNE_Z), (-260, -40)),
        ("OUT3-OUT4\nmotor derecho", (21.5, -32.5, BORNE_Z), (230, -120)),
        ("Poste con inserto\n+ M3×8", (18.5, -56, 28), (200, 120)),
        ("Cables del motor por\nla ranura de su lado", (27, -26, 27), (260, 30)),
        ("Quita los jumpers\nENA y ENB", (1, -21.5, 41), (-120, -230)),
    ]),
    "det_l298": ({"PIEZA": "det_l298"}, (0, -45, 150, 0, -33, 30), [
        ("12V (batería)", (18, -16, BORNE_Z + 4), (170, -170)),
        ("GND", (13, -16, BORNE_Z + 4), (60, -230)),
        ("5V: no se usa", (8, -16, BORNE_Z + 4), (-60, -260)),
        ("ENA", (1, -19, 41), (-80, -170)),
        ("IN1 IN2 IN3 IN4", (-5.3, -19, 41), (-260, -150)),
        ("ENB", (-11.7, -19, 41), (-300, -60)),
        ("Jumper 5V-EN:\nse queda", (3.9, -18, 38), (240, -40)),
        ("OUT1 OUT2", (-21.5, -32.5, BORNE_Z), (-260, 60)),
        ("OUT3 OUT4", (21.5, -32.5, BORNE_Z), (240, 80)),
    ]),
    "paso4": ({"PASO": 4}, FRENTE, [
        ("Batería 2S sobre velcro", (18, 7, 44), (260, -120)),
        ("Conector T macho", (-18, 10, 51), (-150, -220)),
        ("Balanceo (solo para\ncargar)", (-25, 20, 49), (-300, -60)),
        ("Topes", (33.7, -6.7, 33), (250, 40)),
    ]),
    "paso5": ({"PASO": 5}, FRENTE, [
        ("VL53L0X frente", (0, 54.5, 30), (230, 160)),
        ("VL53L0X izquierdo", (-50.5, 34.5, 30), (-230, 130)),
        ("VL53L0X derecho", (50.5, 34.5, 30), (230, 60)),
        ("5 dupont (GPIO1 libre),\nantes de meterlo", (0, 50, 35), (-80, 230)),
        ("Cables hacia arriba", (23, 33.2, 62), (250, -150)),
    ]),
    "paso6": ({"PASO": 6}, ATRAS, [
        ("Columna impresa\n(inserto arriba)", (48, -40, 45), (220, 60)),
        ("Dupont en ENA … ENB", (-5, -19, 47), (-200, -220)),
        ("Cables hacia arriba", (-5, -3, 62), (120, -230)),
    ]),
    "paso7": ({"PIEZA": "sub_piso2", "PLACA": "nano"}, (60, -170, 230, 0, -12, 70), [
        ("Nano: USB hacia atrás", (-19.9, -52, ZP + 5), (-260, 80)),
        ("Bus 5V (columna 4)", (hx(XP, 1) + 3, hy(13), ZP + 1), (250, 0)),
        ("Bus GND (columna 1)", (hx(XP, 1) + 3, hy(16), ZP + 1), (250, -110)),
        ("Bus SDA (columna 10)", (hx(XP, 1) + 3, hy(7), ZP + 1), (250, 110)),
        ("Bus SCL (columna 7)", (hx(XP, 1) + 3, hy(10), ZP + 1), (250, 50)),
        ("Puentes del Nano\nal bus", (-2, hy(11), ZP + 2), (-60, 260)),
        ("OLED, pines al fondo", (0, 39.4, Z2 + ESP + 3), (-200, -200)),
        ("Botón", (-38, 5, Z2 + ESP + 6), (-200, -40)),
        ("Interruptor", (38, 5, Z2 + ESP + 9), (200, -120)),
        ("Ranuras de cables", (26.5, 34.5, Z2 + ESP), (220, -200)),
    ]),
    "paso8": ({"PASO": 8, "PLACA": "nano"}, FRENTE, [
        ("Piso 2 armado", (-40, 20, Z2 + ESP), (-230, -120)),
        ("Cables de sensores\npor las ranuras", (-26.5, 30, Z2 + ESP + 4), (-150, -250)),
        ("M3×8 en cada\ncolumna", (42, 50, Z2 + ESP + 3), (220, -60)),
    ]),
    "det_arnes": ({"PIEZA": "det_arnes"}, (200, -150, 170, 10, -3, 45), [
        ("Interruptor: rojo a una pata\nexterior, 2 naranjas al centro", (38, 5, 46), (180, -200)),
        ("Conector T hembra", (-6, 10, 51), (-200, -180)),
        ("Naranja a 12V", (18, -15, BORNE_Z), (60, 200)),
        ("2 negros en GND:\nconector T y Nano", (13, -15, BORNE_Z), (-260, 170)),
        ("Naranja y negro suben\npor la ranura central", (20, -3, 58), (-160, -260)),
    ]),
    "paso9": ({"PASO": 9, "PLACA": "nano"}, ARRIBA, [
        ("XSHUT → A0 A1 A2", (hx(-XP, 4), pin_nano(4), ZP + 18), (240, -20)),
        ("L298N → D5 … D10", (hx(-XP, -4), pin_nano(5), ZP + 18), (-240, -70)),
        ("Botón → D2 y GND", (hx(-XP, -5), pin_nano(10), ZP + 15), (-240, 90)),
        ("VIN y GND\n(cable rígido)", (hx(-XP, 4), pin_nano(14), ZP + 3), (-60, -260)),
        ("Sensores → bus", (hx(XP, 2), hy(13), ZP + 17), (240, 60)),
    ]),
    "paso10": ({"PIEZA": "det_arnes", "UNIDO": "true"}, (-140, 120, 150, -12, 10, 45), [
        ("Une el conector T", (-12, 10, 51), (200, -180)),
        ("Interruptor en OFF", (38, 5, 60), (220, 40)),
    ]),
    "det_insertos": ({"PIEZA": "det_insertos"}, (230, -260, 300, 40, 0, 10), [
        ("Columnas: 4", (48, -40, 38), (-200, -120)),
        ("Postes del L298N: 4", (-18.5, -56, 8), (-220, 60)),
        ("Cunas: 2 c/u", (80, 39, 11.7), (200, -150)),
        ("Capucha: 2", (107, 60, 20), (200, -40)),
        ("Patín: 2", (116, -50, 22), (200, 80)),
    ]),
    # ---- UNO R3 / UNO Q: las piezas impresas son las mismas; la Q solo agrega mastil, camara, repisa, hub y clip ----
    "r3_iso": ({"PLACA": "uno_r3"}, (250, 290, 250, 0, 0, 60), [
        ("Arduino UNO R3\n(4 M3×8 a insertos)", (34.2, -30, 70), (-250, 180)),
        ("Proto Shield + mini\nprotoboard: bus I2C", (30, -45, 83), (-250, 160)),
        ("Tiras hembra del shield:\ndupont de L298N y botón", (20, -7.2, zhd("uno_r3")), (-250, -120)),
        ("OLED en el marco\ndel piso 2", (0, 39.4, 66), (230, 20)),
        ("Cables de sensores:\nsuben por las ranuras", (-29.2, 34, 70), (250, -20)),
        ("VL53L0X frente", (0, 54.5, 30), (230, 170)),
        ("Interruptor", (38, 5, 73), (-230, 80)),
    ]),
    "r3_atras": ({"PLACA": "uno_r3"}, (-250, -290, 250, 0, 0, 60), [
        ("Header de potencia: VIN,\nGND, 5V (R3) o 3V3 (Q)", (pin("VIN")[0], pin("VIN")[1], zhd("uno_r3")), (250, -230)),
        ("A0 A1 A2: XSHUT\nde los VL53L0X", (pin("A1")[0], pin("A1")[1], zhd("uno_r3")), (250, -150)),
        ("USB-B del R3", (-34.3, -19.9, 77), (-250, 40)),
        ("L298N", (0, -58, 40), (250, 90)),
    ]),
    "q_iso": ({"PLACA": "unoq"}, (300, -330, 330, 0, 5, 85), [
        ("Arduino UNO Q\n(4 M3×8 a insertos)", (30, -50, 72), (-250, 150)),
        ("Proto Shield con mini\nprotoboard: bus I2C", (-15, -31, 91), (230, 140)),
        ("Cámara UVC 32 × 32\nlente M12 gran angular", (0, 30, 165), (-260, -60)),
        ("Mástil PTR 10 o 15\n(medida pendiente)", (7.5, 10.5, 120), (-260, 40)),
        ("Hub USB en repisa\n(4 M3×8 a insertos)", (20, 39.5, 96.5), (240, -40)),
        ("OLED de cabeza en el\nclip del mástil", (0, -3, 120), (-240, -20)),
        ("Cable USB-C en ángulo", (-38, -20, 76), (-220, 60)),
    ]),
    "q_lado": ({"PLACA": "unoq"}, (-560, 40, 150, 0, 40, 85), [
        ("Lente a 150 mm,\n25° hacia abajo", (0, 30, 150), (220, -120)),
        ("Campo de visión\n≈ 100° × 75°", (0, 139, 99), (-200, -160)),
        ("El piso se ve desde\n≈ 3 cm frente al robot", (0, 92, 0), (-200, 60)),
        ("Hub: queda bajo\nel campo de visión", (0, 54, 96), (230, 120)),
    ]),
    "r3_paso7": ({"PIEZA": "sub_piso2", "PLACA": "uno_r3"}, (170, -170, 210, 0, -12, 70), [
        ("UNO R3 sobre 4 postes\ncon inserto (4 M3×8)", (34.2, -40, 70), (250, 100)),
        ("Proto Shield: sus pines\nentran en los headers", (-34.3, -30, 82), (-250, 120)),
        ("Mini protoboard 170", (0, -31, zbb("uno_r3")), (-250, -40)),
        ("Puentes del bus", (bb(6, 5)[0], bb(6, 5)[1], zbb("uno_r3") + 2.5), (250, -60)),
        ("OLED en su marco\n(pines al fondo)", (0, 39.4, 66), (-230, -180)),
        ("Botón", (-38, 5, 70), (-230, -80)),
        ("Interruptor", (38, 5, 73), (230, -180)),
    ]),
    "r3_paso8": ({"PASO": 8, "PLACA": "uno_r3"}, FRENTE, [
        ("Piso 2 armado, sobre las\ncolumnas (4 M3×8)", (-40, 20, Z2 + ESP), (-230, -120)),
        ("Cables de sensores\npor las ranuras", (-26.5, 30, Z2 + ESP + 4), (-150, -250)),
        ("Cables de potencia y\nlógica: ranura central", (20, -3, Z2 + ESP + 2), (-230, 40)),
    ]),
    "r3_paso9": ({"PASO": 9, "PLACA": "uno_r3"}, (190, -250, 250, 0, -25, 90), [
        ("XSHUT → A0 A1 A2", (pin("A1")[0], pin("A1")[1], zhd("uno_r3") + 14), (240, -60)),
        ("L298N → D5 … D10", (pin("D8")[0], pin("D8")[1], zhd("uno_r3") + 14), (-240, -170)),
        ("Botón → D2 y GND", (pin("D2")[0], pin("D2")[1], zhd("uno_r3") + 14), (240, -170)),
        ("VIN y GND\n(potencia)", (pin("VIN")[0], pin("VIN")[1], zhd("uno_r3") + 1.2), (-240, 60)),
        ("Sensores → bus", (bb(8, 8)[0], bb(8, 8)[1], zbb("uno_r3") + 14), (240, 60)),
    ]),
    "r3_paso10": ({"PIEZA": "det_arnes", "UNIDO": "true"}, (-140, 120, 150, -12, 10, 45), [
        ("Une el conector T", (-12, 10, 51), (200, -180)),
        ("Interruptor en OFF", (38, 5, 60), (220, 40)),
    ]),
    "q_paso11": ({"PASO": 11, "PLACA": "unoq"}, (300, -330, 330, 0, 5, 85), [
        ("Mástil (PTR)", (7.5, 10.5, 120), (-250, 40)),
        ("Cámara en su cabeza\nimpresa", (0, 30, 150), (-250, -80)),
        ("Clip del OLED\nsobre el mástil", (0, -4, 108), (-250, 150)),
        ("Repisa: 4 M3×8", (50, 40, 84.5), (240, -60)),
        ("Hub USB", (20, 39.5, 96.5), (240, 60)),
        ("Cables USB", (-51.5, 30, 90.5), (-250, 230)),
    ]),
    "det_shield": ({"PIEZA": "det_shield", "PLACA": "uno_r3"}, (0, -170, 250, 0, -28, 85), [
        ("Columna VCC", (bb(6, 9)[0], bb(6, 9)[1], zbb("uno_r3") + 14), (-250, -170)),
        ("Columna GND", (bb(7, 9)[0], bb(7, 9)[1], zbb("uno_r3") + 14), (-250, -90)),
        ("Columna SCL", (bb(8, 9)[0], bb(8, 9)[1], zbb("uno_r3") + 14), (250, -170)),
        ("Columna SDA", (bb(9, 9)[0], bb(9, 9)[1], zbb("uno_r3") + 14), (250, -90)),
        ("SDA y SCL del UNO\n(junto a AREF)", (pin("SDA")[0], pin("SDA")[1], zhd("uno_r3") + 14), (-250, 40)),
        ("D5 … D10: L298N", (pin("D8")[0], pin("D8")[1], zhd("uno_r3") + 14), (-250, 150)),
        ("D2: botón", (pin("D2")[0], pin("D2")[1], zhd("uno_r3") + 14), (250, 30)),
        ("VIN, GND, 5V/3V3", (pin("GND3")[0], pin("GND3")[1], zhd("uno_r3") + 14), (-250, -250)),
        ("A0 A1 A2: XSHUT", (pin("A1")[0], pin("A1")[1], zhd("uno_r3") + 14), (250, -250)),
        ("Puentes del bus", (bb(6, 5)[0], bb(6, 5)[1], zbb("uno_r3") + 2.5), (250, 110)),
    ]),
    "det_q_usb": ({"PIEZA": "det_q_usb", "PLACA": "unoq"}, (-260, 230, 230, 0, 25, 95), [
        ("Hub USB (cinchos)", (0, 39.5, 96.5), (240, -20)),
        ("Repisa sobre 4 postes", (-52, 26, 84.5), (-240, 60)),
        ("Hub → USB-C del UNO Q", (-51.5, 30, 90.5), (-240, -40)),
        ("Cámara → hub", (13, 40, 102.5), (240, 120)),
        ("USB-C del UNO Q", (-38, -20, 75), (-240, 160)),
    ]),
    "placa_x2d": ({"PIEZA": "placa_vista"}, (128, 127, 720, 128, 128, 0), []),
}


def correr(salida, defs, cam):
    args = ["xvfb-run", "-a", "openscad", "-o", salida, f"--imgsize={TAM[0]},{TAM[1]}", "--colorscheme=Tomorrow",
            "--camera=" + ",".join(str(c) for c in cam)]
    for k, v in defs.items():
        crudo = not isinstance(v, str) or v in ("true", "false") or v.startswith("[")
        args += ["-D", f"{k}={v}" if crudo else f'{k}="{v}"']
    args.append(SCAD)
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def ubicar(cam, punto, tmp):
    ruta = os.path.join(tmp, f"m_{abs(hash((cam, punto)))}.png")
    correr(ruta, {"PIEZA": "marca", "MARCA": "[%s]" % ",".join(str(c) for c in punto)}, cam)
    im = Image.open(ruta).convert("RGB")
    px = im.load()
    xs, ys = [], []
    for y in range(im.height):
        for x in range(im.width):
            r, g, b = px[x, y]
            if r > 120 and g < 110 and b < 110:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise RuntimeError(f"marca fuera de cuadro: {punto}")
    return sum(xs) / len(xs), sum(ys) / len(ys)


def caja_contenido(im):
    fondo = im.getpixel((2, 2))
    px = im.load()
    x0, y0, x1, y1 = im.width, im.height, 0, 0
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            if sum(abs(a - b) for a, b in zip(px[x, y], fondo)) > FONDO_TOL:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return x0, y0, x1, y1


def etiquetar(im, etiquetas):
    """Etiquetas en dos columnas, a los lados del modelo; dx < 0 la manda a la izquierda."""
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FUENTE, 32)
    bx0, by0, bx1, by1 = caja_contenido(im)
    cajas = []
    for texto, (x, y), (dx, dy) in etiquetas:
        c = d.multiline_textbbox((0, 0), texto, font=f, spacing=4)
        cajas.append([texto, x, y, dx < 0, c[2] - c[0] + 18, c[3] - c[1] + 14, y + dy * 0.25])
    for izq in (True, False):
        lado = sorted([c for c in cajas if c[3] == izq], key=lambda c: c[6])
        fin = -1e9
        for c in lado:
            c[6] = max(c[6], fin + c[5] / 2 + 12)
            fin = c[6] + c[5] / 2
    for texto, x, y, izq, w, h, yc in cajas:
        x0 = bx0 - 40 - w if izq else bx1 + 40
        y0 = yc - h / 2
        lx = x0 + w if izq else x0
        d.line([(x, y), (lx, yc)], fill=(201, 122, 30), width=3)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(201, 122, 30))
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=6, fill=(255, 246, 222), outline=(214, 150, 60), width=2)
        d.multiline_text((x0 + 9, y0 + 6), texto, font=f, fill=(40, 40, 40), spacing=4)


def recortar(im, margen=20):
    fondo = im.getpixel((2, 2))
    px = im.load()
    x0, y0, x1, y1 = im.width, im.height, 0, 0
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            if sum(abs(a - b) for a, b in zip(px[x, y], fondo)) > FONDO_TOL:
                x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
    return im.crop((max(0, x0 - margen), max(0, y0 - margen), min(im.width, x1 + margen), min(im.height, y1 + margen)))


def acercar(cam, f):
    ojo, centro = cam[:3], cam[3:]
    return tuple(c + (o - c) * f for o, c in zip(ojo, centro)) + tuple(centro)


def hacer(nombre):
    defs, cam, marcas = VISTAS[nombre]
    cam = acercar(cam, ZOOM.get(nombre, 0.88))
    with tempfile.TemporaryDirectory() as tmp:
        base = os.path.join(tmp, "base.png")
        correr(base, defs, cam)
        im = Image.open(base).convert("RGB")
        # lienzo mas grande para que quepan las etiquetas
        lienzo = Image.new("RGB", (TAM[0] + 1000, TAM[1] + 500), im.getpixel((2, 2)))
        lienzo.paste(im, (500, 250))
        puntos = [ubicar(cam, m[1], tmp) for m in marcas]
        etiquetar(lienzo, [(m[0], (x + 500, y + 250), m[2]) for m, (x, y) in zip(marcas, puntos)])
        recortar(lienzo).save(os.path.join(IMG, nombre + ".png"))
    print("img/" + nombre + ".png")


if __name__ == "__main__":
    nombres = sys.argv[1:] or list(VISTAS)
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(hacer, nombres))
