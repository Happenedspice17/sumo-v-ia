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
ZOOM = {"placa_x2d": 1, "det_l298": 1, "iso": 1.25, "fig_atras": 1.25, "fig_lado": 1.3, "paso10": 1.35, "det_arnes": 0.95, "paso9": 0.85}
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


VISTAS = {
    # nombre: (defs, camara, [(texto, punto, (dx, dy))])
    "iso": ({"PASO": 0}, FRENTE, []),
    "fig_atras": ({"PASO": 0}, ATRAS, []),
    "fig_lado": ({"PASO": 0}, LADO, []),
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
    "paso7": ({"PIEZA": "sub_piso2"}, (60, -170, 230, 0, -12, 70), [
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
    "paso8": ({"PASO": 8}, FRENTE, [
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
    "paso9": ({"PASO": 9}, ARRIBA, [
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
    "unoq_iso": ({"PLACA": "unoq"}, (300, -330, 330, 0, 5, 85), [
        ("Arduino UNO Q\n(4 M3×8 a insertos)", (10, -31, 72), (-250, 150)),
        ("Cámara UVC 32 × 32\nlente M12 gran angular", (0, 30, 165), (-260, -60)),
        ("Mástil PTR 10 o 15\n(medida pendiente)", (7.5, 10.5, 115), (-260, 40)),
        ("Hub USB en repisa\n(4 M3×8 a insertos)", (20, 39.5, 96.5), (240, -40)),
        ("OLED atrás del mástil", (0, 1, 100), (-240, -20)),
        ("USB-C en ángulo", (-38, -20, 74), (-220, 60)),
    ]),
    "unoq_lado": ({"PLACA": "unoq"}, (-520, 70, 150, 0, 90, 85), [
        ("Lente a 150 mm,\n25° hacia abajo", (0, 30, 150), (220, -120)),
        ("Campo de visión\n≈ 100° × 75°", (0, 139, 99), (-200, -160)),
        ("El piso se ve desde\n≈ 3 cm frente al robot", (0, 92, 0), (-200, 60)),
        ("Hub: queda bajo\nel campo de visión", (0, 54, 96), (230, 120)),
    ]),
    "uno_r3": ({"PLACA": "uno_r3"}, (300, -330, 300, 0, 0, 55), [
        ("UNO R3 en los mismos\n4 postes", (10, -31, 72), (-250, 150)),
        ("USB-B y jack salen\n6 mm por la izquierda", (-38, -20, 76), (-230, -60)),
        ("Columnas movidas a\n(±48, −40)", (48, -40, 45), (230, 60)),
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
