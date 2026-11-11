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
ARCH_COL = DATOS + "/colores.json"
ARCH_MAPA = DATOS + "/mapa.json"
ARCH_TOF = DATOS + "/tof.json"
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
PARED = 120                              # mm: lateral con esto o mas = libre
PARED_F = 55                             # mm reales (frontal calibrado): menos de esto = pared (= PARED_F del sketch)
FRENTE_LIBRE = 130                       # mm reales: a la mitad entre pared en su celda (~35-45) y en la siguiente (~215-225)
D_FRENTE_TOF = 35                        # mm reales donde se detiene el sketch con pared enfrente (= D_FRENTE)
FUERA = 2000                             # mm: los 2 laterales sin nada a esta distancia = salio del laberinto
RECORRIDO = -3                           # voto de un paso por donde ya paso (-5) con hasta 2 lecturas en contra
VOTO_MAX = 5                             # cada lectura vota pared (+1) o libre (-1); tope para que el mapa se corrija
Y_COLOR = 36                             # mm del eje al sensor de color (adelante)

# ---------- Camara (OV9281 monocromatica, obturador global): asistencia, nunca decide sola ----------
CAM_ID = 2                               # /dev/video0 y video1 son internos de la placa: nunca son la camara
USAR_CAM = True
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
vistas = set()                           # celdas donde el robot ya leyo sus 3 ToF (se guarda con el mapa)
colores = {}
meta = None
# Para la pagina web: durante una corrida lee esto (lo actualiza el robot) en vez de pedirle al Bridge
corriendo = False
t_ini = None                             # inicio de la corrida (time.time())
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
    t = round(time.time() - t_ini, 1) if t_ini else 0
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
        rel += verifica_giro()
        time.sleep(0.1)                  # ToF frescos: con la lectura de antes del giro el sketch cree que tiene
                                         # la pared enfrente y avanza 0 mm (paso en pista)
    rumbo = (rumbo + rel) % 4


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


def avanzar():
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
    rpc("mover", CELDA, int(lento))
    esperar(True)
    mm, saltos = rpc("odo", 0), rpc("odo", 3)
    if rpc("odo", 12):                   # el acelerometro sintio un choque: el sketch ya retrocedio
        print(f"MPU: choque a los {mm} mm (golpe {rpc('odo', 15) / 1000:.2f} g); retrocedi y vuelvo a leer")
    vivo["mm"], vivo["saltos"] = mm, saltos
    n = round(mm / CELDA)
    for _ in range(n):                   # por donde paso no hay pared, seguro
        sig = vecino(pos, rumbo)
        celda(pos)[rumbo] = celda(sig)[(rumbo + 2) % 4] = -VOTO_MAX
        pos = sig
    print(f"Avanzo {mm} mm -> {pos}" + (f", salto en ToF {saltos}" if saltos else ""))
    return saltos


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


def estado_tof_cal():
    return {n: {"puntos": tof_cal[n], "a": round(ajuste(tof_cal[n])[0], 3), "b": round(ajuste(tof_cal[n])[1], 1)}
            for n in TOF_NOM}


