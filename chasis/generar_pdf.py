"""Genera chasis.pdf: planos acotados del chasis (Arduino Nano / ATmega328P).

Uso: python3 generar_pdf.py   (las vistas 3D salen de img/, renderizadas desde chasis.scad)
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------- Medidas (mismas que chasis.scad) ----------
L, R_ESQ, ESP = 120, 30, 3
D_RUEDA, A_RUEDA = 34, 20
MOT_L, MOT_A, MOT_H = 24, 12, 10
EJE_Z = D_RUEDA / 2
X_RUEDA_INT = L / 2 - A_RUEDA
X_MOT = X_RUEDA_INT - 1.5 - MOT_L / 2
POZO_X, POZO_Y = X_RUEDA_INT - 2, 19
Z1 = EJE_Z + MOT_H / 2
SEP = 35
Z2 = Z1 + ESP + SEP
POSTES = [(42, 50), (-42, 50), (48, -40), (-48, -40)]
BAT, BAT_Y = (65, 37, 19), 7
L298, L298_Y, L298_AG = (43, 43, 27), -37.5, 37
TOF = (25, 10.7)
TOF_FRENTE_Y, TOF_LADO = 54, (50, 34.5)
TOF_CARA = 1.8                      # del centro del soporte a la cara del sensor
HEADER, DUPONT = 2.5, 14            # plastico del header recto y largo del dupont
TOF_ATRAS = 0.3 + HEADER + DUPONT   # del centro del soporte al final del dupont
TOF_PASILLO = TOF_ATRAS + 10        # pasillo libre detras del sensor (dupont + doblez del cable)
TOF_PIN_Z = Z1 + ESP + TOF[1] - 1.3
COLOR_Y, COLOR_MOD, COLOR_Z = 34, 20.5, 5
PATIN_Y = -52
PATIN_X = 26
CUNA_Y = (-16.8, 29)
PROTO, PROTO_Y = (35, 47, 9.5), -32.6
NANO = (18, 44)
OLED, OLED_Y = (27.3, 27.8), 39.4
OLED_PINES_Y = OLED_Y - OLED[1] / 2 + 2.5
BOTON_XY, SWITCH_XY = (-38, 5), (38, 5)
RAN2_X = 26.5                       # ranuras de cables del piso 2
PASILLO = 180
ALTO = Z2 + ESP + PROTO[2] + 22          # dupont parados en las protoboards y sus cables

C = {
    "piso": "#c9d6ea", "borde": "#33415c", "rueda": "#222222", "motor": "#d4a017",
    "bat": "#4169e1", "l298": "#d62728", "placa": "#138a8a", "tof": "#2ca02c",
    "color": "#7b2d8b", "oled": "#eeeeee", "imp": "#f39c12", "cota": "#c0392b",
    "pared": "#8d6e63", "texto": "#1b1b1b", "proto": "#e74c3c",
}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def pagina(titulo, sub=""):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.95, titulo, fontsize=17, weight="bold", color=C["texto"])
    if sub:
        fig.text(0.04, 0.915, sub, fontsize=10, color="#555")
    fig.text(0.96, 0.025, "Robot laberinto · Arduino Nano · cotas en mm", fontsize=7, color="#888", ha="right")
    return fig


def ejes(fig, rect, lim):
    ax = fig.add_axes(rect)
    ax.set_aspect("equal")
    ax.set_xlim(*lim[0])
    ax.set_ylim(*lim[1])
    ax.axis("off")
    return ax


def caja(ax, cx, cy, w, h, col, txt=None, alpha=1, ls="-", fs=7, tc=None, z=2):
    ax.add_patch(Rectangle((cx - w / 2, cy - h / 2), w, h, fc=col, ec=C["borde"],
                           lw=0.8, alpha=alpha, ls=ls, zorder=z))
    if txt:
        ax.text(cx, cy, txt, ha="center", va="center", fontsize=fs, color=tc or C["texto"], zorder=z + 1)


def cota(ax, p1, p2, txt, off=8, horiz=True, fs=7):
    (x1, y1), (x2, y2) = p1, p2
    if horiz:
        y = y1 + off
        ax.plot([x1, x1], [y1, y], color=C["cota"], lw=0.5)
        ax.plot([x2, x2], [y2, y], color=C["cota"], lw=0.5)
        ax.annotate("", (x1, y), (x2, y), arrowprops=dict(arrowstyle="<->", color=C["cota"], lw=0.7))
        ax.text((x1 + x2) / 2, y + 1.5, txt, ha="center", va="bottom", fontsize=fs, color=C["cota"])
    else:
        x = x1 + off
        ax.plot([x1, x], [y1, y1], color=C["cota"], lw=0.5)
        ax.plot([x2, x], [y2, y2], color=C["cota"], lw=0.5)
        ax.annotate("", (x, y1), (x, y2), arrowprops=dict(arrowstyle="<->", color=C["cota"], lw=0.7))
        ax.text(x + 1.5, (y1 + y2) / 2, txt, ha="left", va="center", fontsize=fs, color=C["cota"], rotation=90)


def placa_redonda(ax, col=C["piso"], z=1):
    ax.add_patch(FancyBboxPatch((-L / 2 + R_ESQ, -L / 2 + R_ESQ), L - 2 * R_ESQ, L - 2 * R_ESQ,
                                boxstyle=f"round,pad={R_ESQ}", fc=col, ec=C["borde"], lw=1.2, zorder=z))


def agujero(ax, x, y, d=3.4, z=6):
    ax.add_patch(Circle((x, y), d / 2, fc="white", ec="k", lw=0.6, zorder=z))


def frente(ax, x=-80):
    ax.annotate("FRENTE", (x, 72), (x, 86), ha="center", fontsize=9, weight="bold",
                arrowprops=dict(arrowstyle="<-", lw=1.2))


def texto(fig, txt):
    tx = fig.add_axes([0.64, 0.1, 0.34, 0.78])
    tx.axis("off")
    tx.text(0, 1, txt, va="top", fontsize=9.5, linespacing=1.45)


def ruedas_planta(ax):
    for s in (-1, 1):
        caja(ax, s * (X_RUEDA_INT + A_RUEDA / 2), 0, A_RUEDA, D_RUEDA, C["rueda"], "rueda", fs=6, tc="white", z=4)
        caja(ax, s * X_MOT, 0, MOT_L, MOT_A, C["motor"], "N20", fs=6, z=4)


# ---------- Paginas ----------
GIRO = math.sqrt(2) * (L / 2 - R_ESQ) + R_ESQ
D_LADO = PASILLO / 2 - (TOF_LADO[0] + TOF_CARA)
D_FRENTE = PASILLO / 2 - (TOF_FRENTE_Y + TOF_CARA)


def portada(pp):
    fig = pagina("Chasis robot de laberinto", f"Arduino Nano (ATmega328P) · {L} × {L} mm con ruedas · 2 pisos impresos")
    p = os.path.join(AQUI, "img", "iso.png")
    ax = fig.add_axes([0.0, 0.08, 0.55, 0.8])
    ax.imshow(plt.imread(p)[120:1000, 250:1150])
    ax.axis("off")
    texto(fig, (
        "Cumple los lineamientos\n"
        f"• Huella {L} × {L} mm con ruedas (máximo 120 × 120).\n"
        f"• Alto ≈ {ALTO:.0f} mm con cables (sin límite).\n"
        "• Sensor de color I2C, OLED y botón de arranque.\n\n"
        "Pisos\n"
        f"• Piso 1 (a {Z1:.0f} mm): motores, ruedas, patines,\n"
        "  sensor de color, batería, L298N y 3 VL53L0X.\n"
        f"• Piso 2 (a {Z2:.0f} mm): Nano y bus I2C en 2 mini\n"
        "  protoboards, OLED, botón e interruptor.\n\n"
        "Sensores sin tornillos\n"
        "• VL53L0X: header recto, pines hacia adentro;\n"
        "  bajan por ranuras en el piso 1. Detrás de cada uno\n"
        f"  queda un pasillo libre de {TOF_PASILLO:.0f} mm para el dupont.\n"
        "• TCS34725: entra deslizando por atrás de la capucha.\n"
        "• OLED y protoboards: entran en su marco.\n\n"
        "Giro\n"
        f"• Esquinas R{R_ESQ}: radio de giro {GIRO:.0f} mm contra\n"
        f"  {PASILLO / 2:.0f} mm de medio pasillo.\n\n"
        "Medir antes de imprimir\n"
        f"• Rueda Ø{D_RUEDA} × {A_RUEDA}; agujeros del L298N a {L298_AG}.\n"
        f"• VL53L0X {TOF[0]} × {TOF[1]}; TCS34725 {COLOR_MOD} × {COLOR_MOD}.\n"
        f"• OLED {OLED[0]} × {OLED[1]}."
    ))
    pp.savefig(fig)
    plt.close(fig)


def soporte_tof(ax, x, y, s):
    """Soporte de VL53L0X en planta; s = direccion a la que mira: 'N', 'E', 'O'."""
    a = TOF[0] + 0.4
    w = 6 * 2.54                     # ancho de los 6 dupont
    if s == "N":
        caja(ax, x, y, a + 3, 5, C["imp"], z=5)
        caja(ax, x, y + 0.5, TOF[0], 1.6, C["tof"], z=6)
        caja(ax, x, y - 0.3 - HEADER / 2, w, HEADER, "#666", z=6)
        caja(ax, x, y - 0.3 - HEADER - DUPONT / 2, w, DUPONT, "#111", z=6)
        caja(ax, x, y - TOF_ATRAS - 5, w, 10, "white", ls="--", z=4)
        ax.annotate("", (x, y + 28), (x, y + 3), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    else:
        k0 = 1 if s == "E" else -1
        caja(ax, x, y, 5, a + 3, C["imp"], z=5)
        caja(ax, x + k0 * 0.5, y, 1.6, TOF[0], C["tof"], z=6)
        caja(ax, x - k0 * (0.3 + HEADER / 2), y, HEADER, w, "#666", z=6)
        caja(ax, x - k0 * (0.3 + HEADER + DUPONT / 2), y, DUPONT, w, "#111", z=6)
        caja(ax, x - k0 * (TOF_ATRAS + 5), y, 10, w, "white", ls="--", z=4)
        ax.annotate("", (x + k0 * 28, y), (x + k0 * 3, y), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))


def planta_piso1(pp):
    fig = pagina("Piso 1 · planta", f"Placa de {ESP} mm a {Z1:.0f} mm del suelo. Motores debajo; batería, L298N y VL53L0X encima.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-95, 95), (-90, 95)))
    placa_redonda(ax)
    for s in (-1, 1):
        ax.add_patch(Rectangle((POZO_X if s > 0 else -L / 2 - 1, -POZO_Y), L / 2 - POZO_X + 1,
                               2 * POZO_Y, fc="white", ec=C["borde"], lw=0.8, zorder=1.5))
    ruedas_planta(ax)
    caja(ax, 0, BAT_Y, BAT[0], BAT[1], C["bat"], "batería 2S 18650\n65 × 37", alpha=0.6, tc="white", z=5)
    caja(ax, 0, L298_Y, L298[0], L298[1], C["l298"], "L298N", alpha=0.6, tc="white", z=5)
    xb, yb = BAT[0] / 2 + 1.2, BAT[1] / 2 + 1.2
    for s in (-1, 1):
        for y in (-1, 1):
            caja(ax, s * xb, BAT_Y + y * (yb - 6), 2, 10, C["imp"], z=6)
        caja(ax, s * 26, BAT_Y - yb, 8, 2, C["imp"], z=6)
        caja(ax, s * 14, BAT_Y + yb, 8, 2, C["imp"], z=6)
    soporte_tof(ax, 0, TOF_FRENTE_Y, "N")
    soporte_tof(ax, TOF_LADO[0], TOF_LADO[1], "E")
    soporte_tof(ax, -TOF_LADO[0], TOF_LADO[1], "O")
    for x, y in POSTES:
        ax.add_patch(Circle((x, y), 4, fc=C["imp"], ec="k", lw=0.6, zorder=6))
        agujero(ax, x, y, d=4)
    for x in (-1, 1):
        for y in (-1, 1):
            ax.add_patch(Circle((x * L298_AG / 2, L298_Y + y * L298_AG / 2), 3.5, fc=C["imp"], ec="k", lw=0.6, zorder=6))
            agujero(ax, x * L298_AG / 2, L298_Y + y * L298_AG / 2, d=4)
    for s in (-1, 1):
        for y in CUNA_Y:
            agujero(ax, s * X_MOT, y)
    for x in (-1, 1):
        agujero(ax, x * PATIN_X, PATIN_Y)
        agujero(ax, x * 17, COLOR_Y)
    for s in (-1, 1):
        caja(ax, s * 27, -25, 10, 10, "white", z=6)
    caja(ax, 0, COLOR_Y - 4.5, 14, 6, "white", z=6)
    frente(ax, -75)
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=16)
    cota(ax, (L / 2, -L / 2), (L / 2, L / 2), f"{L}", off=14, horiz=False)
    cota(ax, (-X_RUEDA_INT, -POZO_Y), (X_RUEDA_INT, -POZO_Y), f"{2 * X_RUEDA_INT:.0f} entre ruedas", off=-55)
    cota(ax, (-L / 2, 0), (-L / 2, TOF_LADO[1]), f"{TOF_LADO[1]}", off=-26, horiz=False)
    ax.plot([-L / 2 - 26, L / 2], [0, 0], color="#777", lw=0.5, ls="-.")
    ax.text(L / 2 + 22, 0, "eje", fontsize=7, va="center")
    texto(fig, (
        "Impreso con la placa\n"
        "• 3 soportes de VL53L0X: 2 postes y un canal con\n"
        "  ranura de 2.0 mm; el sensor baja desde arriba con\n"
        "  el chip hacia afuera. Header recto arriba, con el\n"
        "  plástico y los dupont hacia adentro (negro). La\n"
        f"  zona punteada ({TOF_PASILLO:.0f} mm desde el sensor) es\n"
        "  para doblar el cable: no poner nada ahí.\n"
        f"• Batería sobre el eje (Y = {BAT_Y}); 6 topes de 8 mm.\n"
        f"• 4 columnas Ø8 × {SEP} y 4 postes Ø7 × 5 del L298N,\n"
        "  con inserto M3 arriba (Ø4.0).\n\n"
        "Agujeros M3 pasantes Ø3.4 (Allen desde arriba)\n"
        f"• 4 de las cunas de motor (Y = {CUNA_Y[0]} y {CUNA_Y[1]}),\n"
        "  fuera de la batería.\n"
        f"• 2 del patín (X = ±{PATIN_X}) y 2 de la capucha.\n"
        "• Ranuras 10 × 10 para cables de motores y 14 × 6\n"
        "  para los del TCS34725 (suben por la capucha).\n\n"
        "Debajo\n"
        f"• Eje a {EJE_Z:.0f} mm del suelo.\n"
        f"• Capucha de color {COLOR_Y} mm delante del eje, con\n"
        "  el patín delantero integrado.\n"
        f"• Patín trasero a {PATIN_Y} mm. Ambos dejan 0.5 mm."
    ))
    pp.savefig(fig)
    plt.close(fig)


def planta_piso2(pp):
    fig = pagina("Piso 2 · planta", f"Placa de {ESP} mm a {Z2:.0f} mm del suelo. Nano, bus I2C, OLED, botón e interruptor.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-100, 100), (-90, 100)))
    placa_redonda(ax)
    for x, y in POSTES:
        agujero(ax, x, y)
    xp = PROTO[0] / 2 + 1.1
    caja(ax, 0, PROTO_Y, 2 * PROTO[0] + 5.2, PROTO[1] + 3.8, C["imp"], z=3)
    caja(ax, -xp, PROTO_Y, PROTO[0], PROTO[1], "#f4f4f4", z=4)
    caja(ax, xp, PROTO_Y, PROTO[0], PROTO[1], "#f4f4f4", "bus I2C\n5V · GND\nSDA · SCL", z=4)
    caja(ax, -xp, PROTO_Y + 1, NANO[0], NANO[1], C["placa"], "Arduino\nNano", tc="white", z=5)
    caja(ax, -xp, PROTO_Y - NANO[1] / 2 - 1, 9, 6, "#999", "USB-C", fs=6, z=6)
    caja(ax, 0, OLED_Y, OLED[0] + 3.8, OLED[1] + 3.8, C["imp"], z=3)
    caja(ax, 0, OLED_Y, OLED[0], OLED[1], "#223", "OLED", tc="white", z=4)
    caja(ax, 0, OLED_PINES_Y, 13, 4.5, "white", "pines", fs=5.5, z=5)
    caja(ax, 0, -3, 60, 6, "white", z=6)
    for s in (-1, 1):
        caja(ax, s * RAN2_X, TOF_LADO[1], 16, 22, "white", z=6)
    ax.add_patch(Circle(BOTON_XY, 5, fc="#333", ec="k", zorder=5))
    ax.text(BOTON_XY[0], BOTON_XY[1] + 8, "botón Ø7", ha="center", fontsize=7)
    ax.add_patch(Circle(SWITCH_XY, 3.2, fc="#777", ec="k", zorder=5))
    ax.text(SWITCH_XY[0], SWITCH_XY[1] + 8, "interruptor Ø6", ha="center", fontsize=7)
    frente(ax)
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=12)
    cota(ax, (-xp - PROTO[0] / 2, PROTO_Y - PROTO[1] / 2), (xp + PROTO[0] / 2, PROTO_Y - PROTO[1] / 2),
         f"{2 * PROTO[0] + 2.2:.0f}", off=-14)
    texto(fig, (
        "Impreso con la placa\n"
        "• Marco para 2 mini protoboards de 170 puntos\n"
        "  (35 × 47, holgura 0.3 por lado, 4 mm de alto).\n"
        "  Se pegan con su adhesivo dentro del marco.\n"
        "• Marco del OLED (holgura 0.3): se acuesta con la\n"
        "  pantalla arriba y los pines hacia abajo por la\n"
        "  ranura; los dupont se conectan por debajo.\n\n"
        "Protoboard izquierda: Arduino Nano, USB-C hacia\n"
        "atrás (se programa sin desarmar).\n"
        "Protoboard derecha: bus I2C. Columnas con puente\n"
        "entre mitades: 1 → 5V   4 → GND   7 → SDA   10 → SCL\n\n"
        "OLED al frente con los pines hacia atrás: sus dupont\n"
        "cuelgan entre la batería y el conector del VL53L0X\n"
        "frontal. El código gira la imagen 180° para leerla\n"
        "desde atrás.\n\n"
        "Ranuras: 60 × 6 central (L298N); 16 × 22 a cada\n"
        "lado para los cables de los sensores: izquierda\n"
        "VL53L0X izq. y TCS34725; derecha VL53L0X der.,\n"
        "VL53L0X frontal y OLED.\n"
        "Botón de panel Ø7 e interruptor MTS-102 Ø6."
    ))
    pp.savefig(fig)
    plt.close(fig)


def oled_pines(ax, c, ancho):
    """Header del OLED dentro de la ranura del piso 2, pines y dupont hacia abajo."""
    z0 = Z2 + ESP
    caja(ax, c, z0 - HEADER / 2, ancho, HEADER, "#666", z=6)
    n = 1 if ancho < 5 else 4
    for k in range(n):
        x = c + (k - (n - 1) / 2) * 2.54
        ax.plot([x, x], [z0 + 1.6, z0 - HEADER - 6], color="#c9a227", lw=0.8, zorder=7)
    caja(ax, c, z0 - HEADER - DUPONT / 2, ancho, DUPONT, "#111", z=6)
    ax.plot([c, c], [z0 - HEADER - DUPONT, z0 - HEADER - DUPONT - 5], color=C["proto"], lw=1.2, zorder=6)
    ax.annotate("pines OLED", (c, z0 - HEADER - DUPONT / 2), (c + 22, z0 - 22), fontsize=6.5,
                arrowprops=dict(arrowstyle="-", lw=0.6), zorder=8)


def alzados(pp):
    fig = pagina("Alzados", "Vista lateral (izquierda) y frontal (derecha)")
    ax = ejes(fig, [0.02, 0.06, 0.52, 0.84], ((-110, 140), (-15, 130)))
    ax.plot([-110, 140], [0, 0], color="k", lw=1)
    for z in (Z1, Z2):
        caja(ax, 0, z + ESP / 2, L, ESP, C["piso"])
    for y in (50, -46):
        caja(ax, y, Z1 + ESP + SEP / 2, 8, SEP, C["imp"])
    ax.add_patch(Circle((0, EJE_Z), D_RUEDA / 2, fc=C["rueda"], ec="k", zorder=3))
    caja(ax, 0, EJE_Z, MOT_A, MOT_H, C["motor"], z=4)
    caja(ax, BAT_Y, Z1 + ESP + BAT[2] / 2, BAT[1], BAT[2], C["bat"], "batería", tc="white", fs=6)
    caja(ax, L298_Y, Z1 + ESP + 5 + L298[2] / 2, L298[1], L298[2], C["l298"], "L298N", tc="white", fs=6)
    caja(ax, COLOR_Y, (Z1 + 2) / 2, 25, Z1 - 2, C["imp"], alpha=0.6)
    caja(ax, COLOR_Y, COLOR_Z + 0.8, COLOR_MOD, 1.6, C["color"], z=4)
    for y in (COLOR_Y + 14.45, PATIN_Y):
        caja(ax, y, (Z1 + 5.5) / 2, 10, Z1 - 5.5, C["imp"])
        ax.add_patch(Circle((y, 5.5), 5, fc=C["imp"], ec=C["borde"], zorder=2))
    caja(ax, TOF_FRENTE_Y + 0.5, Z1 + ESP + TOF[1] / 2, 1.6, TOF[1], C["tof"], z=4)
    caja(ax, TOF_FRENTE_Y - 0.3 - HEADER / 2, TOF_PIN_Z, HEADER, 2.5, "#666", z=4)
    caja(ax, TOF_FRENTE_Y - 0.3 - HEADER - DUPONT / 2, TOF_PIN_Z, DUPONT, 2.5, "#111", z=4)
    ax.plot([TOF_FRENTE_Y - TOF_ATRAS, TOF_FRENTE_Y - TOF_ATRAS - 1, TOF_FRENTE_Y - TOF_ATRAS - 4, TOF_FRENTE_Y - TOF_ATRAS - 4],
            [TOF_PIN_Z, TOF_PIN_Z, TOF_PIN_Z + 3, 50], color=C["proto"], lw=1.2, zorder=4)
    caja(ax, PROTO_Y, Z2 + ESP + PROTO[2] / 2, PROTO[1], PROTO[2], "#f4f4f4", "proto", fs=6)
    caja(ax, PROTO_Y + 1, Z2 + ESP + PROTO[2] + 4, NANO[1], 3, C["placa"], z=4)
    caja(ax, OLED_Y, Z2 + ESP + 1.5, OLED[1], 3, "#223")
    oled_pines(ax, OLED_PINES_Y, 2.5)
    caja(ax, PASILLO / 2 + 6, 50, 12, 100, C["pared"], alpha=0.35)
    ax.text(PASILLO / 2 + 6, 104, "pared", ha="center", fontsize=6)
    for z, off in ((Z1, -12), (Z2, -24), (ALTO, -36)):
        cota(ax, (-L / 2, 0), (-L / 2, z), f"{z:.0f}", off=off, horiz=False)
    cota(ax, (-L / 2, 0), (L / 2, 0), f"{L}", off=-10)
    ax.text(100, 120, "FRENTE →", fontsize=9, weight="bold")

    ax2 = ejes(fig, [0.55, 0.06, 0.43, 0.84], ((-100, 100), (-15, 130)))
    ax2.plot([-100, 100], [0, 0], color="k", lw=1)
    caja(ax2, 0, Z1 + ESP / 2, 2 * POZO_X, ESP, C["piso"])
    caja(ax2, 0, Z2 + ESP / 2, L, ESP, C["piso"])
    for s in (-1, 1):
        caja(ax2, s * (X_RUEDA_INT + A_RUEDA / 2), EJE_Z, A_RUEDA, D_RUEDA, C["rueda"], z=3)
        caja(ax2, s * X_MOT, EJE_Z, MOT_L, MOT_H, C["motor"], z=3)
        caja(ax2, s * 42, Z1 + ESP + SEP / 2, 8, SEP, C["imp"])
        caja(ax2, s * (TOF_LADO[0] + 0.5), Z1 + ESP + TOF[1] / 2, 1.6, TOF[1], C["tof"], z=4)
        caja(ax2, s * (TOF_LADO[0] - 0.3 - HEADER / 2), TOF_PIN_Z, HEADER, 2.5, "#666", z=4)
        caja(ax2, s * (TOF_LADO[0] - 0.3 - HEADER - DUPONT / 2), TOF_PIN_Z, DUPONT, 2.5, "#111", z=4)
        xv = s * (TOF_LADO[0] - TOF_ATRAS - 4)
        ax2.plot([s * (TOF_LADO[0] - TOF_ATRAS), xv + s * 3, xv, xv], [TOF_PIN_Z, TOF_PIN_Z, TOF_PIN_Z + 3, Z2 + ESP + 4],
                 color=C["proto"], lw=1.2, zorder=4)
        caja(ax2, s * (PASILLO / 2 + 6), 50, 12, 100, C["pared"], alpha=0.35)
        caja(ax2, s * (PROTO[0] / 2 + 1.1), Z2 + ESP + PROTO[2] / 2, PROTO[0], PROTO[2], "#f4f4f4", z=4)
    caja(ax2, 0, Z1 + ESP + BAT[2] / 2, BAT[0], BAT[2], C["bat"], z=3)
    caja(ax2, 0, Z2 + ESP + 1.5, OLED[0], 3, "#223", z=5)
    oled_pines(ax2, 0, 4 * 2.54)
    caja(ax2, 0, COLOR_Z + 0.8, COLOR_MOD, 1.6, C["color"], z=4)
    cota(ax2, (-L / 2, 0), (L / 2, 0), f"{L} (máximo)", off=-10)
    cota(ax2, (-PASILLO / 2, 100), (PASILLO / 2, 100), f"pasillo {PASILLO}", off=12)
    ax2.text(0, ALTO + 6, f"VL53L0X (verde) a ≈{Z1 + ESP + TOF[1] / 2:.0f} mm del suelo; dupont (negro) hacia adentro", ha="center", fontsize=7, color=C["tof"])
    pp.savefig(fig)
    plt.close(fig)


def en_laberinto(pp):
    fig = pagina("El robot dentro del laberinto", "Celda de 180 mm: holguras, lecturas esperadas y radio de giro")
    ax = ejes(fig, [0.02, 0.05, 0.55, 0.86], ((-130, 130), (-120, 130)))
    m, gr = PASILLO / 2, 6
    for x0, y0, x1, y1 in ((-m - gr, -m - gr, -m, m), (m, -m - gr, m + gr, m), (-m - gr, -m - gr, m + gr, -m),
                           (-m - gr, m, m + gr, m + gr)):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=C["pared"], ec="none", alpha=0.7))
    placa_redonda(ax, z=2)
    ruedas_planta(ax)
    ax.add_patch(Circle((0, 0), GIRO, fc="none", ec="#e67e22", lw=1.2, ls="--", zorder=6))
    ax.text(GIRO * 0.7, -GIRO * 0.75 - 6, f"giro R{GIRO:.0f}", color="#e67e22", fontsize=8)
    xl = TOF_LADO[0] + TOF_CARA
    for s in (-1, 1):
        ax.annotate("", (s * m, TOF_LADO[1]), (s * xl, TOF_LADO[1]), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
        ax.text(s * (m + 12), TOF_LADO[1] + 6, f"{D_LADO:.0f}", ha="center", color=C["tof"], fontsize=9, weight="bold")
    ax.annotate("", (0, m), (0, TOF_FRENTE_Y + TOF_CARA), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.text(4, m + 10, f"{D_FRENTE:.0f}", color=C["tof"], fontsize=9, weight="bold")
    cota(ax, (-m, -m), (m, -m), f"{PASILLO}", off=-16)
    texto(fig, (
        "Valores iniciales del código (config.h)\n"
        f"• D_LADO ≈ {D_LADO:.0f} mm: lectura lateral centrado.\n"
        f"• D_FRENTE ≈ {D_FRENTE:.0f} mm: lectura frontal al llegar al\n"
        "  centro de una celda con pared enfrente.\n"
        "• PARED = 120 mm: menos que eso es pared.\n"
        "  (Miden hasta el centro de la pared; con su\n"
        "  grosor real salen menores.)\n\n"
        "Holguras\n"
        f"• {m - L / 2:.0f} mm por lado con el robot centrado.\n"
        f"• Radio de giro {GIRO:.0f} mm contra {m:.0f} mm: sobran\n"
        f"  {m - GIRO:.0f} mm al girar en su lugar.\n\n"
        "Los valores reales se miden con el modo\n"
        "calibración (ver manual de uso)."
    ))
    pp.savefig(fig)
    plt.close(fig)


def pdf():
    salida = os.path.join(AQUI, "chasis.pdf")
    with PdfPages(salida) as pp:
        portada(pp)
        planta_piso1(pp)
        planta_piso2(pp)
        alzados(pp)
        en_laberinto(pp)
    print("Generado", salida)


if __name__ == "__main__":
    pdf()
