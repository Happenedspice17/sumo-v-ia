import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams["font.family"] = "DejaVu Sans"
fig, ax = plt.subplots(figsize=(16, 10.5))
ax.set_xlim(0, 160)
ax.set_ylim(-3, 105)
ax.axis("off")

COL = {"5V": "#d62728", "GND": "#111", "SDA": "#1f77b4", "SCL": "#17becf", "BAT": "#ff7f0e",
       "PWM": "#9467bd", "DIR": "#8c564b", "X": "#2ca02c", "BTN": "#e377c2"}


def box(x, y, w, h, t, c, pins=None, side="r", tc="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4", fc=c, ec="#222", lw=1.2))
    ax.text(x + w / 2, y + h - 1.5, t, ha="center", va="top", fontsize=10, weight="bold", color=tc)
    P = {}
    for i, p in enumerate(pins or []):
        n = len(pins)
        py = y + h - 7 - i * (h - 9) / max(n - 1, 1)
        px = x + w if side == "r" else x
        ax.plot(px, py, "o", color="#ddd", mec="#222", ms=5, zorder=5)
        ax.text(px + (-1.2 if side == "r" else 1.2), py, p, ha="right" if side == "r" else "left",
                va="center", fontsize=8, color=tc)
        P[p] = (px, py)
    return P


def w(a, b, c, mid, lw=1.8, ls="-"):
    (x1, y1), (x2, y2) = a, b
    ax.plot([x1, mid, mid, x2], [y1, y1, y2, y2], color=c, lw=lw, ls=ls, zorder=3)


# Arduino: pines de potencia/motores a la izquierda, sensores a la derecha
UL = box(62, 30, 26, 62, "Arduino UNO R3\n(ATmega328P)", "#1a7f8e",
         ["VIN", "GND", "D2", "D5", "D6", "D7", "D8", "D9", "D10"], side="l")
UR = box(62, 30, 26, 62, "", "#1a7f8e", ["5V", "GND ", "A4 SDA", "A5 SCL", "A0", "A1", "A2"], side="r")

L = box(16, 52, 22, 40, "L298N", "#c0392b", ["12V", "GND", "ENA", "IN1", "IN2", "ENB", "IN3", "IN4"])
box(1, 78, 9, 9, "Motor\nizq", "#d4a017", tc="#222")
box(1, 62, 9, 9, "Motor\nder", "#d4a017", tc="#222")
ax.plot([10.4, 15.6], [82, 82], color="#555", lw=2)
ax.plot([10.4, 15.6], [66, 66], color="#555", lw=2)
ax.text(13, 84, "OUT1-2", fontsize=7, ha="center")
ax.text(13, 68, "OUT3-4", fontsize=7, ha="center")
ax.text(27, 48.5, "Quitar jumpers ENA/ENB.\nNo usar su salida de 5V.", fontsize=7.5, ha="center", color="#444")

B = box(2, 22, 24, 14, "Batería 2S 18650\n7.4 V (conector T)", "#2a5bd7", ["+", "−"])
box(32, 26, 12, 9, "Interruptor", "#777")
S = {"in": (32, 29), "out": (44.4, 29)}
for q in S.values():
    ax.plot(*q, "o", color="#ddd", mec="#222", ms=5, zorder=5)
w(B["+"], S["in"], COL["BAT"], mid=29)
w(S["out"], L["12V"], COL["BAT"], mid=50)
w(S["out"], UL["VIN"], COL["BAT"], mid=50)
w(B["−"], L["GND"], COL["GND"], mid=47)
w(B["−"], UL["GND"], COL["GND"], mid=47)
for a, b, c, m in (("ENA", "D5", "PWM", 42), ("IN1", "D7", "DIR", 44), ("IN2", "D8", "DIR", 46),
                   ("ENB", "D6", "PWM", 48), ("IN3", "D9", "DIR", 54), ("IN4", "D10", "DIR", 56)):
    w(L[a], UL[b], COL[c], mid=m)

box(46, 8, 12, 7, "Botón", "#444")
w((58.4, 11.5), UL["D2"], COL["BTN"], mid=59.5)
ax.text(52, 5.5, "otra pata → GND", fontsize=7.5, ha="center")

# Bus I2C en protoboard
bx = 100
ax.add_patch(FancyBboxPatch((bx, 6), 7, 88, boxstyle="round,pad=0.3", fc="#f4f4f4", ec="#888"))
ax.text(bx + 3.5, 96, "protoboard", ha="center", fontsize=8)
rails = {"5V": bx + 1, "GND": bx + 2.7, "SDA": bx + 4.4, "SCL": bx + 6.1}
for k, x in rails.items():
    ax.plot([x, x], [7, 93], color=COL[k], lw=2.4)
for k, pin in (("5V", "5V"), ("GND", "GND "), ("SDA", "A4 SDA"), ("SCL", "A5 SCL")):
    p = UR[pin]
    ax.plot([p[0], rails[k]], [p[1], p[1]], color=COL[k], lw=1.8)

mods = [("VL53L0X izquierdo", 79, "A0", 90), ("VL53L0X frente", 62, "A1", 92.5),
        ("VL53L0X derecho", 45, "A2", 95), ("TCS34725 (morado)", 25, None, 0), ("OLED SSD1306", 6, None, 0)]
for name, y, xpin, xm in mods:
    vcc = "VIN" if "TCS" in name else "VCC"
    pins = [vcc, "GND", "SDA", "SCL"] + (["XSHUT"] if xpin else [])
    color = "#2e7d32" if "VL" in name else ("#6a1b9a" if "TCS" in name else "#333")
    P = box(122, y, 30, 15, name, color, pins, side="l")
    for k, pn in zip(("5V", "GND", "SDA", "SCL"), pins[:4]):
        ax.plot([rails[k], P[pn][0]], [P[pn][1]] * 2, color=COL[k], lw=1.4)
    nota = "GPIO1: sin conectar" if "VL" in name else ("LED, INT, 3V3: sin conectar" if "TCS" in name else "")
    if nota:
        ax.text(137, y - 1.3, nota, fontsize=7, ha="center", color="#555")
    if xpin:
        xs, up = P["XSHUT"], UR[xpin]
        ax.plot([up[0], xm, xm, 117, 117, xs[0]], [up[1], up[1], y - 3, y - 3, xs[1], xs[1]],
                color=COL["X"], lw=1.4, ls="--")

ax.set_title("Conexiones · Arduino UNO R3 (ATmega328P)", fontsize=16, weight="bold", loc="left")
leg = [("Batería 7.4 V", "BAT"), ("5V", "5V"), ("GND", "GND"), ("SDA", "SDA"), ("SCL", "SCL"),
       ("PWM motores", "PWM"), ("Dirección", "DIR"), ("XSHUT", "X"), ("Botón", "BTN")]
for i, (t, k) in enumerate(leg):
    ax.plot([2 + i * 17.5, 6 + i * 17.5], [-1.5, -1.5], color=COL[k], lw=3)
    ax.text(7 + i * 17.5, -1.5, t, va="center", fontsize=8.5)
fig.savefig("/home/user/sumo-v-ia/atmega328p/img/conexiones_uno.png", dpi=110, bbox_inches="tight")
