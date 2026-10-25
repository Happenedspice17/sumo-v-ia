"""Genera chasis.pdf con planos acotados de ambas versiones.

Uso: python3 generar_pdf.py   (las vistas 3D salen de img/, renderizadas desde chasis.scad)
"""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle

AQUI = os.path.dirname(os.path.abspath(__file__))

# ---------- Medidas (mismas que chasis.scad) ----------
L, R_ESQ, ESP = 125, 30, 3
D_RUEDA, A_RUEDA = 34, 20
MOT_L, MOT_A, MOT_H = 24, 12, 10
EJE_Z = D_RUEDA / 2
X_RUEDA_INT = L / 2 - A_RUEDA
X_MOT_EXT = X_RUEDA_INT - 1.5
Z1 = EJE_Z + MOT_H / 2
SEP = 32
Z2 = Z1 + ESP + SEP
POZO_Y = D_RUEDA / 2 + 4
POSTES = [(48, 28), (-48, 28), (35, -52), (-35, -52)]
OLED_XY = (29, 46)
BOTON_XY = (-29, 46)
BAT = (37, 65, 19)
BAT_Y = 28
L298 = (43, 43, 27)
L298_Y = -36
COLOR_Y, COLOR_MOD, COLOR_Z = 34, 20, 4
PLACA = (53.4, 68.6)
PLACA_Y = -10
TOF_FRENTE_Y, TOF_LADO_X = 35, 40
OLED = 27
MASTIL_Y, MASTIL_H, CAM_INCL = -54, 120, 40
PASILLO = 180
PATIN_Y = 52

C = {
    "piso": "#c9d6ea", "borde": "#33415c", "rueda": "#222222", "motor": "#d4a017",
    "bat": "#4169e1", "l298": "#d62728", "placa": "#138a8a", "tof": "#2ca02c",
    "color": "#7b2d8b", "oled": "#eeeeee", "imp": "#f39c12", "cota": "#c0392b",
    "pared": "#8d6e63", "texto": "#1b1b1b",
}

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})


def pagina(titulo, sub=""):
    fig = plt.figure(figsize=(11.69, 8.27))
    fig.text(0.04, 0.95, titulo, fontsize=17, weight="bold", color=C["texto"])
    if sub:
        fig.text(0.04, 0.915, sub, fontsize=10, color="#555")
    fig.text(0.96, 0.025, "Robot laberinto · Microcontroladores 2 · cotas en mm",
             fontsize=7, color="#888", ha="right")
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
        ax.text(cx, cy, txt, ha="center", va="center", fontsize=fs,
                color=tc or C["texto"], zorder=z + 1)


def cota(ax, p1, p2, txt, off=8, horiz=True, fs=7):
    """Cota con flechas; off desplaza la linea perpendicularmente."""
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
        ax.text(x + 1.5, (y1 + y2) / 2, txt, ha="left", va="center", fontsize=fs,
                color=C["cota"], rotation=90)


def placa_redonda(ax, col=C["piso"], alpha=1, z=1):
    ax.add_patch(FancyBboxPatch((-L / 2 + R_ESQ, -L / 2 + R_ESQ), L - 2 * R_ESQ, L - 2 * R_ESQ,
                                boxstyle=f"round,pad={R_ESQ}", fc=col, ec=C["borde"],
                                lw=1.2, alpha=alpha, zorder=z))


def ruedas_planta(ax):
    for s in (-1, 1):
        x0 = s * (X_RUEDA_INT + A_RUEDA / 2)
        caja(ax, x0, 0, A_RUEDA, D_RUEDA, C["rueda"], "rueda", fs=6, tc="white", z=4)
        caja(ax, s * (X_MOT_EXT - MOT_L / 2), 0, MOT_L, MOT_A, C["motor"], "N20", fs=6, z=4)


def piso1_planta(ax):
    placa_redonda(ax)
    for s in (-1, 1):  # huecos de rueda
        ax.add_patch(Rectangle((s * (X_RUEDA_INT - 2) if s > 0 else -L / 2 - 1, -POZO_Y),
                               L / 2 - X_RUEDA_INT + 3, 2 * POZO_Y, fc="white", ec=C["borde"],
                               lw=0.8, zorder=1.5))
    for x, y in POSTES:
        ax.add_patch(Circle((x, y), 2.5, fc="#999", ec=C["borde"], zorder=3))


