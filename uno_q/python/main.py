import sys
import time
import traceback
sys.stdout.reconfigure(line_buffering=True)   # sin esto los print salen tarde o se pierden si la app truena
T0 = time.monotonic()


def paso(m):
    """Debug de arranque: en la pestana Python se ve hasta donde llego."""
    print(f"[arranque {time.monotonic() - T0:5.1f} s] {m}", flush=True)


paso("Python " + sys.version.split()[0])
from arduino.app_utils import *
paso("arduino.app_utils OK")
from arduino.app_bricks.web_ui import WebUI
paso("WebUI OK")
import os
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")   # sin camara, OpenCV llena el log de WARN cada 2 s
import cv2
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)   # sin los WARN de V4L2 cada 2 s
except AttributeError:
    pass
paso("cv2 OK")
import glob
import math
import random
import numpy as np
paso("numpy OK")
import json
import threading
import base64

print("Python OK, cv2", cv2.__version__)

COLORES = ["PISO", "ROJO", "VERDE", "AZUL", "AMAR"]
OBJETIVO = 4                             # se detiene al encontrar este color (4 = AMAR)
DATOS = "/app/datos"                     # en una subcarpeta: archivos en la raiz de la app confunden a App Lab
os.makedirs(DATOS, exist_ok=True)
LOGS = DATOS + "/logs"                   # todo lo que se imprime, en archivos: uno por arranque y uno por corrida


class Registro:
    """Copia la salida a LOGS/NNNN_fecha_nombre.txt (guarda los ultimos 100). Si el disco falla, sigue sin archivo."""
    def __init__(self, sal):
        self.sal, self.f = sal, None

    def nuevo(self, nombre):
        try:
            os.makedirs(LOGS, exist_ok=True)
            vs = sorted(v for v in os.listdir(LOGS) if v[:4].isdigit())
            for v in vs[:-99]:
                os.remove(os.path.join(LOGS, v))
            if self.f:
                self.f.close()
            n = int(vs[-1][:4]) + 1 if vs else 1
            self.f = open(f"{LOGS}/{n:04d}_{time.strftime('%m%d_%H%M%S')}_{nombre}.txt", "w")
        except OSError as e:
            self.f = None
            self.sal.write(f"Log a archivo fallo: {e!r}\n")

    def write(self, t):
        self.sal.write(t)
        if self.f:
            try:
                self.f.write(t)
                self.f.flush()
            except OSError:
                self.f = None

    def flush(self):
        self.sal.flush()

    def __getattr__(self, n):            # isatty, encoding...: uvicorn (WebUI) se los pide a sys.stdout
        return getattr(self.sal, n)


sys.stdout = Registro(sys.stdout)
sys.stdout.nuevo("arranque")
ARCH_COL = DATOS + "/colores.json"
ARCH_MAPA = DATOS + "/mapa.json"
ARCH_TOF = DATOS + "/tof.json"
ARCH_AVANCE = DATOS + "/avance.json"     # ms por celda calibrados en la web (avance de prueba)
TOF_NOM = ["izq", "frente", "der"]
tof_cal = {n: {} for n in TOF_NOM}       # sensor -> {mm reales: lectura cruda promedio}
# r, g, b normalizados y brillo c; los mismos de refs[] del sketch
REFS = [[0.282, 0.379, 0.333, 153], [0.602, 0.208, 0.188, 581], [0.155, 0.535, 0.309, 636],
        [0.16, 0.329, 0.508, 354], [0.409, 0.449, 0.142, 1836]]
BRILLO_MIN = 1.3                         # una marca refleja al menos 1.3 veces mas que el piso negro

# ---------- Movimiento ----------
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
CELDA = 180                              # mm por avance; la posicion solo sirve para contar visitas
LADO_CERCA = 35                          # mm: lateral mas cerca que esto tras un choque = pegado a esa pared
PARED = 120                              # mm: lateral con esto o mas = libre
PARED_F = 55                             # mm reales (frontal calibrado): menos de esto = pared (= PARED_F del sketch)
FRENTE_LIBRE = 120                       # mm reales: a la mitad entre pared en su celda (~30) y en la siguiente (~210)
D_FRENTE_TOF = 30                        # mm reales donde se detiene el sketch con pared enfrente (= D_FRENTE)
D_LADO_TOF = 41                          # mm reales de cada lateral con el robot centrado (= D_LADO)
FUERA = 2000                             # mm: los 2 laterales sin nada a esta distancia = salio del laberinto
RECORRIDO = -3                           # voto de un paso por donde ya paso (-5) con hasta 2 lecturas en contra
CENTRO = 5                               # celdas de la esquina de salida a la meta (laberinto de 11 x 11)
ESTRATEGIA = "pista"                     # "pista": trae el mapa de la pista y se ubica con lo que ven los ToF;
                                         # "brujula": sin mapa (respaldo); "mapa": Tremaux con el mapa que arma
PERDIDAS_MAX = 10                        # pista: perdido estas veces = no es esta pista (o la cambiaron mucho): solo brujula
MALA = 0.01                              # pista: lectura que casi no cuadra con ninguna hipotesis (0.7^3 = 0.34 cuadra)
CONFIANZA = 0.6                          # pista: con menos certeza de donde esta, decide con la brujula
RUIDO = 0.6                              # brujula: azar en cada decision (rompe ciclos)
CASTIGO = 1.0                            # brujula: castigo por cada vez que ya tomo esa salida desde esa celda aproximada
BARRE, BARRE_PASO = 35, 7                # grados: barrido para cuadrarse con las paredes (cuadrar)
CENTRA_F = 600                           # mm: tras avanzar, con pared enfrente a menos de esto se centra en la celda con ella
PASILLO = 3                              # celdas maximas de un tiron con pared a ambos lados (1 = parar en cada celda)
VOTO_MAX = 5                             # cada lectura vota pared (+1) o libre (-1); tope para que el mapa se corrija
Y_COLOR = 34                             # mm del eje al sensor de color (adelante; CAD: COLOR_Y)

# ---------- Camara (OV9281 monocromatica, obturador global): asistencia, nunca decide sola ----------
CAM_ID = 2                               # /dev/video0 y video1 son internos de la placa: nunca son la camara
USAR_CAM = False                         # apagada por ahora: solo ToF
EXPERIMENTAL = False                     # True: version experimental, ademas distancias y aberturas por camara
ANCHO, ALTO = 320, 240
ARCH_CAM = DATOS + "/camara.json"
# Calibracion de la camara (se ajusta en la web y se guarda): exposicion (0 = automatica; unidades UVC de 100 us),
# columna del punto de fuga con el robot derecho (x0), radianes por pixel (k) y, experimental, fila -> mm
camcal = {"expo": 0, "gain": -1, "sens": 0, "x0": ANCHO / 2, "k": 0.008, "filas": {}}   # gain -1: no la toca
cam_leido = {}
# Blanco = pared (piso negro). Umbral de gris automatico (Otsu) acotado: una imagen toda negra no inventa blanco
UMBRAL_MIN, UMBRAL_MAX = 100, 220
ZONA_PASO = (0.30, 0.55, 0.70, 1.00)     # piso por donde va a pasar, en fraccion de la imagen
BLANCO_MAX = 0.15                        # fraccion de blanco en ZONA_PASO para ir lento
# Rumbo: punto de fuga de las bases de las 2 paredes del pasillo
ZONA_BORDES = (0.45, 0.95)               # filas (fraccion) donde busca las bases de las paredes
ANG_MIN, ANG_MAX = 4, 20                 # grados: menos no corrige; mas es una lectura mala
# Experimental: profundidad por fila (columnas en fraccion) y aberturas en la celda siguiente
COLS = (0.1, 0.3, 0.5, 0.7, 0.9)
SIG = (60, 240)                          # mm del frontal: tramo de las paredes de la celda siguiente

