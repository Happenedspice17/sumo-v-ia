"""Genera chasis.pdf: planos acotados del chasis (Arduino UNO R3 / ATmega328P).

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
L, R_ESQ, ESP = 125, 30, 3
D_RUEDA, A_RUEDA = 34, 20
MOT_L, MOT_A, MOT_H = 24, 12, 10
EJE_Z = D_RUEDA / 2
X_RUEDA_INT = L / 2 - A_RUEDA
X_MOT = X_RUEDA_INT - 1.5 - MOT_L / 2
Z1 = EJE_Z + MOT_H / 2
SEP, SEP3 = 35, 25
Z2 = Z1 + ESP + SEP
Z3 = Z2 + ESP + SEP3
POZO_Y = D_RUEDA / 2 + 4
POSTES = [(48, 28), (-48, 28), (35, -52), (-35, -52)]
P3, P3_Y, R3 = (110, 104), -8, 15
BAT, BAT_Y = (37, 65, 19), 28
L298, L298_Y, L298_AG = (43, 43, 27), -36, 37
COLOR_Y, COLOR_MOD, COLOR_Z = 34, 20.5, 5
PATIN_Y = 52
PLACA, PLACA_Y = (53.4, 68.6), -10
AG_UNO = [(2.5, 14.0), (50.7, 15.3), (7.6, 66.1), (35.5, 66.1)]
TOF_FRENTE_Y, TOF_LADO_X = 35, 40
OLED, OLED_XY, BOTON_XY, SWITCH_XY = 27, (28, 29), (-30, 30), (36, -42)
PROTO, PROTO_XY = (35, 47, 9), (0, -25)
RANURA_X = 25
PASILLO = 180

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
    fig.text(0.96, 0.025, "Robot laberinto · Arduino UNO R3 · cotas en mm", fontsize=7, color="#888", ha="right")
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
def portada(pp):
    fig = pagina("Chasis robot de laberinto", "Arduino UNO R3 (ATmega328P) · base de 125 × 125 mm · 3 pisos impresos")
    p = os.path.join(AQUI, "img", "iso.png")
    ax = fig.add_axes([0.0, 0.08, 0.55, 0.8])
    ax.imshow(plt.imread(p)[120:1000, 250:1150])
    ax.axis("off")
    giro = math.sqrt(2) * (L / 2 - R_ESQ) + R_ESQ
    texto(fig, (
        "Cumple los lineamientos\n"
        f"• Huella {L} × {L} mm con ruedas (máximo 125 × 125).\n"
        "• Solo ruedas; sin conexión externa.\n"
        "• Sensor de color I2C, OLED y botón de arranque.\n\n"
        "Pisos\n"
        f"• Piso 1 (a {Z1:.0f} mm): motores, ruedas, patines,\n"
        "  sensor de color, batería y L298N.\n"
        f"• Piso 2 (a {Z2:.0f} mm): Arduino y 3 VL53L0X.\n"
        f"• Piso 3 (a {Z3:.0f} mm): protoboard, OLED, botón\n"
        "  e interruptor.\n"
        f"• Altura total ≈ {Z3 + ESP + PROTO[2] + 10:.0f} mm.\n\n"
        "Giro\n"
        f"• Esquinas R{R_ESQ}: radio de giro {giro:.0f} mm contra\n"
        f"  {PASILLO / 2:.0f} mm de medio pasillo. Gira en su lugar.\n\n"
        "Supuestos que hay que medir\n"
        f"• Rueda Ø{D_RUEDA} × {A_RUEDA} mm.\n"
        f"• Agujeros del L298N a {L298_AG} mm.\n"
        f"• TCS34725 de {COLOR_MOD} mm.\n"
        "• Si algo cambia, se edita en chasis.scad."
    ))
    pp.savefig(fig)
    plt.close(fig)


def planta_piso1(pp):
    fig = pagina("Piso 1 · planta", f"Placa de {ESP} mm a {Z1:.0f} mm del suelo. Motores debajo; batería y L298N encima.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-95, 95), (-90, 95)))
    placa_redonda(ax)
    for s in (-1, 1):
        ax.add_patch(Rectangle((X_RUEDA_INT - 2 if s > 0 else -L / 2 - 1, -POZO_Y), L / 2 - X_RUEDA_INT + 3,
                               2 * POZO_Y, fc="white", ec=C["borde"], lw=0.8, zorder=1.5))
    ruedas_planta(ax)
    caja(ax, 0, BAT_Y, BAT[0], BAT[1], C["bat"], "batería 2S\n18650\n37×65", alpha=0.6, tc="white", z=5)
    caja(ax, 0, L298_Y, L298[0], L298[1], C["l298"], "L298N", alpha=0.6, tc="white", z=5)
    for x, y in POSTES:
        agujero(ax, x, y)
    for s in (-1, 1):
        for y in (-1, 1):
            agujero(ax, s * X_MOT, y * (MOT_A / 2 + 3))
        caja(ax, s * 22.5, BAT_Y, 3, 22, "white", z=6)
    for x in (-1, 1):
        for y in (-1, 1):
            agujero(ax, x * L298_AG / 2, L298_Y + y * L298_AG / 2)
    for y in (PATIN_Y, -PATIN_Y):
        agujero(ax, 0, y)
    for x in (-1, 1):
        agujero(ax, x * 17, COLOR_Y)
    caja(ax, 0, COLOR_Y, 16, 16, "white", z=6)
    caja(ax, 0, 0, 24, 10, "white", z=6)
    frente(ax, -75)
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=14)
    cota(ax, (L / 2, -L / 2), (L / 2, L / 2), f"{L}", off=12, horiz=False)
    cota(ax, (-X_RUEDA_INT, -POZO_Y), (X_RUEDA_INT, -POZO_Y), f"{2 * X_RUEDA_INT:.0f} entre ruedas", off=-55)
    cota(ax, (-L / 2, 0), (-L / 2, COLOR_Y), f"{COLOR_Y}", off=-24, horiz=False)
    ax.plot([-L / 2 - 26, L / 2], [0, 0], color="#777", lw=0.5, ls="-.")
    ax.text(L / 2 + 22, 0, "eje", fontsize=7, va="center")
    texto(fig, (
        "Agujeros (todos M3 pasantes Ø3.4)\n"
        "• 4 separadores de piso (±48, 28) y (±35, −52).\n"
        "• 4 de las cunas de motor.\n"
        f"• 4 del L298N (cuadro de {L298_AG} mm).\n"
        "• 2 de patines y 2 de la capucha de color:\n"
        "  avellanados, porque quedan bajo la batería.\n\n"
        "Ranuras\n"
        "• 2 para el cincho de velcro de la batería.\n"
        "• Ventana de 16 × 16 para los cables del sensor\n"
        "  de color.\n"
        "• Paso central de 24 × 10 para cables.\n\n"
        "Debajo\n"
        f"• Eje a {EJE_Z:.0f} mm del suelo; cara del sensor de\n"
        f"  color a {COLOR_Z} mm, {COLOR_Y} mm delante del eje.\n"
        "• Patines delante y detrás: dejan 0.5 mm al suelo."
    ))
    pp.savefig(fig)
    plt.close(fig)


def planta_piso2(pp):
    fig = pagina("Piso 2 · planta", f"Placa de {ESP} mm a {Z2:.0f} mm del suelo. Arduino UNO R3 y sensores VL53L0X.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-100, 100), (-90, 100)))
    placa_redonda(ax)
    for x, y in POSTES:
        agujero(ax, x, y)
    caja(ax, 0, PLACA_Y, PLACA[0], PLACA[1], C["placa"], "Arduino UNO R3\n53.4 × 68.6", tc="white", alpha=0.85)
    for hx, hy in AG_UNO:
        agujero(ax, PLACA[0] / 2 - hx, PLACA_Y - PLACA[1] / 2 + hy)
    caja(ax, 0, PLACA_Y - PLACA[1] / 2 - 4, 12, 8, "#999", "USB", fs=6, z=5)
    caja(ax, 0, -53, 24, 8, "white", z=6)
    caja(ax, 0, TOF_FRENTE_Y - 1.5, 30, 3, C["imp"], z=4)
    caja(ax, 0, TOF_FRENTE_Y + 0.8, 25, 1.6, C["tof"], z=5)
    agujero(ax, 0, TOF_FRENTE_Y - 7.5)
    for s in (-1, 1):
        caja(ax, s * (TOF_LADO_X - 1.5), 0, 3, 30, C["imp"], z=4)
        caja(ax, s * (TOF_LADO_X + 0.8), 0, 1.6, 25, C["tof"], z=5)
        agujero(ax, s * (TOF_LADO_X - 7.5), 0)
        ax.annotate("", (s * (TOF_LADO_X + 30), 0), (s * TOF_LADO_X, 0),
                    arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.annotate("", (0, TOF_FRENTE_Y + 30), (0, TOF_FRENTE_Y), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.text(-24, PLACA_Y, "D0–D13", rotation=90, fontsize=6.5, color="white", va="center", zorder=6)
    ax.text(24, PLACA_Y, "A0–A5 / 5V", rotation=90, fontsize=6.5, color="white", va="center", zorder=6)
    frente(ax)
    cota(ax, (0, 0), (TOF_LADO_X, 0), f"{TOF_LADO_X}", off=-50)
    cota(ax, (0, 0), (0, TOF_FRENTE_Y), f"{TOF_FRENTE_Y}", off=-52, horiz=False)
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=12)
    ax.plot([-L / 2, L / 2], [0, 0], color="#777", lw=0.5, ls="-.")
    texto(fig, (
        "Arduino UNO R3\n"
        "• USB hacia atrás: se programa sin desarmar.\n"
        "• Pines digitales a la izquierda; A0–A5 y 5V a la\n"
        "  derecha (vistos desde arriba, frente adelante).\n"
        "• 4 espaciadores impresos de 5 mm + M3 × 12.\n\n"
        "VL53L0X (3 escuadras impresas)\n"
        f"• Laterales a ±{TOF_LADO_X} mm, sobre el eje.\n"
        f"• Frontal a {TOF_FRENTE_Y} mm delante del eje.\n"
        "• Metidos hacia dentro para nunca leer a menos de\n"
        "  4 cm de una pared.\n"
        "• Cada escuadra: 1 M3 × 8 + tuerca al piso y\n"
        "  2 M2 × 6 al sensor.\n\n"
        "Ranura trasera 24 × 8: cables que suben del piso 1."
    ))
    pp.savefig(fig)
    plt.close(fig)


def planta_piso3(pp):
    fig = pagina("Piso 3 · planta", f"Placa de {ESP} mm a {Z3:.0f} mm del suelo. Protoboard, OLED, botón e interruptor.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-100, 100), (-90, 100)))
    placa_redonda(ax, col="none")
    ax.add_patch(FancyBboxPatch((-P3[0] / 2 + R3, P3_Y - P3[1] / 2 + R3), P3[0] - 2 * R3, P3[1] - 2 * R3,
                                boxstyle=f"round,pad={R3}", fc=C["piso"], ec=C["borde"], lw=1.2, zorder=2))
    caja(ax, 0, PLACA_Y, PLACA[0], PLACA[1], "none", ls=":", z=3)
    for x, y in POSTES:
        agujero(ax, x, y)
    for s in (-1, 1):
        caja(ax, s * RANURA_X, -12, 8, 52, "white", z=4)
    caja(ax, *PROTO_XY, PROTO[0], PROTO[1], C["proto"], "mini\nprotoboard\n170 pts", tc="white", z=5)
    caja(ax, *OLED_XY, OLED, OLED, C["oled"], "OLED", z=5)
    ax.add_patch(Circle(BOTON_XY, 5, fc="#333", ec="k", zorder=5))
    ax.text(BOTON_XY[0], BOTON_XY[1] + 8, "botón Ø7", ha="center", fontsize=7)
    ax.add_patch(Circle(SWITCH_XY, 3.2, fc="#777", ec="k", zorder=5))
    ax.text(SWITCH_XY[0] + 6, SWITCH_XY[1] - 8, "interruptor Ø6", ha="center", fontsize=7)
    ax.text(-RANURA_X, -42, "ranura", ha="center", fontsize=6.5)
    frente(ax)
    cota(ax, (-P3[0] / 2, P3_Y + P3[1] / 2), (P3[0] / 2, P3_Y + P3[1] / 2), f"{P3[0]}", off=10)
    cota(ax, (P3[0] / 2, P3_Y - P3[1] / 2), (P3[0] / 2, P3_Y + P3[1] / 2), f"{P3[1]}", off=12, horiz=False)
    texto(fig, (
        "Mini protoboard (170 puntos, sin rieles)\n"
        "• Pegada con su adhesivo, girada (35 × 47).\n"
        "• Columnas con puente entre mitades:\n"
        "    1 → 5V   4 → GND   7 → SDA   10 → SCL\n\n"
        "OLED: cinta doble cara de espuma.\n"
        "Botón: de panel, Ø7 mm, con tuerca.\n"
        "Interruptor: de palanca MTS-102, Ø6 mm.\n\n"
        "Ranuras sobre los headers del Arduino\n"
        "• Los cables entran derecho a los pines sin\n"
        "  chocar con el piso 3.\n"
        f"• Separadores M3 × {SEP3} (macho-hembra) sobre\n"
        "  los del piso 1-2."
    ))
    pp.savefig(fig)
    plt.close(fig)


def alzados(pp):
    fig = pagina("Alzados", "Vista lateral (izquierda) y frontal (derecha)")
    ax = ejes(fig, [0.02, 0.06, 0.52, 0.84], ((-110, 140), (-15, 140)))
    ax.plot([-110, 140], [0, 0], color="k", lw=1)
    for z, ln, cy in ((Z1, L, 0), (Z2, L, 0), (Z3, P3[1], P3_Y)):
        caja(ax, cy, z + ESP / 2, ln, ESP, C["piso"])
    for y in (28, -52):
        caja(ax, y, Z1 + ESP + SEP / 2, 5, SEP, "#aaa")
        caja(ax, y, Z2 + ESP + SEP3 / 2, 5, SEP3, "#aaa")
    ax.add_patch(Circle((0, EJE_Z), D_RUEDA / 2, fc=C["rueda"], ec="k", zorder=3))
    caja(ax, 0, EJE_Z, MOT_A, MOT_H, C["motor"], z=4)
    caja(ax, BAT_Y, Z1 + ESP + BAT[2] / 2, BAT[1], BAT[2], C["bat"], "batería", tc="white", fs=6)
    caja(ax, L298_Y, Z1 + ESP + 5 + L298[2] / 2, L298[1], L298[2], C["l298"], "L298N", tc="white", fs=6)
    caja(ax, COLOR_Y, (Z1 + 2) / 2, 25, Z1 - 2, C["imp"], alpha=0.6)
    caja(ax, COLOR_Y, COLOR_Z + 0.8, COLOR_MOD, 1.6, C["color"], z=4)
    for y in (PATIN_Y, -PATIN_Y):
        caja(ax, y, (Z1 + 5.5) / 2, 10, Z1 - 5.5, C["imp"])
        ax.add_patch(Circle((y, 5.5), 5, fc=C["imp"], ec=C["borde"], zorder=2))
    caja(ax, PLACA_Y, Z2 + ESP + 5 + 7, PLACA[1], 14, C["placa"], "Arduino", tc="white", fs=7)
    caja(ax, TOF_FRENTE_Y + 0.8, Z2 + ESP + 12, 1.6, 11, C["tof"], z=4)
    caja(ax, PROTO_XY[1], Z3 + ESP + PROTO[2] / 2, PROTO[1], PROTO[2], C["proto"], "proto", tc="white", fs=6)
    caja(ax, OLED_XY[1], Z3 + ESP + 2, OLED, 4, C["oled"])
    caja(ax, PASILLO / 2 + 6, 50, 12, 100, C["pared"], alpha=0.35)
    ax.text(PASILLO / 2 + 6, 104, "pared", ha="center", fontsize=6)
    for z, off in ((Z1, -12), (Z2, -24), (Z3, -36)):
        cota(ax, (-L / 2, 0), (-L / 2, z), f"{z:.0f}", off=off, horiz=False)
    cota(ax, (-L / 2, 0), (L / 2, 0), f"{L}", off=-10)
    ax.text(100, 130, "FRENTE →", fontsize=9, weight="bold")

    ax2 = ejes(fig, [0.55, 0.06, 0.43, 0.84], ((-100, 100), (-15, 140)))
    ax2.plot([-100, 100], [0, 0], color="k", lw=1)
    caja(ax2, 0, Z1 + ESP / 2, 2 * X_RUEDA_INT - 4, ESP, C["piso"])
    caja(ax2, 0, Z2 + ESP / 2, L, ESP, C["piso"])
    caja(ax2, 0, Z3 + ESP / 2, P3[0], ESP, C["piso"])
    for s in (-1, 1):
        caja(ax2, s * (X_RUEDA_INT + A_RUEDA / 2), EJE_Z, A_RUEDA, D_RUEDA, C["rueda"], z=3)
        caja(ax2, s * X_MOT, EJE_Z, MOT_L, MOT_H, C["motor"], z=3)
        caja(ax2, s * 48, Z1 + ESP + SEP / 2, 5, SEP, "#aaa")
        caja(ax2, s * 48, Z2 + ESP + SEP3 / 2, 5, SEP3, "#aaa")
        caja(ax2, s * (TOF_LADO_X + 0.8), Z2 + ESP + 12, 1.6, 11, C["tof"], z=4)
        caja(ax2, s * (PASILLO / 2 + 6), 50, 12, 100, C["pared"], alpha=0.35)
    caja(ax2, 0, Z1 + ESP + BAT[2] / 2, BAT[0], BAT[2], C["bat"], z=3)
    caja(ax2, 0, Z2 + ESP + 5 + 7, PLACA[0], 14, C["placa"], "Arduino", tc="white", fs=7)
    caja(ax2, 0, Z3 + ESP + PROTO[2] / 2, PROTO[0], PROTO[2], C["proto"], z=4)
    caja(ax2, 0, COLOR_Z + 0.8, COLOR_MOD, 1.6, C["color"], z=4)
    cota(ax2, (-L / 2, 0), (L / 2, 0), f"{L} (máximo)", off=-10)
    cota(ax2, (-PASILLO / 2, 100), (PASILLO / 2, 100), f"pasillo {PASILLO}", off=12)
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
    giro = math.sqrt(2) * (L / 2 - R_ESQ) + R_ESQ
    ax.add_patch(Circle((0, 0), giro, fc="none", ec="#e67e22", lw=1.2, ls="--", zorder=6))
    ax.text(giro * 0.7, -giro * 0.75 - 6, f"giro R{giro:.0f}", color="#e67e22", fontsize=8)
    for s in (-1, 1):
        ax.annotate("", (s * m, 0), (s * TOF_LADO_X, 0), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
        ax.text(s * (m + 10), 6, f"{m - TOF_LADO_X:.0f}", ha="center", color=C["tof"], fontsize=9, weight="bold")
    ax.annotate("", (0, m), (0, TOF_FRENTE_Y), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.text(4, (TOF_FRENTE_Y + m) / 2, f"{m - TOF_FRENTE_Y:.0f}", color=C["tof"], fontsize=9, weight="bold")
    cota(ax, (-m, -m), (m, -m), f"{PASILLO}", off=-16)
    texto(fig, (
        "Valores que usa el código\n"
        f"• D_LADO = {m - TOF_LADO_X:.0f} mm: lectura lateral centrado.\n"
        f"• D_FRENTE = {m - TOF_FRENTE_Y:.0f} mm: lectura frontal al llegar al\n"
        "  centro de una celda con pared enfrente.\n"
        "• PARED = 120 mm: menos que eso es pared.\n\n"
        "Holguras\n"
        f"• {m - L / 2:.1f} mm por lado con el robot centrado.\n"
        f"• Radio de giro {giro:.0f} mm contra {m:.0f} mm: sobran\n"
        f"  {m - giro:.0f} mm al girar en su lugar.\n\n"
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
        planta_piso3(pp)
        alzados(pp)
        en_laberinto(pp)
    print("Generado", salida)


if __name__ == "__main__":
    pdf()