def pdf():
    salida = os.path.join(AQUI, "chasis.pdf")
    with PdfPages(salida) as pp:
        portada(pp)
        vistas_3d(pp)
        planta_piso1(pp)
        planta_piso2(pp)
        alzados(pp)
        en_laberinto(pp)
        conexiones(pp)
        piezas(pp)
    print("Generado", salida)


# ---------- Paginas ----------
def portada(pp):
    fig = pagina("Chasis robot de laberinto", "Dos iteraciones sobre la misma base de 125 × 125 mm")
    filas = [
        ("", "Iteración A · ATmega328P", "Iteración B · Arduino UNO Q"),
        ("Cerebro", "Arduino UNO R3 (ATmega328P)", "Arduino UNO Q (Linux + STM32)"),
        ("Resuelve el laberinto", "Flood-fill en el MCU", "Flood-fill en Python (Linux)"),
        ("Paredes", "3 × VL53L0X", "3 × VL53L0X + cámara (celda siguiente)"),
        ("Marcas de color", "TCS34725 (I2C)", "TCS34725 (I2C)"),
        ("Pantalla", "OLED SSD1306 128×64", "OLED SSD1306 128×64"),
        ("Motores", "2 × N20 sin encoder + L298N", "2 × N20 sin encoder + L298N"),
        ("Memoria del mapa", "EEPROM interna", "Archivo /app/mapa.json"),
        ("Mástil de cámara", "No", "Sí, ajustable 150–200 mm"),
        ("Altura total aprox.", f"{Z2 + ESP + 5 + 15:.0f} mm", f"≈ {Z2 + ESP + MASTIL_H + 25:.0f} mm"),
    ]
    ax = fig.add_axes([0.04, 0.38, 0.92, 0.5])
    ax.axis("off")
    t = ax.table(cellText=[list(r) for r in filas[1:]], colLabels=["", *filas[0][1:]],
                 loc="upper center", cellLoc="left", colWidths=[0.2, 0.36, 0.42])
    t.auto_set_font_size(False)
    t.set_fontsize(10)
    t.scale(1, 1.7)
    for (r, c), cell in t.get_celld().items():
        cell.set_edgecolor("#bbb")
        if r == 0:
            cell.set_facecolor("#33415c")
            cell.get_text().set_color("white")
            cell.get_text().set_weight("bold")
        if c == 0:
            cell.get_text().set_weight("bold")

    giro = math.sqrt(2) * (L / 2 - R_ESQ) + R_ESQ
    notas = [
        f"✔ Huella máxima {L} × {L} mm incluyendo ruedas (lineamiento: ≤ 125 × 125 mm, altura libre).",
        f"✔ Esquinas redondeadas R{R_ESQ}: radio de giro {giro:.0f} mm < {PASILLO / 2:.0f} mm (medio pasillo). Gira en su lugar sin rozar.",
        f"✔ Ruedas de {A_RUEDA} mm de ancho por lado (40 mm en total). Queda {2 * X_RUEDA_INT:.0f} mm de chasis entre ruedas.",
        "✔ Sensor de color I2C, OLED, interruptor de arranque: incluidos (lineamientos de diseño).",
        f"Supuesto: rueda Ø{D_RUEDA} mm (la típica de N20). Si la suya es distinta, cambie D_RUEDA en chasis.scad.",
        "Las dos iteraciones usan las mismas piezas impresas; la B agrega el mástil y la cámara.",
    ]
    for i, n in enumerate(notas):
        fig.text(0.06, 0.31 - i * 0.035, n, fontsize=10, color=C["texto"] if n[0] == "✔" else "#8a4b00")
    pp.savefig(fig)
    plt.close(fig)


def vistas_3d(pp):
    fig = pagina("Vistas 3D", "Renderizadas desde chasis.scad (OpenSCAD)")
    imgs = [("iso_328p.png", "Iteración A · ATmega328P"), ("iso_unoq.png", "Iteración B · UNO Q con mástil"),
            ("abajo.png", "Vista inferior: patines, sensor de color, motores")]
    for i, (f, t) in enumerate(imgs):
        p = os.path.join(AQUI, "img", f)
        if not os.path.exists(p):
            continue
        ax = fig.add_axes([0.01 + i * 0.33, 0.12, 0.32, 0.76])
        ax.imshow(plt.imread(p)[60:1060, 230:1170])
        ax.set_title(t, fontsize=11)
        ax.axis("off")
    leyenda = [("Pisos impresos", C["piso"]), ("Soportes impresos", C["imp"]), ("Placa Arduino", C["placa"]),
               ("VL53L0X", C["tof"]), ("Batería 2S 18650", C["bat"]), ("L298N", C["l298"]), ("OLED", C["oled"])]
    for i, (t, c) in enumerate(leyenda):
        fig.patches.append(Rectangle((0.06 + i * 0.13, 0.07), 0.012, 0.016, fc=c, ec="#555",
                                     transform=fig.transFigure, figure=fig))
        fig.text(0.076 + i * 0.13, 0.072, t, fontsize=8)
    pp.savefig(fig)
    plt.close(fig)