pos = (0, 0)
rumbo = 0
cam = None
videos = None
cam_lock = threading.Lock()
cuenta = [0] * len(COLORES)
encontrado = False
# Mapa: celda -> [N, E, S, O] con 1 pared, 0 libre, None sin dato; colores: celda -> color; meta: celda del amarillo
muros = {}
usos = {}                                # brujula: (celda aproximada, rumbo) -> veces tomada
ms_celda = 700                           # ms por celda del avance por tiempo (se calibra en la web)
signo = [0, 0]                           # hacia donde esta el centro en x, y (0 = aun no se sabe)
vistas = set()                           # celdas donde el robot ya leyo sus 3 ToF (se guarda con el mapa)
colores = {}
meta = None
# Para la pagina web: durante una corrida lee esto (lo actualiza el robot) en vez de pedirle al Bridge
corriendo = False
t_ini = None                             # inicio de la corrida (time.monotonic())
t_meta = None                            # segundos hasta el amarillo en la ultima corrida
t_fin = None                             # duracion de la ultima corrida
log_col = []                             # colores vistos en la corrida: tiempo, color, celda
pedido = None                            # desde la web: "corre", "alto" o "borra" (como el boton D2)
fase_act = ""
vivo = {"izq": 9999, "frente": 9999, "der": 9999, "mm": 0, "saltos": 0, "v": [0, 0, 0, 0]}
ult_img = None
FASES = ["", "SENSA", "DECIDE", "GIRA", "AVANZA", "ESCANEA"]


def escribe(ruta, datos):
    """Escribe completo o nada: si se apaga a la mitad no deja un archivo roto."""
    with open(ruta + ".tmp", "w") as f:
        json.dump(datos, f)
    os.replace(ruta + ".tmp", ruta)


def lee(ruta):
    """None si no existe o esta roto (un archivo vacio ya no tumba la app)."""
    try:
        with open(ruta) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# ---------- Comunicacion con el MCU ----------
rpc_err = set()


def rpc(nombre, *args):
    while True:
        try:
            return Bridge.call(nombre, *args)
        except Exception as e:
            if nombre not in rpc_err:        # avisa una vez por RPC: si se repite, el sketch no lo tiene o no corre
                rpc_err.add(nombre)
                print(f"RPC {nombre}{args} fallo: {e!r} (reintento cada 0.2 s)", flush=True)
            time.sleep(0.2)


def estado(e):
    rpc("set_estado", e)


def fase(f):
    global fase_act
    fase_act = f
    rpc("set_fase", FASES.index(f))