def api_lectura():
    mapa = {"pos": pos, "celdas": len(muros), "meta": meta, "fase": fase_act, "corriendo": corriendo,
            "tiempo": round(time.time() - t_ini, 1) if corriendo and t_ini else t_fin, "t_meta": t_meta,
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
ui.expose_api("GET", "/api/cam_expo", api_cam_expo)
ui.expose_api("GET", "/api/cam_cero", api_cam_cero)
ui.expose_api("GET", "/api/cam_sens", api_cam_sens)
ui.expose_api("GET", "/api/cam_giro", api_cam_giro)
ui.expose_api("GET", "/api/cam_dist", api_cam_dist)


# ---------- Estrategia ----------
def frontera():
    """Rumbo (0-3) del primer paso hacia la celda vista mas cercana que tiene un lado libre hacia una celda
    sin ver (BFS por pasos conocidos), o None si ya no queda nada por explorar."""
    previo, cola = {pos: None}, [pos]
    for c in cola:
        if c != pos and any(muros.get(c, [0] * 4)[h] < 0 and vecino(c, h) not in vistas for h in range(4)):
            while previo[c][0] != pos:
                c = previo[c][0]
            return previo[c][1]
        for h in range(4):
            n = vecino(c, h)
            if n not in previo and n in vistas and libre(c, h):
                previo[n] = (c, h)
                cola.append(n)
    return None


def decidir(izq, frente, der):
    """Exploracion completa con mano izquierda (tipo Tremaux / DFS):
    1. Salidas libres hacia celdas sin ver: la primera en orden izquierda, frente, derecha.
    2. Si todas llevan a celdas ya vistas: va por el camino conocido mas corto a la celda con lados sin explorar.
    Asi entra a una meta en una isla (al centro, con pocas entradas), que la mano izquierda sola rodea sin entrar."""
    if izq >= FUERA and der >= FUERA:        # nada a 2 m por ningun lado: salio del laberinto
        p = celda(pos)
        for r in (-1, 0, 1):
            p[(rumbo + r) % 4] = VOTO_MAX
        print("Fuera del laberinto: regreso")
        return 2
    # un paso por donde ya paso cuenta como libre aunque un ToF diga pared (robot descentrado o chueco):
    # sin esto se quedaba yendo y viniendo entre 2 celdas (paso en pista)
    libres = set(salidas(izq, frente, der)) | {r for r in (-1, 0, 1) if celda(pos)[(rumbo + r) % 4] <= RECORRIDO}
    ops = [r for r in (-1, 0, 1) if r in libres] or [2]
    nuevas = [r for r in ops if r != 2 and vecino(pos, (rumbo + r) % 4) not in vistas]
    if nuevas:
        return nuevas[0]
    h = frontera()
    if h is not None:
        rel = {0: 0, 1: 1, 2: 2, 3: -1}[(h - rumbo) % 4]
        if rel in ops or rel == 2:           # atras siempre esta libre: de ahi vino
            return rel
    return ops[0]


def buscar_color():
    """Maquina de estados: SENSA (3 ToF, 3 lecturas; ESCANEA con 5 tras un salto) -> DECIDE -> GIRA -> AVANZA.
    Todo se decide quieto. El color se revisa todo el tiempo; amarillo o un toque a D2 la terminan."""
    global encontrado
    encontrado = False
    estado(1)
    f = "SENSA"
    while not encontrado:
        if detener():
            return False
        fase(f)
        if f in ("SENSA", "ESCANEA"):
            lect = tof3(5 if f == "ESCANEA" else 3)
            anota(*lect)
            vistas.add(pos)
            f = "DECIDE"
        elif f == "DECIDE":
            rel = decidir(*lect)
            print("ToF izq {} frente {} der {} en {}:".format(*lect, pos),
                  {1: "derecha", 0: "frente", -1: "izquierda", 2: "media vuelta"}[rel])
            f = "GIRA"
        elif f == "GIRA":
            girar(rel)
            f = "AVANZA"
        else:
            saltos = avanzar()
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
    t = t_ini = time.time()
    t_meta = t_fin = None
    log_col.clear()
    corriendo = True
    try:
        ok = (meta is not None and seguir_ruta()) or buscar_color()
    finally:
        corriendo = False
        fase("")
    t_fin = round(time.time() - t, 1)
    guardar()
    estado(4 if ok else 0)
    print(f"Corrida: {t_fin} s" + (f", amarillo a los {t_meta} s" if t_meta is not None else ", sin amarillo") +
          f", marcas {cuenta[1:]}")


try:
    iniciar()
    paso("App.run")
    App.run(user_loop=loop)
except BaseException:
    print("ERROR al arrancar:", flush=True)
    traceback.print_exc()
    sys.stdout.flush()
    raise