def planta_piso1(pp):
    fig = pagina("Piso 1 · planta (vista superior)",
                 f"Placa de {ESP} mm a {Z1:.0f} mm del suelo. Motores debajo, batería y L298N encima.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-95, 95), (-90, 95)))
    piso1_planta(ax)
    ruedas_planta(ax)
    caja(ax, 0, BAT_Y, BAT[0], BAT[1], C["bat"], "2S 18650\n7.4 V\n37×65", alpha=0.85, tc="white", z=5)
    caja(ax, 0, L298_Y, L298[0], L298[1], C["l298"], "L298N\n43×43", alpha=0.85, tc="white", z=5)
    caja(ax, 0, COLOR_Y, 26, 26, "none", ls="--", z=6)
    ax.text(16, COLOR_Y + 8, "TCS34725\n(debajo)", fontsize=6, color=C["color"])
    for y in (PATIN_Y, -PATIN_Y):
        ax.add_patch(Circle((0, y), 5, fc=C["imp"], ec=C["borde"], ls="--", zorder=6))
    ax.text(7, PATIN_Y + 2, "patín", fontsize=6)
    ax.text(7, -PATIN_Y - 6, "patín", fontsize=6)
    ax.annotate("FRENTE", (-75, 72), (-75, 86), ha="center", fontsize=9, weight="bold",
                arrowprops=dict(arrowstyle="<-", lw=1.2))
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=14)
    cota(ax, (L / 2, -L / 2), (L / 2, L / 2), f"{L}", off=12, horiz=False)
    cota(ax, (-X_RUEDA_INT, -POZO_Y), (X_RUEDA_INT, -POZO_Y), f"{2 * X_RUEDA_INT:.0f} entre ruedas", off=-55)
    cota(ax, (X_RUEDA_INT, -D_RUEDA / 2), (L / 2, -D_RUEDA / 2), f"{A_RUEDA}", off=-20)
    cota(ax, (-L / 2, -POZO_Y), (-L / 2, POZO_Y), f"{2 * POZO_Y:.0f}", off=-14, horiz=False)
    cota(ax, (-L / 2, 0), (-L / 2, COLOR_Y), f"{COLOR_Y}", off=-24, horiz=False)
    ax.plot([-L / 2 - 26, 0], [COLOR_Y, COLOR_Y], color=C["cota"], lw=0.4, ls=":")
    ax.plot([-L / 2 - 26, L / 2], [0, 0], color="#777", lw=0.5, ls="-.")
    ax.text(L / 2 + 22, 0, "eje", fontsize=7, va="center")

    tx = fig.add_axes([0.64, 0.1, 0.34, 0.78])
    tx.axis("off")
    txt = (
        "Debajo del piso 1\n"
        f"• 2 cunas impresas aprietan cada N20 contra el piso (M3).\n"
        f"• Eje a {EJE_Z:.0f} mm del suelo (rueda Ø{D_RUEDA}).\n"
        f"• Capucha del sensor de color a {COLOR_Y} mm delante del eje;\n"
        f"  la cara del sensor queda a {COLOR_Z} mm del suelo y la\n"
        "  capucha tapa la luz ambiente.\n"
        f"• 2 patines (delante y detrás, y = ±{PATIN_Y}) dejan 0.5 mm\n"
        "  al suelo: el robot se apoya en las ruedas.\n\n"
        "Encima del piso 1\n"
        "• Batería 2S 18650 al frente (peso bajo y adelante del eje\n"
        "  para que no cabecee al frenar).\n"
        "• L298N atrás; su disipador mide 27 mm y cabe bajo\n"
        f"  el piso 2 (hueco libre {SEP} mm).\n"
        "• Ventanas al centro para pasar cables.\n"
        "• 4 separadores M3 × 32 mm en (±48, 28) y (±35, −52).\n\n"
        "Por qué así\n"
        "• Eje al centro: gira sobre su propio lugar, lo que\n"
        "  simplifica los giros de 90° por tiempo.\n"
        "• OFF_COLOR del código = 34 / 180 ≈ 0.2 celdas."
    )
    tx.text(0, 1, txt, va="top", fontsize=9.5, linespacing=1.45)
    pp.savefig(fig)
    plt.close(fig)