def revisar_color(avanza):
    """El sketch manda un color solo si lo leyo 3 veces seguidas. Va al mapa en la celda donde esta el sensor;
    el amarillo es la meta."""
    global encontrado, meta
    c = rpc("color")
    if not c:
        return
    mm = rpc("odo", 0) if avanza else 0
    k = int((mm + Y_COLOR + CELDA / 2) // CELDA)
    cel = (pos[0] + DX[rumbo] * k, pos[1] + DY[rumbo] * k)
    global t_meta
    t = round(time.monotonic() - t_ini, 1) if t_ini else 0
    if c == OBJETIVO:
        encontrado, meta = True, cel
        rpc("alto")
        t_meta = t
        print(f"{COLORES[c]} encontrado en {cel}: meta a los {t} s")
    if not log_col or log_col[-1][1:] != [COLORES[c], list(cel)]:
        log_col.append([t, COLORES[c], list(cel)])
    if cel in colores:                   # cada celda se cuenta una vez
        return
    colores[cel] = c
    cuenta[c] += 1
    rpc("set_cuenta", c, cuenta[c])
    print(f"Marca {COLORES[c]} en {cel} -> {cuenta[c]}")


def esperar(avanza=False):
    while rpc("ocupado"):
        revisar_color(avanza)
        time.sleep(0.02)
    revisar_color(avanza)


def girar(rel):
    """rel: 1 derecha, -1 izquierda, 2 media vuelta, 0 nada."""
    global rumbo
    if rel:
        rpc("girar", rel)
        esperar()
        mal = abs(rpc("odo", 8)) > 10 or rpc("odo", 13)   # giro chueco o atorado: el frente ya no es de fiar
        rel += verifica_giro()
        if mal:
            cuadrar()
        time.sleep(0.1)                  # ToF frescos: con la lectura de antes del giro el sketch cree que tiene
                                         # la pared enfrente y avanza 0 mm (paso en pista)
    rumbo = (rumbo + rel) % 4


def cuadra_angulo(pts):
    """pts = [(grados, izq, frente, der)] de un barrido en su lugar. Devuelve los grados donde el robot queda
    perpendicular a las paredes, o None si el barrido no sirve. Frente a una pared (o entre 2), la lectura
    es minima justo de frente: ajusta una parabola y toma su vertice. El cono del ToF aplana el minimo, por eso
    barre +-35 grados; un ajuste malo (puntas de pared, aberturas) se descarta por su error."""
    xs = [p[0] for p in pts]
    if max(xs) - min(xs) < BARRE:        # no pudo girar (atorado): no hay barrido
        return None
    mx = sum(xs) / len(xs)
    X = [x - mx for x in xs]
    n, s2, s3, s4 = len(X), sum(x * x for x in X), sum(x ** 3 for x in X), sum(x ** 4 for x in X)
    series = []
    fr = [p[2] for p in pts]
    if min(fr) < CELDA - D_FRENTE_TOF and max(fr) < 2 * (CELDA - D_FRENTE_TOF):   # pared enfrente, en su celda
        series.append(fr)
    if max(max(p[1], p[3]) for p in pts) < 300:                                   # pared a los 2 lados
        series.append([p[1] + p[3] for p in pts])
    num = den = 0
    for ys in series:
        sy, sxy, sx2y = sum(ys), sum(x * y for x, y in zip(X, ys)), sum(x * x * y for x, y in zip(X, ys))
        a = (n * sx2y - s2 * sy) / (n * s4 - s2 * s2)
        if a <= 0:
            continue
        b = (sxy - a * s3) / s2
        c = (sy - a * s2) / n
        rms = (sum((a * x * x + b * x + c - y) ** 2 for x, y in zip(X, ys)) / n) ** 0.5
        x0 = mx - b / (2 * a)
        if abs(x0) <= 0.7 * BARRE and rms <= 0.15 * (max(ys) - min(ys)):
            num, den = num + a * x0, den + a
    return num / den if den else None


def cuadrar():
    """Recupera el frente con las paredes (el MPU solo mide giro, no sabe donde es el frente): barre +-BARRE
    grados en su lugar leyendo los ToF, y deja el rumbo deseado perpendicular a la pared. Unos 5 s; solo con MPU."""
    if rpc("ajustar", -BARRE) == 2:      # sin MPU giro por tiempo y no sabe cuanto: regresa y no toca nada
        esperar()
        if rpc("ajustar", BARRE) == 2:
            esperar()
        return
    a, pts, g = 0, [], -BARRE            # a = grados reales desde donde empezo
    for _ in range(2 * BARRE // BARRE_PASO + 1):
        if rpc("alinear", 180) == 2:
            esperar()
        a += g + rpc("odo", 16) / 10     # en decimas: con grados enteros el error se acumulaba (8 grados en el barrido)
        ls = [[], [], []]
        for _ in range(5):
            time.sleep(0.03)
            for l, i in zip(ls, (6, 5, 7)):
                l.append(rpc("odo", i))
        pts.append([a] + [sorted(l)[2] for l in ls])
        g = BARRE_PASO
        rpc("ajustar", g)
    x0 = cuadra_angulo(pts)
    rpc("ajustar", round((x0 or 0) - a) or 1)   # deseado = perpendicular a la pared (ajustar(0) no hace nada)
    for _ in range(2):                   # el giro corta antes por la inercia: el segundo lo termina
        if rpc("alinear", 180) == 2:
            esperar()
    time.sleep(0.1)
    print("Cuadre: " + (f"el frente estaba a {x0:+.0f} grados, corregido" if x0 is not None
                        else "sin pared clara para cuadrarme, sigo igual"), [tuple(p) for p in pts])


def verifica_giro():
    """Con MPU: si el giro quedo lejos del rumbo deseado (se atoro o choco), lo termina girando en su lugar.
    Si aun asi queda a 45 grados o mas, acepta el rumbo real: devuelve los cuartos de vuelta de diferencia
    y mueve la referencia del sketch, para que el mapa no se tuerza. Sin MPU el desvio vale 0."""
    atoron = rpc("odo", 13)
    if atoron:
        print(f"MPU: el giro se atoro {atoron} vez/veces (retrocedio y siguio)")
    dev = rpc("odo", 8)
    for _ in range(2):
        if abs(dev) <= 10:
            return 0
        print(f"MPU: el giro quedo a {dev:+d} grados, lo termino")
        if rpc("alinear", 180) == 2:
            esperar()
        dev = rpc("odo", 8)
    k = round(dev / 90)
    if k:
        print(f"MPU: quedo {k:+d} cuartos de vuelta distinto de lo pedido; el mapa toma el rumbo real")
        if 90 * k - dev:
            rpc("ajustar", 90 * k - dev)
    return k


def tof3(n=3):
    """izq, frente, der: la menor de n lecturas de cada VL53L0X (una lectura mala no deja pasar)."""
    d = [9999] * 3
    for _ in range(n):
        time.sleep(0.03)                 # lectura nueva de los VL53L0X
        d = [min(a, rpc("odo", i)) for a, i in zip(d, (6, 5, 7))]
    vivo["izq"], vivo["frente"], vivo["der"] = d
    return d


def avanzar(celdas=1):
    """Una celda por distancia (el sketch para con el frontal); la posicion sale de los mm recorridos.
    Antes, la camara: blanco en el camino -> lento; rumbo chueco -> lo corrige. Devuelve los ToF que saltaron (0 = ninguno)."""
    global pos
    v = mira()
    lento = v is not None and v["blanco"] >= BLANCO_MAX
    if lento:                            # blanco en el camino: lento; el frontal hace el doble check
        f = rpc("odo", 5)
        print(f"Camara: blanco adelante ({v['blanco']:.2f}), " + (f"el frontal lo confirma a {f} mm"
              if f < D_FRENTE_TOF + CELDA else "el frontal no ve nada (punto ciego?)") + ": voy lento")
    if v and v["ang"] is not None and abs(v["ang"]) >= ANG_MIN:
        print(f"Camara: rumbo chueco, corrijo {v['ang']:+.0f} grados")
        if rpc("ajustar", round(v["ang"])) == 2:
            esperar()
    if rpc("alinear", 45) == 2:          # con MPU: endereza al rumbo deseado antes de avanzar (hasta 45 grados)
        esperar()
        time.sleep(0.1)                  # ToF frescos
    if EXPERIMENTAL and v and v["abre"]:  # abertura en la celda siguiente: lento y voto debil de libre
        lento = True
        sig = celda(vecino(pos, rumbo))
        for rel in v["abre"]:
            h = (rumbo + rel) % 4
            sig[h] = max(-VOTO_MAX, sig[h] - 1)
        print("Camara: abertura adelante", ["izq" if r < 0 else "der" for r in v["abre"]])
    rpc("mover", CELDA * celdas, int(lento))
    esperar(True)
    mm, saltos = rpc("odo", 0), rpc("odo", 3)
    if rpc("odo", 12):                   # el acelerometro sintio un choque: el sketch ya retrocedio
        print(f"MPU: choque a los {mm} mm (golpe {rpc('odo', 15) / 1000:.2f} g); retrocedi")
        vuelve_al_carril()
    if rpc("centrar", CENTRA_F) == 2:    # a D_FRENTE + k celdas de la pared de enfrente: re-centra la celda
        esperar()
    vivo["mm"], vivo["saltos"] = mm, saltos
    n = round(mm / CELDA)
    for i in range(n):                   # por donde paso no hay pared, seguro
        if i:                            # pasillo: la celda intermedia tenia paredes (abrirse una lo habria parado)
            celda(pos)[(rumbo - 1) % 4] = celda(pos)[(rumbo + 1) % 4] = VOTO_MAX
            vistas.add(pos)
        sig = vecino(pos, rumbo)
        celda(pos)[rumbo] = celda(sig)[(rumbo + 2) % 4] = -VOTO_MAX
        pos = sig
    loc_mueve(n, rpc("odo", 5) < FRENTE_LIBRE)
    print(f"Avanzo {mm} mm -> {pos}" + (f", salto en ToF {saltos}" if saltos else ""))
    return saltos


def vuelve_al_carril():
    """Tras un choque (casi siempre una esquina contra una pared lateral): se aleja de la pared mas cercana.
    Gira 20 grados hacia el otro lado, avanza 50 mm (unos 17 mm de lado) y regresa al rumbo deseado. Con MPU.
    Sin pared cerca choco con un poste (punta de pared) que los ToF no ven: prueba 15 grados a un lado al azar."""
    izq, _, der = tof3(2)
    if min(izq, der) < LADO_CERCA:
        g = 20 if izq < der else -20     # pared a la izquierda: gira a la derecha (+)
        print(f"Carril: pared {'izquierda' if g > 0 else 'derecha'} a {min(izq, der)} mm, me alejo")
    else:
        g = random.choice((15, -15))
        print(f"Carril: choque sin pared cerca (poste), esquivo {'derecha' if g > 0 else 'izquierda'}")
    if rpc("ajustar", g) == 2:           # sin MPU ajustar gira en su lugar
        esperar()
    elif rpc("alinear", 45) == 2:
        esperar()
    time.sleep(0.1)                      # ToF frescos antes de avanzar
    rpc("mover", 50, 1)
    esperar(True)
    if rpc("ajustar", -g) == 2:
        esperar()
    elif rpc("alinear", 45) == 2:
        esperar()
    time.sleep(0.1)


def salidas(izq, frente, der):
    """Salidas libres, regla de la mano izquierda pura: izquierda, frente, derecha (-1 izq, 0 frente, 1 der);
    sin ninguna, media vuelta. Preferir siempre el mismo lado garantiza recorrer todo el muro conexo."""
    return [r for r, ok in ((-1, izq >= PARED), (0, frente >= FRENTE_LIBRE), (1, der >= PARED)) if ok] or [2]


# ---------- Mapa ----------
def vecino(c, h):
    return c[0] + DX[h], c[1] + DY[h]


def celda(c):
    return muros.setdefault(c, [0] * 4)


def anota(izq, frente, der):
    """Votos de pared de la celda actual: una lectura mala no borra lo que vieron las demas."""
    p = celda(pos)
    for rel, d, lim in ((-1, izq, PARED), (0, frente, FRENTE_LIBRE), (1, der, PARED)):
        h = (rumbo + rel) % 4
        p[h] = max(-VOTO_MAX, min(VOTO_MAX, p[h] + (1 if d < lim else -1)))


def libre(c, h):
    """Paso conocido: los votos de los 2 lados suman libre."""
    return muros.get(c, [0] * 4)[h] + muros.get(vecino(c, h), [0] * 4)[(h + 2) % 4] < 0


def ruta(desde, hasta):
    """Rumbos del camino mas corto por pasos conocidos (BFS), o None."""
    previo, cola = {desde: None}, [desde]
    for c in cola:
        if c == hasta:
            camino = []
            while previo[c]:
                c, h = previo[c]
                camino.append(h)
            return camino[::-1]
        for h in range(4):
            n = vecino(c, h)
            if n not in previo and (n in muros or n == hasta) and libre(c, h):
                previo[n] = (c, h)
                cola.append(n)
    return None


def guardar():
    escribe(ARCH_MAPA, {"muros": [[*c, *p] for c, p in muros.items()],
                        "colores": [[*c, k] for c, k in colores.items()], "meta": meta,
                        "vistas": [list(c) for c in vistas]})


def cargar():
    global meta
    d = lee(ARCH_MAPA)
    if not d:
        return
    muros.update({(x, y): [v or 0 for v in p] for x, y, *p in d["muros"]})
    colores.update({(x, y): k for x, y, k in d["colores"]})
    meta = tuple(d["meta"]) if d["meta"] else None
    vistas.update(tuple(c) for c in d.get("vistas", []))
    for k in colores.values():
        cuenta[k] += 1
    print(f"Mapa: {len(muros)} celdas, meta {meta}")


# ---------- Vision ----------
def abrir_camara():
    """Prueba solo los /dev/video que existen; avisa en el log solo si la lista cambia."""
    global cam, videos
    devs = sorted(int(d[10:]) for d in glob.glob("/dev/video*") if d[10:].isdigit())
    if devs != videos:
        videos = devs
        print("video:", devs, "(0 y 1 son internos: si no hay mas, la camara no esta conectada)")
    cam = None
    for i in devs:
        if i < CAM_ID:
            continue
        c = cv2.VideoCapture(i, cv2.CAP_V4L2)
        if c.isOpened() and c.read()[0]:
            print("Camara en /dev/video%d" % i)
            c.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
            c.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
            c.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cam = c
            break
        c.release()
    aplica_expo()
    return cam is not None


def foto():
    global ult_img
    with cam_lock:                       # la usan el robot y la pagina web
        if cam is None:
            return None
        for _ in range(3):
            cam.grab()
        ok, img = cam.read()
    if ok:
        ult_img = img
    return img if ok else None


def aplica_expo():
    """1. Exposicion fija: el umbral de blanco no cambia con la luz del lugar ni con la gente alrededor."""
    if cam is None:
        return
    if camcal["expo"] > 0:
        cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)        # V4L2: 1 manual, 3 automatica
        if cam.get(cv2.CAP_PROP_AUTO_EXPOSURE) != 1:
            cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # algunos drivers usan la escala vieja de OpenCV
        cam.set(cv2.CAP_PROP_EXPOSURE, camcal["expo"])
    else:
        cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
    if camcal.get("gain", -1) >= 0:
        cam.set(cv2.CAP_PROP_GAIN, camcal["gain"])
    # lo que la camara dice que quedo: si no cambia, el driver ignora el ajuste
    cam_leido.update(modo=cam.get(cv2.CAP_PROP_AUTO_EXPOSURE), expo=cam.get(cv2.CAP_PROP_EXPOSURE),
                     gain=cam.get(cv2.CAP_PROP_GAIN))
    print("Camara: exposicion", cam_leido, flush=True)


def contraste(g):
    """Estira el gris: el 2 % mas oscuro de la mitad de abajo pasa a 0 y el 2 % mas claro a 255.
    Con poca luz o exposicion baja, piso y pared quedan bien separados antes de Otsu."""
    lo, hi = np.percentile(g[g.shape[0] // 2:], (2, 98))
    if hi - lo < 25:                     # imagen casi uniforme (todo piso o todo pared): no inventa contraste
        return g
    return np.clip((g.astype(np.float32) - lo) * (255.0 / (hi - lo)), 0, 255).astype(np.uint8)


def umbral(g):
    """2. Umbral de blanco por Otsu en la mitad de abajo (piso negro y pared blanca son 2 grupos de gris)."""
    t, _ = cv2.threshold(g[g.shape[0] // 2:], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return min(max(t, UMBRAL_MIN), UMBRAL_MAX)


def bordes(b):
    """Bases de las paredes: en cada fila, desde el centro hacia cada lado, el primer blanco. [(y, xl, xr)]."""
    h, w = b.shape
    c, out = w // 2, []
    for y in range(int(ZONA_BORDES[0] * h), int(ZONA_BORDES[1] * h)):
        if b[y, c]:
            continue                     # pared enfrente en esta fila
        izq, der = np.flatnonzero(b[y, :c]), np.flatnonzero(b[y, c:])
        out.append((y, izq[-1] if len(izq) else None, c + der[0] if len(der) else None))
    return out


def recta(pts):
    """x = a*y + c por minimos cuadrados, sin los puntos que no caen en ella (tramo abierto, pared del fondo,
    reflejo). Empieza con la mitad mas cercana (abajo), la mas confiable. None si menos del 30 % forma la recta."""
    if len(pts) < 8:
        return None
    ys, xs = np.array(pts, float).T
    ok = ys >= np.median(ys)
    for _ in range(3):
        a, c = np.polyfit(ys[ok], xs[ok], 1)
        ok = np.abs(a * ys + c - xs) < 5
        if ok.sum() < max(8, 0.3 * len(ys)):
            return None
    return a, c


def angulo(bs):
    """3. Grados que hay que girar (derecha +) para quedar paralelo al pasillo, o None.
    Las bases de las 2 paredes convergen en el punto de fuga; su columna respecto a x0 da el rumbo."""
    li = recta([(y, x) for y, x, _ in bs if x is not None])
    ld = recta([(y, x) for y, _, x in bs if x is not None])
    if not li or not ld or li[0] >= 0 or ld[0] <= 0:
        return None, None
    y = (ld[1] - li[1]) / (li[0] - ld[0])
    xf = li[0] * y + li[1]
    ang = math.degrees(math.atan((xf - camcal["x0"]) * camcal["k"]))
    return (ang if abs(ang) <= ANG_MAX else None), (xf, y, li, ld)


def fila_pared(b, x):
    """Primera fila blanca desde abajo en la columna x (franja de 5 px): la base de la pared."""
    col = b[:, max(x - 2, 0):x + 3].mean(axis=1) > 0.5
    i = np.flatnonzero(col[::-1])
    return len(col) - 1 - int(i[0]) if len(i) else None


def mm_fila(y):
    """4. Profundidad de una fila de la imagen (mm desde el frontal) con la tabla calibrada; None fuera de ella."""
    f = sorted((int(k), v) for k, v in camcal["filas"].items())
    if len(f) < 2 or y is None or not f[0][0] <= y <= f[-1][0]:
        return None
    return round(float(np.interp(y, [k for k, _ in f], [v for _, v in f])))


def aberturas(bs, fuga):
    """5. Lados (-1 izq, 1 der) sin pared en la celda siguiente: en ese tramo casi ninguna fila tiene la base
    de la pared sobre la recta de esa pared (sin blanco, o el blanco es la pared del fondo del pasillo lateral)."""
    if not fuga:
        return []
    filas = [(y, xl, xr) for y, xl, xr in bs if (d := mm_fila(y)) is not None and SIG[0] <= d <= SIG[1]]
    if len(filas) < 5:
        return []
    out = []
    for rel, k, (a, c) in ((-1, 1, fuga[2]), (1, 2, fuga[3])):
        en = sum(f[k] is not None and abs(f[k] - (a * f[0] + c)) < 8 for f in filas)
        if en < 0.3 * len(filas):
            out.append(rel)
    return out


def vision(img):
    """Todo lo de la camara con una sola foto."""
    g = contraste(cv2.medianBlur(img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5))
    t = min(max(umbral(g) - camcal.get("sens", 0), UMBRAL_MIN // 2), UMBRAL_MAX)
    b = g >= t
    h, w = b.shape
    x0, y0, x1, y1 = ZONA_PASO
    bs = bordes(b)
    ang, fuga = angulo(bs)
    v = {"umbral": int(t), "blanco": float(b[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)].mean()),
         "ang": None if ang is None else round(ang, 1), "fuga": fuga, "b": b}
    if EXPERIMENTAL:
        v["virtual"] = [mm_fila(fila_pared(b, int(c * w))) for c in COLS]
        v["abre"] = aberturas(bs, fuga)
    return v


def mira():
    """Foto y vision antes de avanzar, o None sin camara."""
    img = foto() if cam is not None else None
    return vision(img) if img is not None else None


# ---------- Dashboard (http://<ip de la Q>:7000) ----------
def lectura():
    r, g, b, c = (rpc("raw", i) for i in range(4))
    s = r + g + b + 1
    return [r / s, g / s, b / s, c]


def clasifica(v):
    import math
    d = [(v[0] - f[0]) ** 2 + (v[1] - f[1]) ** 2 + (v[2] - f[2]) ** 2
         + 0.01 * math.log((v[3] + 1) / (f[3] + 1)) ** 2 for f in REFS]
    if v[3] < REFS[0][3] * BRILLO_MIN:
        return 0
    k = min(range(len(REFS)), key=d.__getitem__)
    return k if d[k] < 0.02 else 0


def enviar_refs():
    for i, f in enumerate(REFS):
        rpc("set_ref", i, round(f[0] * 1000), round(f[1] * 1000), round(f[2] * 1000), round(f[3]))


def ajuste(puntos):
    """Recta real = a * crudo + b por minimos cuadrados. 1 punto: solo desfase. Sin puntos: sin cambio."""
    if not puntos:
        return 1.0, 0.0
    xs, ys = [c for c in puntos.values()], [float(r) for r in puntos]
    n, mx, my = len(xs), sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if n > 1 and sxx else 1.0
    return a, my - a * mx


def enviar_tof():
    for i, n in enumerate(TOF_NOM):
        a, b = ajuste(tof_cal[n])
        rpc("set_tof", i, round(a * 1000), round(b * 10))


def api_tof_cal(s: int, mm: int):
    """Calibra el sensor s (0 izq, 1 frente, 2 der) con una pared a mm reales (la web manda 100): un solo punto,
    que reemplaza al anterior, y de ahi solo el desfase (real = crudo + b). mm = 0 borra su calibracion."""
    n = TOF_NOM[s]
    tof_cal[n].clear()
    if mm > 0:
        lect = []
        for _ in range(10):
            time.sleep(0.04)
            c = rpc("odo", 9 + s)
            if c < 2000:
                lect.append(c)
        if lect:
            tof_cal[n][str(mm)] = round(sum(lect) / len(lect), 1)
    enviar_tof()
    escribe(ARCH_TOF, tof_cal)
    print("ToF", n, tof_cal[n], "a=%.3f b=%.1f" % ajuste(tof_cal[n]))
    return estado_tof_cal()


def api_avance_prueba():
    """Avance de prueba de 100 mm por tiempo (sin medir con el frontal), para calibrar ms_celda."""
    if corriendo:
        return {"ok": False, "ms": ms_celda}
    ok = rpc("mover_t", 100) == 1
    print(f"Avance de prueba: 100 mm por tiempo con {ms_celda} ms por celda")
    return {"ok": ok, "ms": ms_celda}


def api_avance_cal(mm: int):
    """Lo que de verdad avanzo la prueba (mm, con regla): ajusta ms_celda en proporcion y lo guarda."""
    global ms_celda
    if mm > 0:
        ms_celda = max(200, min(2000, round(ms_celda * 100 / mm)))
        rpc("set_ms", ms_celda)
        escribe(ARCH_AVANCE, {"ms_celda": ms_celda})
        print(f"Avance: midio {mm} mm de 100 -> {ms_celda} ms por celda")
    return {"ok": mm > 0, "ms": ms_celda}


def estado_tof_cal():
    return {n: {"puntos": tof_cal[n], "a": round(ajuste(tof_cal[n])[0], 3), "b": round(ajuste(tof_cal[n])[1], 1)}
            for n in TOF_NOM}


def api_lectura():
    mapa = {"pos": pos, "celdas": len(muros), "meta": meta, "fase": fase_act, "corriendo": corriendo,
            "tiempo": round(time.monotonic() - t_ini, 1) if corriendo and t_ini else t_fin, "t_meta": t_meta,
            "log": log_col[-15:]}
    if corriendo:                        # sin Bridge: no le quita tiempo al robot
        v = vivo["v"]
        odo = {"falta": None, "frente": vivo["frente"], "paredes": 0, "mm": vivo["mm"], "saltos": vivo["saltos"], **mapa}
    else:
        v = vivo["v"] = lectura()
        odo = {"falta": rpc("odo", 1), "frente": rpc("odo", 5), "paredes": rpc("odo", 2), "mm": rpc("odo", 0),
               "saltos": rpc("odo", 3), **mapa}
    return limpio({"v": v, "color": COLORES[clasifica(v)], "colores": COLORES, "refs": REFS, "odo": odo})


def que_haria(izq, frente, der, mueve):
    """Simulacion para pruebas: que haria el robot con lo que leen los ToF ahora (no mueve nada)."""
    if frente < D_FRENTE_TOF - 5:         # = D_CERCA del sketch
        return "Retrocede: muy pegado a la pared de enfrente", 2
    if mueve and frente < PARED_F:
        return f"Frena: pared a {frente} mm, se detiene a {D_FRENTE_TOF} mm", 0
    rel = salidas(izq, frente, der)[0]
    return {0: "Sigue de frente 1 celda",
            1: "Gira 90° a la derecha y avanza 1 celda",
            -1: "Gira 90° a la izquierda y avanza 1 celda",
            2: "Media vuelta (180°) y avanza 1 celda"}[rel], rel


def api_tof():
    if corriendo:                        # ultima lectura de tof3 (la que uso para decidir)
        izq, frente, der, mueve, falta = vivo["izq"], vivo["frente"], vivo["der"], fase_act in ("GIRA", "AVANZA"), None
        crudos = None
    else:
        izq, frente, der = rpc("odo", 6), rpc("odo", 5), rpc("odo", 7)
        mueve, falta = bool(rpc("odo", 2) & 8), rpc("odo", 1)
        crudos = [rpc("odo", 9 + i) for i in range(3)]
    accion, rel = que_haria(izq, frente, der, mueve)
    return limpio({"izq": izq, "frente": frente, "der": der, "pared": PARED, "pared_f": PARED_F,
                   "falta": falta, "mueve": mueve, "accion": accion, "rel": rel, "fase": fase_act,
                   "crudos": crudos, "cal": estado_tof_cal()})


def api_guardar(i: int):
    m = [0, 0, 0, 0]
    for _ in range(5):
        m = [a + b / 5 for a, b in zip(m, lectura())]
        time.sleep(0.05)
    REFS[i] = [round(x, 3) for x in m[:3]] + [round(m[3])]
    enviar_refs()
    escribe(ARCH_COL, REFS)
    print("Color", COLORES[i], REFS[i])
    return api_lectura()


def api_foto():
    # en corrida reusa la ultima foto del robot: no le gana la camara
    img = (ult_img.copy() if ult_img is not None else None) if corriendo else (foto() if cam is not None else None)
    if img is None:
        return {"img": None, "exp": EXPERIMENTAL, "cal": camcal}
    v = vision(img)
    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    h, w = img.shape[:2]
    x0, y0, x1, y1 = ZONA_PASO               # rojo = ve blanco (pared) en el camino, verde = negro
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w) - 1, int(y1 * h) - 1),
                  (0, 0, 255) if v["blanco"] >= BLANCO_MAX else (0, 255, 0), 2)
    if v["fuga"]:                            # azul: bases de las paredes y punto de fuga
        xf, yf, li, ld = v["fuga"]
        for a, c in (li, ld):
            cv2.line(img, (int(a * h + c), h - 1), (int(xf), int(yf)), (255, 128, 0), 2)
        cv2.circle(img, (int(xf), int(yf)), 5, (255, 128, 0), -1)
    cv2.line(img, (int(camcal["x0"]), 0), (int(camcal["x0"]), h // 3), (255, 255, 255), 1)
    if EXPERIMENTAL:                         # amarillo: base de la pared en cada columna
        for c in COLS:
            y = fila_pared(v["b"], int(c * w))
            if y is not None:
                cv2.circle(img, (int(c * w), y), 4, (0, 255, 255), -1)
    img = cv2.resize(img, (160, 120))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    return limpio({"img": base64.b64encode(buf).decode(), "blanco": round(v["blanco"], 2), "umbral": v["umbral"],
                   "ang": v["ang"], "virtual": v.get("virtual"), "abre": v.get("abre"), "exp": EXPERIMENTAL,
                   "cal": camcal, "leido": cam_leido})


def guarda_cam():
    escribe(ARCH_CAM, camcal)
    return api_foto()


def api_cam_expo(v: int, g: int = -1):
    """Exposicion fija (0 = automatica) y ganancia (-1 = no la toca)."""
    camcal["expo"] = max(v, 0)
    camcal["gain"] = max(g, -1)
    with cam_lock:
        aplica_expo()
    return guarda_cam()


def fuga_ahora():
    img = foto() if cam is not None else None
    return vision(img)["fuga"] if img is not None else None


def api_cam_sens(v: int):
    """Sensibilidad al blanco: baja el umbral de Otsu v niveles de gris (0 = sin cambio; mas = ve blanco antes)."""
    camcal["sens"] = max(min(v, 80), -80)
    return guarda_cam()


def api_cam_cero():
    """Robot derecho en un pasillo: el punto de fuga que ve ahora es 'derecho'."""
    f = fuga_ahora()
    if f:
        camcal["x0"] = round(f[0], 1)
    return guarda_cam()


def api_cam_giro(g: int):
    """Robot girado g grados a la derecha del pasillo: fija los radianes por pixel."""
    f = fuga_ahora()
    if f and g and abs(camcal["x0"] - f[0]) > 3:
        k = math.tan(math.radians(g)) / (camcal["x0"] - f[0])
        if k > 0:
            camcal["k"] = round(k, 5)
    return guarda_cam()


def api_cam_dist(borrar: int = 0):
    """Experimental: con una pared enfrente, la fila de su base en la columna central vale lo que lee el frontal."""
    if borrar:
        camcal["filas"] = {}
        return guarda_cam()
    img = foto() if cam is not None else None
    y = fila_pared(vision(img)["b"], ANCHO // 2) if img is not None else None
    f = sorted(rpc("odo", 5) for _ in range(5))[2]
    if y is not None and f < 2000:
        camcal["filas"][str(y)] = f
        print(f"Camara: fila {y} = {f} mm")
    return guarda_cam()


def limpio(x):
    """Pasa tipos de numpy a tipos de Python para que FastAPI los pueda mandar."""
    return json.loads(json.dumps(x, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


paso("creando WebUI")
ui = WebUI()
ui.expose_api("GET", "/api/lectura", api_lectura)
ui.expose_api("GET", "/api/guardar", api_guardar)
ui.expose_api("GET", "/api/foto", api_foto)
ui.expose_api("GET", "/api/tof", api_tof)
ui.expose_api("GET", "/api/tof_cal", api_tof_cal)
ui.expose_api("GET", "/api/avance_prueba", api_avance_prueba)
ui.expose_api("GET", "/api/avance_cal", api_avance_cal)
ui.expose_api("GET", "/api/cam_expo", api_cam_expo)
ui.expose_api("GET", "/api/cam_cero", api_cam_cero)
ui.expose_api("GET", "/api/cam_sens", api_cam_sens)
ui.expose_api("GET", "/api/cam_giro", api_cam_giro)
ui.expose_api("GET", "/api/cam_dist", api_cam_dist)


# ---------- Estrategia ----------
def ubica(izq, frente, der):
    """Arranca en una esquina: un lado libre en la salida, o haberse movido en un eje, apunta hacia adentro."""
    if pos == (0, 0):
        for rel, d, lim in ((-1, izq, PARED), (0, frente, FRENTE_LIBRE), (1, der, PARED)):
            h = (rumbo + rel) % 4
            if d >= lim:
                signo[0] = signo[0] or DX[h]
                signo[1] = signo[1] or DY[h]
    for i in (0, 1):
        if pos[i] and not signo[i]:
            signo[i] = 1 if pos[i] > 0 else -1


def al_centro(c):
    """Celdas (sin paredes) de c al centro; un eje sin direccion conocida no cuenta."""
    return sum(abs(CENTRO * s - v) for v, s in zip(c, signo) if s)


def frontera():
    """Rumbo (0-3) del primer paso hacia una celda vista con un lado libre hacia una celda sin ver (BFS por pasos
    conocidos); entre ellas, la de menos pasos + distancia de la celda nueva al centro. None si ya no queda nada."""
    previo, dist, cola, mejor = {pos: None}, {pos: 0}, [pos], None
    for c in cola:
        for h in range(4):
            n = vecino(c, h)
            if c != pos and muros.get(c, [0] * 4)[h] < 0 and n not in vistas:
                costo = dist[c] + al_centro(n)
                if mejor is None or costo < mejor[0]:
                    mejor = (costo, c)
            if n not in previo and n in vistas and libre(c, h):
                previo[n], dist[n] = (c, h), dist[c] + 1
                cola.append(n)
    if mejor is None:
        return None
    c = mejor[1]
    while previo[c][0] != pos:
        c = previo[c][0]
    return previo[c][1]


# ---------- Pista conocida (fotos del 12-nov) y autolocalizacion ----------
# 11 x 11 celdas, vista desde la foto 3: x a la derecha, y hacia abajo (0 = lado opuesto al fotografo).
# PISTA_H[y] = columnas x con pared horizontal en la linea y (de x a x+1); PISTA_V[x] = filas y con pared vertical.
# Los muros exteriores van aparte. Si cambian la pista, se corrige aqui (y uno_q/sim lo usa igual).
PISTA_H = {1: [1, 3, 4, 5, 7, 10], 2: [2, 3, 4, 7, 8, 9, 10], 3: [3, 4, 5, 8, 9, 10], 4: [1, 2, 5, 9, 10],
           5: [0, 1, 5, 6, 10], 6: [0, 4, 9], 7: [1, 3], 8: [1, 5, 7], 9: [4, 5, 6, 10], 10: [4, 6, 8, 9]}
PISTA_V = {1: [1, 3, 6, 8, 10], 2: [0, 1, 2, 6, 9, 10], 3: [0, 4, 5, 7, 9, 10], 4: [4, 5, 7, 8], 5: [2, 5, 6, 7, 10],
           6: [1, 3], 7: [1, 3, 4, 5, 8], 8: [3, 5, 6, 7, 9], 9: [0, 4, 6, 8, 9], 10: [5, 6, 8, 9]}
PISTA_META = (6, 6)                      # el amarillo
PN = 11
PDX, PDY = [0, 1, 0, -1], [-1, 0, 1, 0]  # rumbos de la pista: 0 arriba de la foto, 1 derecha, 2 abajo, 3 izquierda


def pista_celdas():
    """{(x, y): [arriba, der, abajo, izq]} con True = pared."""
    W = {(x, y): [y == 0, x == PN - 1, y == PN - 1, x == 0] for x in range(PN) for y in range(PN)}
    for y, xs in PISTA_H.items():
        for x in xs:
            if y > 0: W[(x, y - 1)][2] = True
            if y < PN: W[(x, y)][0] = True
    for x, ys in PISTA_V.items():
        for y in ys:
            if x > 0: W[(x - 1, y)][1] = True
            if x < PN: W[(x, y)][3] = True
    return W


pmuros = {}                              # la pista como la cree ahora (se corrige si algo cambio)
creencia = {}                            # (celda, h0) -> probabilidad; h0 = rumbo de la pista cuando rumbo = 0
cambios = {}                             # (celda, lado) -> votos de que la pista cambio ahi
perdidas = 0                             # veces que se perdio en esta corrida
malas = 0                                # lecturas seguidas que no cuadran con ninguna hipotesis
recuadra = False                         # se perdio: antes de seguir se cuadra con las paredes


def loc_inicia():
    """Sale de una esquina, viendo hacia cualquier lado: 16 hipotesis; las lecturas descartan las malas."""
    global malas, perdidas
    malas = perdidas = 0
    pmuros.clear()
    pmuros.update(pista_celdas())
    cambios.clear()
    creencia.clear()
    for c in ((0, 0), (PN - 1, 0), (0, PN - 1), (PN - 1, PN - 1)):
        for h0 in range(4):
            creencia[(c, h0)] = 1 / 16


def tramo(c, h, tope=6):
    """Celdas libres seguidas desde c hacia h en la pista (hasta tope)."""
    n = 0
    while n < tope and not pmuros[c][h]:
        c = (c[0] + PDX[h], c[1] + PDY[h])
        n += 1
    return n


def leidas(lect):
    """Celdas libres que ven los ToF a izq, frente, der (None = mas de ~5: no ve nada)."""
    out = []
    for d, base in zip(lect, (D_LADO_TOF, D_FRENTE_TOF, D_LADO_TOF)):
        out.append(None if d >= 1000 else max(0, round((d - base) / CELDA)))
    return out


def loc_observa(lect):
    """Bayes: cada hipotesis pesa segun cuanto se parecen las celdas libres que ven los ToF a las de la pista."""
    if not creencia:
        return
    obs = leidas(lect)
    global malas
    tot = 0
    for (c, h0), p in creencia.items():
        for rel, o in zip((-1, 0, 1), obs):
            m = tramo(c, (h0 + rumbo + rel) % 4)
            if o is None:
                p *= 0.7 if m >= 5 else 0.2 if m == 4 else 0.03
            else:
                m, o = min(m, 5), min(o, 5)          # el cono (~25 grados) ve puntas de pared antes: ve de menos, casi nunca de mas
                p *= 0.7 if m == o else 0.25 if 0 < o < m else 0.1 if o == m + 1 else 0.02
        creencia[(c, h0)] = p
        tot += p
    malas = malas + 1 if tot < MALA else 0   # lo que ve no cuadra con ninguna hipotesis
    if malas >= 2:                       # perdido: se vuelve a ubicar en toda la pista, con los 4 rumbos
        global perdidas, recuadra
        perdidas += 1
        recuadra = True
        malas = 0
        if perdidas >= PERDIDAS_MAX:     # no es esta pista (la cambiaron): sigue solo con la brujula
            print("Pista: no cuadra con el mapa, sigo con la brujula")
            creencia.clear()
            return
        print("Pista: perdido, me vuelvo a ubicar en toda la pista")
        creencia.clear()
        creencia.update({((x, y), h0): 1 / (4 * PN * PN) for x in range(PN) for y in range(PN) for h0 in range(4)})
        return loc_observa(lect)
    for k in creencia:
        creencia[k] = creencia[k] / tot if tot else 1 / len(creencia)
    (c, h0), pm = max(creencia.items(), key=lambda kv: kv[1])
    if pm >= CONFIANZA:                  # seguro de donde esta: lo que no cuadra es que la pista cambio
        for rel, o in zip((-1, 0, 1), obs):
            h = (h0 + rumbo + rel) % 4
            n = (c[0] + PDX[h], c[1] + PDY[h])
            if o is not None and (o == 0) != pmuros[c][h] and n in pmuros:   # los muros exteriores no cambian
                k = (c, h)
                cambios[k] = cambios.get(k, 0) + 1
                if cambios[k] >= 2:
                    pmuros[c][h] = pmuros[n][(h + 2) % 4] = o == 0
                    print(f"Pista: cambio en {c} hacia {'NESO'[h]}: ahora {'pared' if o == 0 else 'libre'}")
                    del cambios[k]


def loc_mueve(k, pared=False):
    """Avanzo ~k celdas (odometria): cada hipotesis avanza k (o k +- 1) por donde la pista deja pasar.
    pared: termino con pared enfrente, asi que llego al final del pasillo aunque los mm digan menos
    (el frontal ve puntas de pared antes y corta el avance)."""
    if not creencia:
        return
    k = max(k, 0)                        # un avance negativo (retrocedio al centrarse) vaciaba la creencia: brujula para siempre
    nueva = {}
    for (c, h0), p in creencia.items():
        h = (h0 + rumbo) % 4
        run = tramo(c, h, k + 4)
        if pared:
            d = (c[0] + PDX[h] * run, c[1] + PDY[h] * run)
            nueva[(d, h0)] = nueva.get((d, h0), 0) + p * (0.7 if abs(run - k) <= 1 else 0.2 if run - k <= 3 else 0.02)
            continue
        for kk, pk in ((k, 0.7), (k - 1, 0.15), (k + 1, 0.15)):
            if kk < 0:
                continue
            kk = min(kk, run)
            d = (c[0] + PDX[h] * kk, c[1] + PDY[h] * kk)
            nueva[(d, h0)] = nueva.get((d, h0), 0) + p * pk
    tot = sum(nueva.values())
    creencia.clear()
    creencia.update({k2: v / tot for k2, v in nueva.items() if v / tot > 1e-4})


def por_pista(izq, frente, der):
    """Con la ubicacion segura: primer paso del camino mas corto (en la pista como la cree) al amarillo.
    Sin certeza, o si los ToF dicen pared donde la pista dice paso, decide la brujula."""
    if not creencia:
        return None
    (c, h0), pm = max(creencia.items(), key=lambda kv: kv[1])
    if pm < CONFIANZA:
        return None
    previo, cola = {c: None}, [c]
    for a in cola:
        if a == PISTA_META:
            break
        for h in range(4):
            n = (a[0] + PDX[h], a[1] + PDY[h])
            if not pmuros[a][h] and n not in previo:
                previo[n] = (a, h)
                cola.append(n)
    if PISTA_META not in previo or PISTA_META == c:
        return None
    a = PISTA_META
    while previo[a][0] != c:
        a = previo[a][0]
    rel = {0: 0, 1: 1, 2: 2, 3: -1}[(previo[a][1] - h0 - rumbo) % 4]
    if rel == 2 or rel in salidas(izq, frente, der):
        return rel
    return None


def brujula(izq, frente, der):
    """Sin mapa de paredes: entre las salidas libres que ven los ToF ahora, la que apunta mas al centro
    (rumbo del giroscopio + posicion aproximada), menos un castigo por cada vez que ya la tomo desde esa celda,
    mas algo de azar. Una posicion desfasada 1-2 celdas casi no cambia hacia donde queda el centro.
    En simulacion (200 laberintos) iguala al mapa con buena odometria y le gana 10-22 puntos con mala."""
    libres = [r for r in salidas(izq, frente, der) if r != 2]
    if not libres:
        return 2
    cx, cy = ((CENTRO * s - p) if s else 0 for p, s in zip(pos, signo))
    n = math.hypot(cx, cy) or 1
    def nota(r):
        h = (rumbo + r) % 4
        return (DX[h] * cx + DY[h] * cy) / n - CASTIGO * usos.get((pos, h), 0) + random.gauss(0, RUIDO)
    r = max(libres, key=nota)
    h = (rumbo + r) % 4
    usos[(pos, h)] = usos.get((pos, h), 0) + 1
    return r


def decidir(izq, frente, der, abre=()):
    """Exploracion completa hacia el centro (tipo Tremaux / DFS):
    1. Salidas libres hacia celdas sin ver: la que mas acerca al centro (empate: izquierda, frente, derecha).
    2. Si todas llevan a celdas ya vistas: va por el camino conocido mas corto a la celda con lados sin explorar.
    Asi entra a una meta en una isla (al centro, con pocas entradas), que la mano izquierda sola rodea sin entrar."""
    if izq >= FUERA and der >= FUERA:        # nada a 2 m por ningun lado: salio del laberinto
        p = celda(pos)
        for r in (-1, 0, 1):
            p[(rumbo + r) % 4] = VOTO_MAX
        print("Fuera del laberinto: regreso")
        return 2
    if ESTRATEGIA == "pista":
        loc_observa((izq, frente, der))
        rel = por_pista(izq, frente, der)
        return brujula(izq, frente, der) if rel is None else rel
    if ESTRATEGIA == "brujula":
        return brujula(izq, frente, der)
    # un paso por donde ya paso cuenta como libre aunque un ToF diga pared (robot descentrado o chueco):
    # sin esto se quedaba yendo y viniendo entre 2 celdas (paso en pista)
    libres = set(salidas(izq, frente, der)) | {r for r in (-1, 0, 1) if celda(pos)[(rumbo + r) % 4] <= RECORRIDO}
    ops = [r for r in (-1, 0, 1) if r in libres] or [2]
    nuevas = [r for r in ops if r != 2 and vecino(pos, (rumbo + r) % 4) not in vistas]
    if nuevas:
        tomar = [r for r in nuevas if r in abre]   # se acaba de abrir a un lado (paro ahi por eso): se va por ahi
        return min(tomar or nuevas, key=lambda r: al_centro(vecino(pos, (rumbo + r) % 4)))
    h = frontera()
    if h is not None:
        rel = {0: 0, 1: 1, 2: 2, 3: -1}[(h - rumbo) % 4]
        if rel in ops or rel == 2:           # atras siempre esta libre: de ahi vino
            return rel
    return ops[0]


def buscar_color():
    """Maquina de estados: SENSA (3 ToF, 3 lecturas; ESCANEA con 5 tras un salto) -> DECIDE -> GIRA -> AVANZA.
    Todo se decide quieto. El color se revisa todo el tiempo; amarillo o un toque a D2 la terminan."""
    global encontrado, recuadra
    encontrado = False
    estado(1)
    f, abre = "SENSA", []
    while not encontrado:
        if detener():
            return False
        fase(f)
        if f in ("SENSA", "ESCANEA"):
            lect = tof3(5 if f == "ESCANEA" else 3)
            anota(*lect)
            ubica(*lect)
            vistas.add(pos)
            f = "DECIDE"
        elif f == "DECIDE":
            rel = decidir(*lect, abre=abre)
            if recuadra:                 # se acaba de perder: recupera el frente y vuelve a leer antes de moverse
                recuadra = False
                cuadrar()
                f = "SENSA"
                continue
            print("ToF izq {} frente {} der {} en {}:".format(*lect, pos),
                  {1: "derecha", 0: "frente", -1: "izquierda", 2: "media vuelta"}[rel])
            f = "GIRA"
        elif f == "GIRA":
            girar(rel)
            f = "AVANZA"
        else:
            # pasillo (pared a ambos lados y sin girar): varias celdas de un tiron; para si se abre un lateral
            n = PASILLO if rel == 0 and lect[0] < PARED and lect[2] < PARED else 1
            saltos = avanzar(n)
            abre = [r for r, b in ((-1, 1), (1, 4)) if saltos & b]   # bits de odo(3): 1 izq, 2 frente, 4 der
            f = "ESCANEA" if saltos else "SENSA"
    return True


def seguir_ruta():
    """Con la meta en el mapa va por el camino mas corto conocido. False si algo no cuadra (sigue explorando)."""
    camino = ruta(pos, meta)
    if camino is None:
        return False
    estado(3)
    print(f"Ruta a {meta}: {len(camino)} celdas")
    for h in camino:
        if detener():
            return False
        fase("GIRA")
        girar({0: 0, 1: 1, 2: 2, 3: -1}[(h - rumbo) % 4])
        esperado = vecino(pos, h)
        fase("AVANZA")
        avanzar()
        if encontrado:
            return True
        if pos != esperado:
            print(f"Ruta: quede en {pos} y esperaba {esperado}, sigo explorando")
            return False
    return pos == meta


# ---------- Principal ----------
def borrar():
    global meta
    muros.clear()
    colores.clear()
    vistas.clear()
    meta = None
    if os.path.exists(ARCH_MAPA):
        os.remove(ARCH_MAPA)
    for c in range(1, len(COLORES)):
        cuenta[c] = 0
        rpc("set_cuenta", c, 0)
    estado(5)
    print("Mapa y conteo borrados")


def iniciar():
    global REFS
    paso("archivos en /app: " + str(sorted(os.listdir("/app"))) + " datos: " + str(sorted(os.listdir(DATOS))))
    REFS = lee(ARCH_COL) or lee("/app/colores.json") or REFS   # tambien los de la version anterior
    paso("colores leidos; mandando al STM32 (si se queda aqui, el sketch no responde por Bridge)")
    enviar_refs()
    paso("colores enviados")
    for n, p in (lee(ARCH_TOF) or {}).items():
        if n in tof_cal:
            tof_cal[n].update(p)
    enviar_tof()
    paso("ToF enviados")
    global ms_celda
    ms_celda = (lee(ARCH_AVANCE) or {}).get("ms_celda", ms_celda)
    rpc("set_ms", ms_celda)
    camcal.update(lee(ARCH_CAM) or {})
    cargar()
    for c in range(1, len(COLORES)):
        rpc("set_cuenta", c, cuenta[c])
    paso("mapa cargado; buscando camara")
    if USAR_CAM and abrir_camara():
        estado(0)
    else:
        print("Sin camara: la sigo buscando")
        estado(6)
    if USAR_CAM:                         # en segundo plano: no frena el arranque de la app
        threading.Thread(target=vigilar_cam, daemon=True).start()
    paso("iniciar() listo")


def vigilar_cam():
    """Cada 2 s: si no hay camara la busca; si la hay, revisa que siga conectada."""
    global cam
    while True:
        time.sleep(2)
        with cam_lock:
            if cam is None:
                if abrir_camara():
                    print("Camara encontrada")
                    estado(0)
            elif not cam.grab():
                print("Camara desconectada: la sigo buscando")
                cam.release()
                cam = None
                estado(6)


def detener():
    """Toque a D2 o "Detener" en la web durante una corrida."""
    global pedido
    if rpc("arranque") or pedido == "alto":
        pedido = None
        print("Detenido con el boton o la web")
        return True
    if rpc("odo", 14):                   # el MPU vio que lo levantaron: la posicion ya no vale
        print("MPU: me levantaron, detengo la corrida")
        return True
    return False


def api_control(a: str):
    """Web: corre (como un toque corto a D2), alto (lo detiene) o borra (como sostener D2: mapa y conteo)."""
    global pedido
    if a in ("corre", "alto", "borra"):
        pedido = a
    return {"corriendo": corriendo, "pedido": pedido}


ui.expose_api("GET", "/api/control", api_control)


def loop():
    global pedido
    a = rpc("arranque")
    p, pedido = pedido, None
    if a == 2 or p == "borra":
        borrar()
        return
    if not a and p != "corre":
        time.sleep(0.05)
        return
    global pos, rumbo, encontrado, corriendo, t_ini, t_meta, t_fin
    pos, rumbo, encontrado = (0, 0), 0, False   # cada corrida empieza en la misma celda viendo al mismo lado
    signo[:] = [0, 0]                    # la esquina de salida puede cambiar
    usos.clear()
    loc_inicia()
    sys.stdout.nuevo("corrida")
    t = t_ini = time.monotonic()
    t_meta = t_fin = None
    log_col.clear()
    corriendo = True
    try:
        ok = (meta is not None and seguir_ruta()) or buscar_color()
    finally:
        corriendo = False
        fase("")
    t_fin = round(time.monotonic() - t, 1)
    guardar()
    estado(4 if ok else 0)
    print(f"Corrida: {t_fin} s" + (f", amarillo a los {t_meta} s" if t_meta is not None else ", sin amarillo") +
          f", marcas {cuenta[1:]}")


try:
    iniciar()
    paso("App.run")
    App.run(user_loop=loop)
except SystemExit as e:                  # App Lab la detiene (143 = SIGTERM): no es un error
    print(f"App detenida (codigo {e.code})", flush=True)
    raise
except BaseException:
    print("ERROR al arrancar:", flush=True)
    traceback.print_exc()
    sys.stdout.flush()
    raise
