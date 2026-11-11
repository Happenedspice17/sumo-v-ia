"""Diagrama de conexiones del robot (mismo para UNO R3 y UNO Q). Colores = cables.csv.
Uso: python3 docs/diagrama_conexiones.py  ->  docs/diagrama_conexiones.png y .pdf
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle

AQUI = os.path.dirname(os.path.abspath(__file__))
COL = {"VCC": "red", "GND": "black", "SDA": "royalblue", "SCL": "darkturquoise", "XSHUT": "green",
       "EN": "mediumpurple", "IN": "sienna", "PWR": "darkorange", "BTN": "hotpink"}

fig, ax = plt.subplots(figsize=(17, 10.5))
ax.set_xlim(0, 160)
ax.set_ylim(0, 100)
ax.set_aspect("equal")
ax.axis("off")


def caja(x, y, w, h, titulo, color="#e8eef7", sub=None, punteada=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=color, ec="#33415c", lw=1.4,
                                ls="--" if punteada else "-"))
    ax.text(x + w / 2, y + h - 2, titulo, ha="center", va="top", fontsize=11, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h - 5.2, sub, ha="center", va="top", fontsize=7.5, color="#444")


def pin(x, y, nombre, lado):
    ax.plot(x, y, "o", ms=4, color="#33415c", zorder=5)
    ax.text(x + (-1 if lado == "der" else 1), y, nombre, ha="right" if lado == "der" else "left",
            va="center", fontsize=8)


def cable(pts, c, lw=2.2):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=COL.get(c, c), lw=lw, solid_capstyle="round", zorder=3)


def nodo(x, y, c):
    ax.plot(x, y, "o", ms=6, color=COL.get(c, c), zorder=4)


# ---------- Bateria e interruptor ----------
caja(3, 80, 22, 13, "Batería 2S", "#dfe9ff", "18650, 7.4 V, conector T")
pin(25, 89, "+", "der"); pin(25, 84, "−", "der")
caja(32, 85, 13, 8, "Interruptor", "#fff4d6")
pin(32, 89, "", "izq"); pin(45, 89, "", "der")
cable([(25, 89), (32, 89)], "VCC")

# ---------- L298N ----------
LX, LY, LW, LH = 3, 18, 26, 50
caja(LX, LY, LW, LH, "L298N", "#f3e1e1", "quita jumpers ENA/ENB;\njumper 5V-EN se queda")
L = {"12V": 61, "GND": 57, "5V": 53, "ENA": 45, "IN1": 42, "IN2": 39, "IN3": 36, "IN4": 33, "ENB": 30}
for n, y in L.items():
    pin(LX + LW, y, n if n != "5V" else "5V (no se usa)", "der")
OUT = {"OUT1": 7, "OUT2": 12, "OUT3": 20, "OUT4": 25}
for n, x in OUT.items():
    ax.plot(x, LY, "o", ms=4, color="#33415c", zorder=5)
    ax.text(x, LY + 1.2, n, ha="center", va="bottom", fontsize=7, rotation=90)

# motores
for cx, nom, a, b in [(9.5, "Motor izq", "OUT1", "OUT2"), (22.5, "Motor der", "OUT3", "OUT4")]:
    ax.add_patch(Circle((cx, 6), 4, fc="#f2d36b", ec="#33415c", lw=1.2))
    ax.text(cx, 6, "M", ha="center", va="center", fontsize=11, weight="bold")
    ax.text(cx, 0.8, nom, ha="center", va="bottom", fontsize=7)
    cable([(OUT[a], LY), (OUT[a], 13), (cx - 2, 9.5)], "gold")
    cable([(OUT[b], LY), (OUT[b], 13), (cx + 2, 9.5)], "silver")

ax.text(16, -1.5, "Cada motor: capacitor de 100 nF entre sus terminales", ha="center", va="top", fontsize=6.5)

# ---------- Placa ----------
PX, PY, PW, PH = 62, 12, 30, 78
caja(PX, PY, PW, PH, "UNO R3  /  UNO Q", "#e3f1e3", "mismo mapa de pines;\nse cambia solo la placa")
P_IZQ = {"VIN": 65, "GND": 57, "D5": 45, "D7": 42, "D8": 39, "D9": 36, "D10": 33, "D6": 30, "D2": 21, "GND ": 17}
for n, y in P_IZQ.items():
    pin(PX, y, n.strip(), "izq")
P_DER = {"5V / 3V3": 82, "GND": 78, "SDA": 74, "SCL": 70, "A0": 52, "A1": 47, "A2": 42}
for n, y in P_DER.items():
    pin(PX + PW, y, n, "der")
ax.text(PX + PW - 1, 66.5, "SDA/SCL: los de junto a AREF", ha="right", va="top", fontsize=6.5, color="#444")

# potencia
cable([(45, 89), (50, 89), (50, L["12V"]), (LX + LW, L["12V"])], "PWR")
cable([(50, 89), (55, 89), (55, P_IZQ["VIN"]), (PX, P_IZQ["VIN"])], "PWR")
nodo(50, 89, "PWR")
cable([(25, 84), (30, 84), (30, 75), (47, 75), (47, L["GND"]), (LX + LW, L["GND"])], "GND")
cable([(47, L["GND"]), (PX, P_IZQ["GND"])], "GND")
nodo(47, L["GND"], "GND")
ax.text(56, 70, "naranja: después\ndel interruptor", fontsize=6.5, color=COL["PWR"])

# logica del L298N
for l298, placa, c in [("ENA", "D5", "EN"), ("IN1", "D7", "IN"), ("IN2", "D8", "IN"), ("IN3", "D9", "IN"),
                       ("IN4", "D10", "IN"), ("ENB", "D6", "EN")]:
    cable([(LX + LW, L[l298]), (PX, P_IZQ[placa])], c, lw=1.8)

# boton
caja(36, 15, 13, 9, "Botón", "#fbe3f0")
pin(49, 21, "", "der"); pin(49, 17, "", "der")
cable([(49, 21), (PX, 21)], "BTN", lw=1.8)
cable([(49, 17), (PX, 17)], "GND", lw=1.8)
ax.text(42.5, 12.5, "INPUT_PULLUP:\napretado = LOW", ha="center", va="top", fontsize=6.5)

# ---------- Bus I2C ----------
RIEL = {"VCC": 104, "GND": 107, "SDA": 110, "SCL": 113}
ax.add_patch(FancyBboxPatch((101.5, 8), 14, 84, boxstyle="round,pad=0.4", fc="#f7f7f7", ec="#999", lw=1, ls="--"))
ax.text(108.5, 95.5, "Bus I2C en la protoboard\nVCC = 5V con R3, 3V3 con Q", ha="center", va="bottom",
        fontsize=8, weight="bold")
for n, x in RIEL.items():
    cable([(x, 10), (x, 90)], n, lw=2.8)
    ax.text(x, 9, n, ha="center", va="top", fontsize=7, rotation=90)
for n, r in [("5V / 3V3", "VCC"), ("GND", "GND"), ("SDA", "SDA"), ("SCL", "SCL")]:
    cable([(PX + PW, P_DER[n]), (RIEL[r], P_DER[n])], r, lw=1.8)
    nodo(RIEL[r], P_DER[n], r)

# ---------- Sensores ----------
DX, DW = 125, 30
SENS = [("VL53L0X izquierdo", 78, "A0"), ("VL53L0X frente", 64, "A1"), ("VL53L0X derecho", 50, "A2"),
        ("TCS34725 (color)", 38.3, None), ("OLED SSD1306", 25.5, None), ("MPU-6050 (GY-521)", 10.5, None)]
for i, (nom, y0, xs) in enumerate(SENS):
    h = 13 if xs or "MPU" in nom else 11
    caja(DX, y0, DW, h, nom, "#eef3ff" if xs else "#fff3e0" if "MPU" in nom else "#f1ffe8")
    pines = [("VIN" if "OLED" not in nom and "MPU" not in nom else "VCC", "VCC"), ("GND", "GND"), ("SDA", "SDA"),
             ("SCL", "SCL")]
    for k, (pn, r) in enumerate(pines):
        y = y0 + h - 5 - k * 1.7
        pin(DX, y, pn, "izq")
        cable([(RIEL[r], y), (DX, y)], r, lw=1.4)
        nodo(RIEL[r], y, r)
    y = y0 + h - 5 - 4 * 1.7
    if xs:
        pin(DX, y, "XSHUT", "izq")
        xr = 96 + i * 1.6
        cable([(PX + PW, P_DER[xs]), (xr, P_DER[xs]), (xr, y), (DX, y)], "XSHUT", lw=1.4)
        ax.text(DX + DW - 1, y, "GPIO1 libre", ha="right", va="center", fontsize=6.5, color="#666")
    if "MPU" in nom:
        pin(DX, y, "AD0", "izq")
        cable([(RIEL["GND"], y), (DX, y)], "GND", lw=1.4)
        nodo(RIEL["GND"], y, "GND")
        ax.text(DX + DW - 1, y, "INT, XDA, XCL libres", ha="right", va="center", fontsize=6.5, color="#666")
ax.text(DX + DW / 2, 2, "Direcciones I2C: los VL53L0X arrancan en 0x29 y el código los pasa a 0x30-0x32\nuno por uno con XSHUT; TCS34725 0x29; OLED 0x3C; MPU-6050 0x68 (AD0 a GND)",
        ha="center", va="bottom", fontsize=6.5, color="#444")

# ---------- Solo Q ----------
caja(56, 92.5, 42, 5, "Solo UNO Q: USB-C → hub → cámara USB", "#ffffff", punteada=True)

ax.set_title("Diagrama de conexiones — robot de laberinto", fontsize=15, weight="bold", pad=4)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(AQUI, f"diagrama_conexiones.{ext}"), dpi=170, bbox_inches="tight")
print("Generado diagrama_conexiones.png y .pdf")