def planta_piso2(pp):
    fig = pagina("Piso 2 · planta (vista superior)",
                 f"Placa de {ESP} mm a {Z2:.0f} mm del suelo. Arduino, sensores de distancia, OLED, botón y mástil.")
    ax = ejes(fig, [0.03, 0.06, 0.6, 0.84], ((-100, 100), (-90, 100)))
    placa_redonda(ax)
    for s in (-1, 1):
        caja(ax, s * (X_RUEDA_INT + A_RUEDA / 2), 0, A_RUEDA, D_RUEDA, "none", ls=":", z=2)
    for x, y in POSTES:
        ax.add_patch(Circle((x, y), 2.5, fc="#999", ec=C["borde"], zorder=3))
    caja(ax, 0, PLACA_Y, PLACA[0], PLACA[1], C["placa"], "UNO R3 / UNO Q\n53.4 × 68.6", tc="white", alpha=0.9)
    for hx, hy in ((2.5, 14.0), (50.7, 15.3), (7.6, 66.1), (35.5, 66.1)):
        ax.add_patch(Circle((-PLACA[0] / 2 + hx, PLACA_Y - PLACA[1] / 2 + hy), 1.6, fc="white", ec="k", zorder=4))
    # VL53L0X
    caja(ax, 0, TOF_FRENTE_Y - 1.5, 30, 3, C["imp"], z=4)
    caja(ax, 0, TOF_FRENTE_Y + 0.8, 25, 1.6, C["tof"], z=5)
    ax.text(0, TOF_FRENTE_Y - 8, "VL53L0X frente", ha="center", fontsize=6.5)
    for s in (-1, 1):
        caja(ax, s * (TOF_LADO_X - 1.5), 0, 3, 30, C["imp"], z=4)
        caja(ax, s * (TOF_LADO_X + 0.8), 0, 1.6, 25, C["tof"], z=5)
        ax.text(s * (TOF_LADO_X - 8), 0, "VL53L0X " + ("der" if s > 0 else "izq"), rotation=90,
                ha="center", va="center", fontsize=6.5)
        ax.annotate("", (s * (TOF_LADO_X + 30), 0), (s * TOF_LADO_X, 0),
                    arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.annotate("", (0, TOF_FRENTE_Y + 30), (0, TOF_FRENTE_Y),
                arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    caja(ax, *OLED_XY, OLED, OLED, C["oled"], "OLED\n0.96\"", z=4)
    ax.add_patch(Circle(BOTON_XY, 6, fc="#333", ec="k", zorder=4))
    ax.text(BOTON_XY[0], BOTON_XY[1] + 9, "botón", ha="center", fontsize=7)
    caja(ax, 0, MASTIL_Y, 22, 13, C["imp"], "mástil (B)", fs=6, ls="--", z=4)
    cota(ax, (0, 0), (TOF_LADO_X, 0), f"{TOF_LADO_X}", off=-50)
    cota(ax, (0, 0), (0, TOF_FRENTE_Y), f"{TOF_FRENTE_Y}", off=-52, horiz=False)
    cota(ax, (-L / 2, L / 2), (L / 2, L / 2), f"{L}", off=12)
    ax.plot([-L / 2, L / 2], [0, 0], color="#777", lw=0.5, ls="-.")
    ax.annotate("FRENTE", (-80, 72), (-80, 86), ha="center", fontsize=9, weight="bold",
                arrowprops=dict(arrowstyle="<-", lw=1.2))

    tx = fig.add_axes([0.64, 0.1, 0.34, 0.78])
    tx.axis("off")
    txt = (
        "Sensores de distancia VL53L0X\n"
        "• Van en el piso 2 porque las ruedas tapan los lados\n"
        "  en el piso 1. Las paredes (≈10 cm) los cubren.\n"
        f"• Laterales a ±{TOF_LADO_X} mm del centro, sobre el eje: leen\n"
        "  la celda donde está el robot.\n"
        f"• Frontal a {TOF_FRENTE_Y} mm delante del eje.\n"
        "• Van metidos hacia dentro a propósito: así nunca\n"
        "  leen a menos de 4 cm, donde el VL53L0X es impreciso.\n\n"
        "Placa\n"
        "• UNO R3 y UNO Q tienen la misma huella y agujeros:\n"
        "  el mismo piso 2 sirve para las dos iteraciones.\n"
        "• Separadores de 5 mm bajo la placa.\n\n"
        "Iteración B\n"
        "• El mástil entra en la ranura trasera (10 × 6 mm).\n"
        "• El hub USB-C de la cámara va en el piso 1, en la\n"
        "  zona central entre la batería y el L298N."
    )
    tx.text(0, 1, txt, va="top", fontsize=9.5, linespacing=1.45)
    pp.savefig(fig)
    plt.close(fig)


def alzados(pp):
    fig = pagina("Alzados", "Vista lateral (izquierda) y frontal (derecha). La cámara solo va en la iteración B.")
    ax = ejes(fig, [0.02, 0.06, 0.52, 0.84], ((-110, 140), (-15, 250)))
    ax.plot([-110, 140], [0, 0], color="k", lw=1)
    ax.text(120, -9, "suelo", fontsize=7)
    caja(ax, 0, Z1 + ESP / 2, L, ESP, C["piso"])
    caja(ax, 0, Z2 + ESP / 2, L, ESP, C["piso"])
    for y in (28, -52):
        caja(ax, y, Z1 + ESP + SEP / 2, 5, SEP, "#aaa")
    ax.add_patch(Circle((0, EJE_Z), D_RUEDA / 2, fc=C["rueda"], ec="k", zorder=3))
    caja(ax, 0, EJE_Z, MOT_A, MOT_H, C["motor"], z=4)
    caja(ax, BAT_Y, Z1 + ESP + BAT[2] / 2, BAT[1], BAT[2], C["bat"], "batería", tc="white", fs=6)
    caja(ax, L298_Y, Z1 + ESP + L298[2] / 2, L298[1], L298[2], C["l298"], "L298N", tc="white", fs=6)
    caja(ax, COLOR_Y, (Z1 + 2) / 2, 26, Z1 - 2, C["imp"], alpha=0.6)
    caja(ax, COLOR_Y, COLOR_Z + 1, COLOR_MOD, 2, C["color"], z=4)
    for y in (PATIN_Y, -PATIN_Y):
        caja(ax, y, (Z1 + 5.5) / 2, 10, Z1 - 5.5, C["imp"])
        ax.add_patch(Circle((y, 5.5), 5, fc=C["imp"], ec=C["borde"], zorder=2))
    caja(ax, PLACA_Y, Z2 + ESP + 5 + 7, PLACA[1], 14, C["placa"], "Arduino", tc="white", fs=7)
    caja(ax, TOF_FRENTE_Y + 0.8, Z2 + ESP + 12, 1.6, 11, C["tof"], z=4)
    caja(ax, 0, Z2 + ESP + 12, 11, 11, C["tof"], z=4)
    # mastil y camara
    zc = Z2 + MASTIL_H + 5
    caja(ax, MASTIL_Y, Z2 + MASTIL_H / 2, 6, MASTIL_H, C["imp"], ls="--", alpha=0.8)
    cam = Rectangle((MASTIL_Y + 8 - 4, zc - 16), 8, 32, fc="#555", ec="k", zorder=4)
    tr = matplotlib.transforms.Affine2D().rotate_deg_around(MASTIL_Y + 8, zc, CAM_INCL) + ax.transData
    cam.set_transform(tr)
    ax.add_patch(cam)
    fov = 25
    for a in (CAM_INCL - fov, CAM_INCL + fov):
        r = math.radians(a)
        d = zc / math.tan(r)
        ax.plot([MASTIL_Y + 8, MASTIL_Y + 8 + d], [zc, 0], color="#888", lw=0.7, ls="--")
    ax.text(70, 150, f"campo de visión\n{2 * fov}° vertical,\ninclinada {CAM_INCL}°", fontsize=7, color="#555")
    # paredes
    for y in (PASILLO / 2, PASILLO / 2 + 180):
        if y < 140:
            caja(ax, y + 6, 50, 12, 100, C["pared"], alpha=0.35)
    ax.text(PASILLO / 2 + 6, 104, "pared\n100", ha="center", fontsize=6)
    cota(ax, (-L / 2, 0), (-L / 2, Z1), f"{Z1:.0f}", off=-12, horiz=False)
    cota(ax, (-L / 2, 0), (-L / 2, Z2), f"{Z2:.0f}", off=-24, horiz=False)
    cota(ax, (-L / 2, 0), (-L / 2, zc), f"{zc:.0f} (ajustable 150–200)", off=-38, horiz=False)
    cota(ax, (-L / 2, 0), (L / 2, 0), f"{L}", off=-10)
    ax.annotate("FRENTE →", (100, 230), fontsize=9, weight="bold")

    ax2 = ejes(fig, [0.55, 0.06, 0.43, 0.84], ((-100, 100), (-15, 250)))
    ax2.plot([-100, 100], [0, 0], color="k", lw=1)
    caja(ax2, 0, Z1 + ESP / 2, L - 2 * A_RUEDA - 2, ESP, C["piso"])
    caja(ax2, 0, Z2 + ESP / 2, L, ESP, C["piso"])
    for s in (-1, 1):
        caja(ax2, s * (X_RUEDA_INT + A_RUEDA / 2), EJE_Z, A_RUEDA, D_RUEDA, C["rueda"], z=3)
        caja(ax2, s * (X_MOT_EXT - MOT_L / 2), EJE_Z, MOT_L, MOT_H, C["motor"], z=3)
        caja(ax2, s * 48, Z1 + ESP + SEP / 2, 5, SEP, "#aaa")
        caja(ax2, s * (TOF_LADO_X + 0.8), Z2 + ESP + 12, 1.6, 11, C["tof"], z=4)
        caja(ax2, s * PASILLO / 2 + s * 6, 50, 12, 100, C["pared"], alpha=0.35)
    caja(ax2, 0, Z1 + ESP + L298[2] / 2, L298[0], L298[2], C["l298"], alpha=0.5)
    caja(ax2, 0, Z1 + ESP + BAT[2] / 2, BAT[0], BAT[2], C["bat"], z=3)
    caja(ax2, 0, Z2 + ESP + 5 + 7, PLACA[0], 14, C["placa"], "Arduino", tc="white", fs=7)
    caja(ax2, 0, Z2 + ESP + 12, 25, 11, C["tof"], z=4)
    caja(ax2, 0, Z2 + MASTIL_H / 2 + 10, 10, MASTIL_H - 20, C["imp"], ls="--", alpha=0.6)
    caja(ax2, 0, zc, 32, 28, "#555", z=4)
    caja(ax2, 0, COLOR_Z + 1, COLOR_MOD, 2, C["color"], z=4)
    cota(ax2, (-L / 2, 0), (L / 2, 0), f"{L} (máximo)", off=-10)
    cota(ax2, (-PASILLO / 2, 100), (PASILLO / 2, 100), f"pasillo {PASILLO}", off=12)
    cota(ax2, (TOF_LADO_X, Z2 + 15), (PASILLO / 2, Z2 + 15), f"{PASILLO // 2 - TOF_LADO_X}", off=-8)
    pp.savefig(fig)
    plt.close(fig)


def en_laberinto(pp):
    fig = pagina("El robot dentro del laberinto",
                 "Celda de 180 mm: holguras, lecturas esperadas de los sensores y radio de giro")
    ax = ejes(fig, [0.02, 0.05, 0.55, 0.86], ((-130, 130), (-120, 290)))
    m = PASILLO / 2
    gr = 6
    for x0, y0, x1, y1 in ((-m - gr, -m, -m, m + 180), (m, -m, m + gr, m), (m, m + 150, m + gr, m + 180),
                           (-m - gr, -m - gr, m + gr, -m)):
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=C["pared"], ec="none", alpha=0.7))
    ax.add_patch(Rectangle((-m, m + 180), 2 * m, gr, fc=C["pared"], ec="none", alpha=0.7))
    ax.text(m + 10, m + 60, "sin pared:\nla celda de la\nderecha está abierta", fontsize=7, color="#555")
    ax.plot([-m, m], [m, m], color="#bbb", lw=0.6, ls=":")
    placa_redonda(ax, alpha=0.9, z=2)
    ruedas_planta(ax)
    giro = math.sqrt(2) * (L / 2 - R_ESQ) + R_ESQ
    ax.add_patch(Circle((0, 0), giro, fc="none", ec="#e67e22", lw=1.2, ls="--", zorder=6))
    ax.text(giro * 0.7, -giro * 0.75 - 6, f"giro R{giro:.0f}", color="#e67e22", fontsize=8)
    for s in (-1, 1):
        ax.annotate("", (s * m, 0), (s * TOF_LADO_X, 0), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
        ax.text(s * (m + 8), 6, f"{m - TOF_LADO_X:.0f}", ha="center", color=C["tof"], fontsize=9, weight="bold")
    ax.annotate("", (0, m), (0, TOF_FRENTE_Y), arrowprops=dict(arrowstyle="->", color=C["tof"], lw=1.5))
    ax.text(4, (TOF_FRENTE_Y + m) / 2, f"{m - TOF_FRENTE_Y:.0f}", color=C["tof"], fontsize=9)
    ax.text(0, m + 90, "celda siguiente\n(la ve la cámara en la iteración B)", ha="center", fontsize=8, color="#555")
    cota(ax, (-m, -m), (m, -m), f"{PASILLO}", off=-14)
    cota(ax, (L / 2, -L / 2), (m, -L / 2), f"{m - L / 2:.1f}", off=-6, fs=6)

    tx = fig.add_axes([0.6, 0.1, 0.38, 0.78])
    tx.axis("off")
    txt = (
        "Valores que usa el código\n"
        f"• D_LADO = {m - TOF_LADO_X:.0f} mm: lectura lateral con el robot centrado.\n"
        f"• D_FRENTE = {m - TOF_FRENTE_Y:.0f} mm: lectura frontal al llegar al\n"
        "  centro de una celda con pared enfrente. El robot frena\n"
        "  por distancia en vez de por tiempo y corrige el error\n"
        "  acumulado.\n"
        "• PARED = 120 mm: si la lectura es menor, hay pared en\n"
        "  esa celda; la siguiente pared quedaría a ≈230 mm.\n\n"
        "Holguras\n"
        f"• {m - L / 2:.1f} mm por lado con el robot centrado.\n"
        f"• Radio de giro {giro:.0f} mm contra {m:.0f} mm de medio pasillo:\n"
        f"  sobran {m - giro:.0f} mm al girar en su lugar.\n"
        "• Sin las esquinas redondeadas el radio sería 88 mm\n"
        "  y rozaría las paredes.\n\n"
        "Calibración rápida\n"
        "1. Centrar el robot a mano en una celda y anotar las\n"
        "   3 lecturas (modo calibración: encender con el botón\n"
        "   presionado). Esos son D_LADO y D_FRENTE reales.\n"
        "2. Ajustar MS/T_CELDA hasta que avance 180 mm en un\n"
        "   pasillo sin pared enfrente."
    )
    tx.text(0, 1, txt, va="top", fontsize=9.5, linespacing=1.45)
    pp.savefig(fig)
    plt.close(fig)


def tabla(fig, rect, titulo, filas, anchos):
    ax = fig.add_axes(rect)
    ax.axis("off")
    ax.set_title(titulo, fontsize=12, weight="bold", loc="left")
    t = ax.table(cellText=filas[1:], colLabels=filas[0], loc="upper left", cellLoc="left", colWidths=anchos)
    t.auto_set_font_size(False)
    t.set_fontsize(8.5)
    t.scale(1, 1.45)
    for (r, _), cell in t.get_celld().items():
        cell.set_edgecolor("#bbb")
        if r == 0:
            cell.set_facecolor("#33415c")
            cell.get_text().set_color("white")


def conexiones(pp):
    fig = pagina("Conexiones", "Mismo cableado en las dos iteraciones salvo donde se indica")
    comun = [
        ["Componente", "Pin del módulo", "UNO R3 (A)", "UNO Q (B)"],
        ["L298N", "ENA (sin jumper)", "D5", "D9"],
        ["L298N", "IN1 / IN2", "D7 / D8", "D4 / D5"],
        ["L298N", "ENB (sin jumper)", "D6", "D10"],
        ["L298N", "IN3 / IN4", "D9 / D10", "D7 / D8"],
        ["L298N", "12V / GND", "Batería + / GND", "Batería + / GND"],
        ["L298N", "OUT1-2 / OUT3-4", "Motor izq / der", "Motor izq / der"],
        ["VL53L0X izq", "XSHUT", "A0", "A0"],
        ["VL53L0X frente", "XSHUT", "A1", "A1"],
        ["VL53L0X der", "XSHUT", "A2", "A2"],
        ["VL53L0X ×3", "SDA / SCL", "A4 / A5", "SDA / SCL"],
        ["TCS34725", "SDA / SCL", "A4 / A5", "SDA / SCL"],
        ["OLED SSD1306", "SDA / SCL", "A4 / A5", "SDA / SCL"],
        ["Sensores y OLED", "VCC", "5V", "3.3V"],
        ["Botón arranque", "a GND", "D2", "D12"],
        ["Batería 2S", "+", "VIN", "VIN"],
        ["Cámara USB", "—", "no lleva", "hub USB-C"],
    ]
    tabla(fig, [0.04, 0.16, 0.6, 0.68], "Tabla de pines", comun, [0.2, 0.22, 0.17, 0.17])
    tx = fig.add_axes([0.67, 0.1, 0.31, 0.78])
    tx.axis("off")
    txt = (
        "Direcciones I2C\n"
        "• TCS34725: 0x29\n"
        "• OLED: 0x3C\n"
        "• VL53L0X: salen todos en 0x29 (igual que el\n"
        "  sensor de color). El código los apaga con XSHUT\n"
        "  y los prende uno por uno para darles\n"
        "  0x30, 0x31 y 0x32.\n\n"
        "Alimentación\n"
        "• GND común: batería, L298N, Arduino y sensores.\n"
        "• No usar el regulador de 5 V del L298N para\n"
        "  el Arduino.\n"
        "• En la iteración B los pines son de 3.3 V. El L298N\n"
        "  acepta esa lógica.\n\n"
        "¿Por qué pines distintos en A?\n"
        "• En el UNO R3, el Timer1 se usa como base de\n"
        "  tiempo de 10 ms (requisito de temporizadores).\n"
        "  Eso quita el PWM de D9/D10, así que los\n"
        "  motores usan D5/D6 (Timer0)."
    )
    tx.text(0, 1, txt, va="top", fontsize=9.5, linespacing=1.45)
    pp.savefig(fig)
    plt.close(fig)


def piezas(pp):
    fig = pagina("Piezas a imprimir y lista de material")
    imp = [
        ["Pieza (PIEZA= en chasis.scad)", "Cant.", "Notas"],
        ["piso1", "1", "PLA/PETG, 3 mm, 30% relleno"],
        ["piso2", "1", "Igual"],
        ["soporte_motor", "2", "Imprimir boca abajo"],
        ["soporte_color", "1", "Negro mate (tapa la luz)"],
        ["patin", "2", "Lijar la punta; ajustar altura"],
        ["soporte_tof", "3", "Escuadra para el VL53L0X"],
        ["mastil", "1", "Solo iteración B; acostado"],
    ]
    bom = [
        ["Material", "Cant.", "A", "B"],
        ["Arduino UNO R3 (ATmega328P)", "1", "✔", ""],
        ["Arduino UNO Q", "1", "", "✔"],
        ["Motorreductor N20 6 V (300–500 RPM)", "2", "✔", "✔"],
        ["Rueda N20 Ø34 × 20 mm", "2", "✔", "✔"],
        ["Puente H L298N (Steren)", "1", "✔", "✔"],
        ["Sensor de color TCS34725", "1", "✔", "✔"],
        ["Sensor de distancia VL53L0X", "3", "✔", "✔"],
        ["OLED SSD1306 0.96\" I2C", "1", "✔", "✔"],
        ["Botón pulsador", "1", "✔", "✔"],
        ["Batería 2S 18650 7.4 V 3000 mAh (conector T)", "1", "✔", "✔"],
        ["Cargador balanceador 2S (JST-XH 3 pines)", "1", "✔", "✔"],
        ["Cámara USB + hub USB-C", "1", "", "✔"],
        ["Separador M3 × 32 / tornillos M3", "4 / 20", "✔", "✔"],
    ]
    tabla(fig, [0.04, 0.3, 0.42, 0.58], "Piezas impresas", imp, [0.5, 0.1, 0.45])
    tabla(fig, [0.52, 0.2, 0.45, 0.68], "Lista de material", bom, [0.62, 0.12, 0.1, 0.1])
    fig.text(0.04, 0.2, "Exportar STL:  openscad -D 'PIEZA=\"piso1\"' -o piso1.stl chasis.scad", fontsize=9,
             family="DejaVu Sans Mono")
    fig.text(0.04, 0.16, "Ver el ensamble:  abrir chasis.scad en OpenSCAD y cambiar VERSION a \"unoq\" o \"328p\".",
             fontsize=9)
    pp.savefig(fig)
    plt.close(fig)


if __name__ == "__main__":
    pdf()
