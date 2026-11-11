from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
import cv2
import json
import os
import threading
import time
import math
import heapq
import base64

print("Python OK, cv2", cv2.__version__)

# ---------- Laberinto ----------
N = 11                                   # 11 x 11 celdas de 18 cm
INICIO = (0, 0)
RUMBO_INI = 0                            # 0=N 1=E 2=S 3=O
# centro: 1 celda si N es impar, las 4 del centro si es par
META = {(N // 2, N // 2)} if N % 2 else {(N // 2 - 1 + i, N // 2 - 1 + j) for i in (0, 1) for j in (0, 1)}
COLORES = ["PISO", "ROJO", "VERDE", "AZUL", "AMAR"]
DATOS = "/app/datos"                     # en una subcarpeta: archivos en la raiz de la app confunden a App Lab
os.makedirs(DATOS, exist_ok=True)
ARCHIVO = DATOS + "/mapa.json"
ARCH_COL = DATOS + "/colores.json"
ARCH_MODO = DATOS + "/modo.json"
modo = "tonto"                           # solo se usa el modo tonto: sigue la pared con los ToF, sin mapa
# r, g, b normalizados y brillo c; los mismos de refs[] del sketch
REFS = [[0.282, 0.379, 0.333, 153], [0.602, 0.208, 0.188, 581], [0.155, 0.535, 0.309, 636],
        [0.16, 0.329, 0.508, 354], [0.409, 0.449, 0.142, 1836]]

DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
BIT = [1, 2, 4, 8]

# ---------- Camara ----------
# Los VL53L0X leen las paredes de la celda actual. La camara mira la celda
# siguiente y adelanta sus paredes al mapa como "tentativas".
CAM_ID = 0
USAR_CAM = True
ANCHO, ALTO = 320, 240
# La camara ve por encima de las paredes: cada region mira una pared de una celda adelante.
# Clave "adelante,lado,pared": adelante = celdas al frente (1 = la siguiente), lado = -1 izq / 0 / 1 der,
# pared = F (fondo), I (izquierda), D (derecha) de esa celda. Valor = (x0, y0, x1, y1) en fraccion de la imagen.
# Ajustar viendo la camara en el panel web (rojo = ve pared, verde = libre).
ROI = {
    "1,0,F": (0.35, 0.05, 0.65, 0.25),
    "1,0,I": (0.05, 0.25, 0.25, 0.55),
    "1,0,D": (0.75, 0.25, 0.95, 0.55),
    "2,0,F": (0.42, 0.00, 0.58, 0.06),
    "2,0,I": (0.25, 0.05, 0.35, 0.22),
    "2,0,D": (0.65, 0.05, 0.75, 0.22),
}
REL = {"F": 0, "I": -1, "D": 1}
# Geometria de la camara (chasis/chasis.scad): lente a CAM_H del piso, CAM_Y adelante del eje, inclinada CAM_INCL
CAM_H, CAM_Y, CAM_INCL, CAM_FOV_V, CAM_FOV_H = 162, 32, 25, 75, 100
# Puntos ciegos de los VL53L0X (CAD: frontal en (0, 54) mirando al frente, laterales en (+-43, 40) mirando a los
# lados, cono de ~25 grados): las diagonales de enfrente no las ve nadie. La camara revisa ahi el piso por donde
# va a pasar el robot (x, y en mm desde el eje; x+ derecha, y+ adelante).
CIEGOS = {"izq": (-60, -25, 120, 220), "der": (25, 60, 120, 220)}   # la camara ve el piso desde y = 116
CIEGO_UMBRAL = 0.15                      # fraccion de blanco en la zona para decir "hay algo"
CAM_CERCA = 230                          # mm: si el frontal no ve nada pero la camara ve pared mas cerca, es pared
CELDA, PARED_CARA = 180, 84              # mm entre centros; cara de la pared de enfrente desde el centro (90 - 6)
ODO_MAX = 30                             # mm: correcciones de la camara mas grandes se ignoran
TOF_RANGO = 1000                         # mm: si el frontal ve algo mas cerca, manda el frontal y no la camara
PARED_F = 130                            # mm: al frente, menos de esto = pared (= PARED_F del sketch)
D_FRENTE_TOF = 130                       # mm que lee el frontal con el robot centrado y pared en su celda (= D_FRENTE del sketch)
odo = {"falta": 0, "corr": 0, "ult": 0, "cam_mm": None, "cam_err": None, "extra": 0, "frente": None,
       "ciego": {"izq": None, "der": None}}
PESO_CAM = 1                             # una pared vista solo por la camara cuenta como 3 celdas extra de camino
# Piso de la celda siguiente: la camara busca ahi marcas de color antes de que llegue el sensor
ROI_PISO = (0.30, 0.45, 0.70, 0.80)
SAT_MIN, VAL_MIN, FRAC_COLOR = 90, 70, 0.08   # pixel "de color": saturado y no oscuro (piso negro, pared blanca)
HUE = [(1, 0, 10), (1, 170, 180), (4, 20, 35), (2, 40, 85), (3, 90, 130)]   # (color, h min, h max) en HSV de OpenCV
BRILLO_MIN = 1.3                         # una marca refleja al menos 1.3 veces mas que el piso negro
PARED_LO = (0, 0, 170)                   # HSV de la pared (blanca por defecto)
PARED_HI = (180, 60, 255)
UMBRAL = 0.35

paredes = [[0] * N for _ in range(N)]
tentativo = [[0] * N for _ in range(N)]
visto = [[False] * N for _ in range(N)]
marcas = {}
cuenta = [0] * len(COLORES)
pos = INICIO
rumbo = RUMBO_INI
cam = None
cam_lock = threading.Lock()
cam_vio = {}                             # celda -> color que vio la camara (0 = solo piso)
OBJETIVO = 4                             # explora hasta encontrar este color (4 = AMAR)
encontrado = False


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


def guardar():
    escribe(ARCHIVO, {"paredes": paredes, "visto": visto,
                      "marcas": [[x, y, c] for (x, y), c in marcas.items()]})


def cargar():
    global paredes, visto
    datos = lee(ARCHIVO)
    if not datos:
        return
    if len(datos["paredes"]) != N:       # mapa de otro tamano de laberinto: no sirve
        print("Mapa guardado de otro tamano: lo ignoro")
        return
    paredes, visto = datos["paredes"], datos["visto"]
    bordes()
    for x, y, c in datos["marcas"]:
        marcas[(x, y)] = c
        cuenta[c] += 1


def dentro(x, y):
    return 0 <= x < N and 0 <= y < N


def set_pared(x, y, h, grid=None):
    grid = paredes if grid is None else grid
    grid[x][y] |= BIT[h]
    nx, ny = x + DX[h], y + DY[h]
    if dentro(nx, ny):
        grid[nx][ny] |= BIT[(h + 2) % 4]


def quita_pared(x, y, h):
    nx, ny = x + DX[h], y + DY[h]
    if dentro(nx, ny):                   # los bordes del laberinto nunca se quitan
        paredes[x][y] &= ~BIT[h]
        paredes[nx][ny] &= ~BIT[(h + 2) % 4]


def bordes():
    for i in range(N):
        set_pared(i, 0, 2)
        set_pared(i, N - 1, 0)
        set_pared(0, i, 3)
        set_pared(N - 1, i, 1)


def bloqueado(x, y, h, solo_conocido, usar_cam=True):
    if paredes[x][y] & BIT[h]:
        return True
    nx, ny = x + DX[h], y + DY[h]
    if not dentro(nx, ny):
        return True
    if solo_conocido:
        return not (visto[x][y] and visto[nx][ny])
    return False


def costo(x, y, h, usar_cam):
    # la camara no bloquea: una pared que solo ella vio hace el paso mas caro, los sensores deciden
    nx, ny = x + DX[h], y + DY[h]
    if usar_cam and not visto[x][y] and not visto[nx][ny] and tentativo[x][y] & BIT[h]:
        return 1 + PESO_CAM
    return 1


def flood(objetivos, solo_conocido, usar_cam=True):
    inf = N * N * (2 + PESO_CAM)
    d = [[inf] * N for _ in range(N)]
    q = []
    for x, y in objetivos:
        d[x][y] = 0
        q.append((0, x, y))
    while q:
        dist, x, y = heapq.heappop(q)
        if dist > d[x][y]:
            continue
        for h in range(4):
            if bloqueado(x, y, h, solo_conocido):
                continue
            nx, ny = x + DX[h], y + DY[h]
            nd = dist + costo(x, y, h, usar_cam)
            if nd < d[nx][ny]:
                d[nx][ny] = nd
                heapq.heappush(q, (nd, nx, ny))
    return d


# ---------- Comunicacion con el MCU ----------
def rpc(nombre, *args):
    while True:
        try:
            return Bridge.call(nombre, *args)
        except Exception:
            time.sleep(0.2)


def estado(e):
    rpc("set_estado", e)


def revisar_color(origen, h):
    global encontrado
    ev = rpc("color")
    if not ev:
        return
    c, k = ev % 16, ev // 16
    x, y = origen[0] + DX[h] * k, origen[1] + DY[h] * k
    vio = cam_vio.get((x, y))            # lo que vio la camara en esa celda (None = no la vio)
    if c == OBJETIVO:                    # la meta: el sensor y, si hay camara, tambien la camara
        if cam is None or vio in (None, OBJETIVO):
            encontrado = True
            rpc("alto")
            print(f"{COLORES[c]} encontrado en {x},{y}: sensor" + ("" if cam is None else " y camara"))
        else:
            print(f"Sensor ve {COLORES[c]} pero la camara vio {COLORES[vio]}: sigo buscando")
            return
    if (x, y) in marcas:
        return
    if vio == 0:                         # la camara vio piso limpio ahi: falso positivo del sensor
        print(f"Descarto {COLORES[c]} en {x},{y}: la camara no vio color")
        return
    marcas[(x, y)] = c
    cuenta[c] += 1
    rpc("set_cuenta", c, cuenta[c])
    print(f"Marca {COLORES[c]} en {x},{y} -> {cuenta[c]}")


def esperar(origen, h):
    while rpc("ocupado"):
        revisar_color(origen, h)
        time.sleep(0.02)
    revisar_color(origen, h)


def girar_a(h):
    global rumbo
    dif = (h - rumbo) % 4
    if dif:
        rpc("girar", {1: 1, 2: 2, 3: -1}[dif])
        esperar(pos, rumbo)
    rumbo = h


def tof_frente():
    """Distancia del VL53L0X de enfrente: la menor de 3 lecturas (una lectura mala no deja pasar)."""
    d = []
    for _ in range(3):
        time.sleep(0.03)
        d.append(rpc("odo", 5))
    return min(d)


def celdas_libres():
    """Cuantas celdas puede avanzar segun el frontal (99 si no ve nada).
    Si el frontal no ve nada (lectura perdida) y la camara ve la pared cerca, manda la camara."""
    d = tof_frente()
    if d >= TOF_RANGO:
        if odo["cam_mm"] is not None and odo["cam_mm"] < CAM_CERCA:
            print(f"Frontal sin lectura; la camara ve pared a {odo['cam_mm']:.0f} mm")
            return 0
        return 99
    if d < PARED_F:
        return 0
    return max(1, int((d - D_FRENTE_TOF + CELDA / 2) // CELDA))


def avanzar(n, rapido=False):
    """Los VL53L0X mandan: nunca avanza mas celdas de las que el frontal ve libres."""
    global pos
    odo["extra"] = int(precheck())     # primero la foto: la usan celdas_libres y los puntos ciegos
    ciego = [k for k, v in odo["ciego"].items() if v]
    if ciego:
        print(f"Camara: algo en el punto ciego {'/'.join(ciego)} de los ToF en {pos}, no avanzo")
        return False
    libres = celdas_libres()
    if libres == 0:
        set_pared(pos[0], pos[1], rumbo)
        print(f"Sensor: pared enfrente en {pos}, no avanzo")
        return False
    if libres < n:
        x, y = pos[0] + DX[rumbo] * libres, pos[1] + DY[rumbo] * libres
        if dentro(x, y):
            set_pared(x, y, rumbo)
        print(f"Sensor: solo {libres} celdas libres de {n}, recorto la recta")
    completo = libres >= n
    n = min(n, libres)
    origen = pos
    rpc("mover", n, int(rapido), odo["extra"])
    esperar(origen, rumbo)
    pos = (pos[0] + DX[rumbo] * n, pos[1] + DY[rumbo] * n)
    odo["corr"], odo["ult"], odo["frente"] = rpc("odo", 3), rpc("odo", 4), rpc("odo", 5)
    print(f"Odo {pos}: camara {odo['extra']:+d} mm, sensores {odo['corr']} correcciones (ultima {odo['ult']:+d} mm)")
    return completo


# ---------- Vision ----------
def abrir_camara():
    global cam
    import glob
    print("video:", sorted(glob.glob("/dev/video*")))
    for i in range(CAM_ID, 12):
        cam = cv2.VideoCapture(i, cv2.CAP_V4L2)
        if cam.isOpened() and cam.read()[0]:
            print("Camara en /dev/video%d" % i)
            break
        cam.release()
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cam.isOpened():
        cam = None
    return cam is not None


def foto():
    with cam_lock:                       # la usan el robot y la pagina web
        if cam is None:
            return None
        for _ in range(3):
            cam.grab()
        ok, img = cam.read()
    return img if ok else None


def analiza(img, dibuja=False):
    h, w = img.shape[:2]
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), PARED_LO, PARED_HI)
    res = {}
    for k, (x0, y0, x1, y1) in ROI.items():
        a, b = (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h))
        res[k] = mask[a[1]:b[1], a[0]:b[0]].mean() / 255 > UMBRAL
        if dibuja:
            cv2.rectangle(img, a, b, (0, 0, 255) if res[k] else (0, 255, 0), 2)
            cv2.putText(img, k, (a[0] + 2, b[1] - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)
    return res, mask


def leer_camara(debug=False):
    if cam is None:
        return None
    img = foto()
    if img is None:
        return None
    res, mask = analiza(img, debug)
    print("cam:", " ".join("%s=%s" % (k, "P" if v else ".") for k, v in res.items()))
    return res                           # sin guardar imagenes en /app: App Lab falla al arrancar con ellas


def color_piso(img):
    h, w = img.shape[:2]
    x0, y0, x1, y1 = ROI_PISO
    hsv = cv2.cvtColor(img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)], cv2.COLOR_BGR2HSV)
    ok = cv2.inRange(hsv, (0, SAT_MIN, VAL_MIN), (180, 255, 255)) > 0
    if ok.mean() < FRAC_COLOR:
        return 0
    hues = hsv[..., 0][ok]
    votos = [0] * len(COLORES)
    for c, a, b in HUE:
        votos[c] += int(((hues >= a) & (hues <= b)).sum())
    return max(range(len(COLORES)), key=votos.__getitem__) if max(votos) else 0


def dist_camara(img):
    """mm del eje a la base de la pared de enfrente (borde blanco/negro al centro de la imagen), o None."""
    h, w = img.shape[:2]
    franja = cv2.inRange(cv2.cvtColor(img[:, int(w * 0.45):int(w * 0.55)], cv2.COLOR_BGR2HSV), PARED_LO, PARED_HI)
    blanco = franja.mean(axis=1) > 128
    f = (h / 2) / math.tan(math.radians(CAM_FOV_V / 2))
    for y in range(h - 1, -1, -1):       # de abajo hacia arriba: la primera fila blanca es la base de la pared
        if blanco[y]:
            ang = CAM_INCL + math.degrees(math.atan((y - h / 2) / f))
            return CAM_H / math.tan(math.radians(ang)) + CAM_Y if ang > 1 else None
    return None


def error_camara(d):
    """mm que le faltan para quedar centrado (+ = esta atras), segun la pared que ve la camara."""
    if d is None or d > PARED_CARA + 2 * CELDA:     # lejos la medida ya no es confiable
        return None
    e = (d - PARED_CARA) - round((d - PARED_CARA) / CELDA) * CELDA
    return e if abs(e) <= ODO_MAX else None


def hacia_objetivo(img):
    """Si la camara ve el color OBJETIVO en el piso: -1 izquierda, 0 al frente, 1 derecha (None si no lo ve).
    Mira la mitad de abajo de la imagen partida en tercios y elige el tercio con mas pixeles de ese color."""
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img[int(h * 0.4):], cv2.COLOR_BGR2HSV)
    a, b = next((a, b) for c, a, b in HUE if c == OBJETIVO)
    m = cv2.inRange(hsv, (a, SAT_MIN, VAL_MIN), (b, 255, 255)) > 0
    tercios = [m[:, i * w // 3:(i + 1) * w // 3].mean() for i in range(3)]
    i = max(range(3), key=tercios.__getitem__)
    return i - 1 if tercios[i] >= FRAC_COLOR / 2 else None


def piso_a_px(x, y, w, h):
    """Pixel (u, v) donde la camara ve el punto del piso (x, y) del robot, con la geometria del CAD."""
    dy = y - CAM_Y
    if dy <= 0:
        return None
    ang = math.atan2(CAM_H, dy) - math.radians(CAM_INCL)          # bajo el eje optico
    prof = dy * math.cos(math.radians(CAM_INCL)) + CAM_H * math.sin(math.radians(CAM_INCL))
    fv = (h / 2) / math.tan(math.radians(CAM_FOV_V / 2))
    fh = (w / 2) / math.tan(math.radians(CAM_FOV_H / 2))
    return int(w / 2 + fh * x / prof), int(h / 2 + fv * math.tan(ang))


def zona_px(zona, w, h):
    x0, x1, y0, y1 = zona
    pts = [piso_a_px(x, y, w, h) for x in (x0, x1) for y in (y0, y1)]
    us, vs = [p[0] for p in pts], [p[1] for p in pts]
    return max(0, min(us)), max(0, min(vs)), min(w, max(us)), min(h, max(vs))


def ciegos(img):
    """Pared (blanco) en los puntos ciegos de los ToF: {"izq": bool, "der": bool}."""
    h, w = img.shape[:2]
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), PARED_LO, PARED_HI)
    res = {}
    for k, z in CIEGOS.items():
        u0, v0, u1, v1 = zona_px(z, w, h)
        res[k] = bool(u1 > u0 and v1 > v0 and mask[v0:v1, u0:u1].mean() / 255 > CIEGO_UMBRAL)
    return res


def precheck():
    """Una foto antes de avanzar: color del piso de la celda siguiente, puntos ciegos y correccion de distancia."""
    odo["ciego"], odo["cam_mm"] = {"izq": None, "der": None}, None
    if cam is None:
        return 0
    img = foto()
    if img is None:
        return 0
    odo["ciego"] = ciegos(img)
    nx, ny = pos[0] + DX[rumbo], pos[1] + DY[rumbo]
    if dentro(nx, ny) and (nx, ny) not in cam_vio:
        cam_vio[(nx, ny)] = color_piso(img)
        if cam_vio[(nx, ny)]:
            print(f"Camara: {COLORES[cam_vio[(nx, ny)]]} adelante en {nx},{ny}")
    odo["cam_mm"] = dist_camara(img)
    odo["cam_err"] = error_camara(odo["cam_mm"])
    if rpc("odo", 5) < TOF_RANGO:        # el frontal ve la pared: corrige el sketch con el ToF, no la camara
        return 0
    return odo["cam_err"] or 0


def sensar():
    x, y = pos
    time.sleep(0.06)                     # deja que los VL53L0X den una lectura nueva
    p = rpc("paredes")                   # siempre, aunque la celda ya se conozca: los sensores mandan
    if p >= 0:
        for bit, rel in ((1, -1), (2, 0), (4, 1)):
            if p & bit:
                set_pared(x, y, (rumbo + rel) % 4)
            else:                        # el sensor ve libre: corrige un mapa viejo
                quita_pared(x, y, (rumbo + rel) % 4)
    if visto[x][y]:
        return
    visto[x][y] = True

    c = leer_camara()                    # ve por arriba: tambien detras de una pared de enfrente
    if c is None:
        return
    der = (rumbo + 1) % 4
    for k, v in c.items():
        if not v:
            continue
        a, l, w = k.split(",")
        cx = x + DX[rumbo] * int(a) + DX[der] * int(l)
        cy = y + DY[rumbo] * int(a) + DY[der] * int(l)
        if dentro(cx, cy) and not visto[cx][cy]:
            set_pared(cx, cy, (rumbo + REL[w]) % 4, tentativo)


# ---------- Dashboard de colores (http://<ip de la Q>:7000) ----------
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


def api_lectura():
    v = lectura()
    vivo = {"falta": rpc("odo", 1), "frente": rpc("odo", 5), "paredes": rpc("odo", 2)}
    return {"v": v, "color": COLORES[clasifica(v)], "colores": COLORES, "refs": REFS, "modo": modo,
            "odo": {**odo, **vivo}}


def que_haria(izq, frente, der, mueve):
    """Simulacion para pruebas: que haria el robot con lo que leen los ToF ahora (no mueve nada)."""
    if frente < D_FRENTE_TOF - 10:
        return "Retrocede: muy pegado a la pared de enfrente", 2, 0
    if mueve and frente < PARED_F:
        return f"Frena: pared a {frente} mm, se detiene a {D_FRENTE_TOF} mm", 0, 0
    libres = 0 if frente < PARED_F else (99 if frente >= TOF_RANGO else
                                         max(1, int((frente - D_FRENTE_TOF + CELDA / 2) // CELDA)))
    libre = {0: libres > 0, -1: izq >= 120, 1: der >= 120, 2: True}
    rel = next(r for r in (1, 0, -1, 2) if libre[r])   # modo tonto: pared derecha
    n = (libres if libres < 99 else "varias") if rel == 0 else 1
    texto = {0: f"Sigue de frente ({n} celda{'s' if n != 1 else ''})",
             1: "Gira 90° a la derecha (no va de frente), luego 1 celda hacia allá",
             -1: "Gira 90° a la izquierda (no va de frente), luego 1 celda hacia allá",
             2: "Media vuelta (180°), luego 1 celda de regreso"}[rel]
    return texto, rel, n


def api_tof():
    izq, frente, der = rpc("odo", 6), rpc("odo", 5), rpc("odo", 7)
    mueve = bool(rpc("odo", 2) & 8)
    accion, rel, n = que_haria(izq, frente, der, mueve)
    return {"izq": izq, "frente": frente, "der": der, "pared": 120, "pared_f": PARED_F,
            "libres": celdas_libres(), "falta": rpc("odo", 1), "mueve": mueve,
            "accion": accion, "rel": rel, "modo": modo, "ciego": odo["ciego"], "cam_mm": odo["cam_mm"]}


def api_modo(m: str):
    global modo
    if m in ("mapa", "tonto"):
        modo = m
        escribe(ARCH_MODO, modo)
        print("Modo", modo)
    return {"modo": modo}


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


reintento = 0


def api_foto():
    global cam, reintento
    if cam is None and USAR_CAM and time.time() > reintento:   # la camara pudo conectarse despues de arrancar
        reintento = time.time() + 5
        with cam_lock:
            abrir_camara()
    img = foto() if cam is not None else None
    if img is None:
        if cam is not None:              # se desconecto: la vuelve a buscar
            with cam_lock:
                cam.release()
                cam = None
        return {"img": None}
    c = color_piso(img)
    cg = ciegos(img)                     # antes de dibujar encima
    res, _ = analiza(img, True)
    h, w = img.shape[:2]
    x0, y0, x1, y1 = ROI_PISO
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), (255, 0, 255), 2)
    cv2.putText(img, COLORES[c], (int(x0 * w) + 2, int(y1 * h) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
    for k, z in CIEGOS.items():          # puntos ciegos de los ToF que cubre la camara
        u0, v0, u1, v1 = zona_px(z, w, h)
        cv2.rectangle(img, (u0, v0), (u1, v1), (0, 0, 255) if cg[k] else (255, 128, 0), 1)
    d = dist_camara(img)
    if d is not None:                    # linea donde la camara ve la base de la pared de enfrente
        f = (h / 2) / math.tan(math.radians(CAM_FOV_V / 2))
        yb = int(h / 2 + f * math.tan(math.radians(math.degrees(math.atan(CAM_H / (d - CAM_Y))) - CAM_INCL)))
        cv2.line(img, (0, yb), (w, yb), (0, 255, 255), 2)
        cv2.putText(img, "%d mm" % d, (4, max(yb - 4, 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
    img = cv2.resize(img, (160, 120))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    vivo = {"cam_mm": round(d) if d else None, "cam_err": error_camara(d), "falta": rpc("odo", 1),
            "frente": rpc("odo", 5), "paredes": rpc("odo", 2)}
    return {"img": base64.b64encode(buf).decode(), "res": res, "odo": {**odo, **vivo}}


ui = WebUI()
ui.expose_api("GET", "/api/lectura", api_lectura)
ui.expose_api("GET", "/api/guardar", api_guardar)
ui.expose_api("GET", "/api/foto", api_foto)
ui.expose_api("GET", "/api/modo", api_modo)
ui.expose_api("GET", "/api/tof", api_tof)


# ---------- Estrategias ----------
def explorar(objetivos, est):
    estado(est)
    while pos not in objetivos:
        sensar()
        d = flood(objetivos, False)
        x, y = pos
        if d[x][y] >= len(d) * len(d) * (2 + PESO_CAM):
            print("Sin camino")
            return False
        mejor = None
        for h in (rumbo, (rumbo + 1) % 4, (rumbo + 3) % 4, (rumbo + 2) % 4):
            if paredes[x][y] & BIT[h]:
                continue
            nx, ny = x + DX[h], y + DY[h]
            if dentro(nx, ny) and (mejor is None or d[nx][ny] < d[mejor[1]][mejor[2]]):
                mejor = (h, nx, ny)
        girar_a(mejor[0])
        avanzar(1)                       # si el sensor ve pared, no avanza y se vuelve a planear
    sensar()
    guardar()
    return True


def seguir_pared(objetivos, mano=1):
    """Modo tonto (el unico que se usa): sigue una pared con lo que leen los ToF en cada celda, sin mapa.
    mano = 1 derecha, -1 izquierda."""
    estado(1)
    vistos = set()
    while (pos, rumbo) not in vistos:    # repetir posicion y rumbo = da vueltas a una isla
        if pos in objetivos:
            return True
        vistos.add((pos, rumbo))
        time.sleep(0.06)                 # lectura nueva de los VL53L0X
        p = rpc("paredes")
        libre = {-1: not p & 1, 0: not p & 2, 1: not p & 4, 2: True}
        rel = next(r for r in (mano, 0, -mano, 2) if libre[r])
        girar_a((rumbo + rel) % 4)
        if not avanzar(1):
            vistos.discard((pos, rumbo))
    print("Da vueltas a una isla con la mano", "derecha" if mano > 0 else "izquierda")
    return False


def buscar_color():
    """Explora sin fin hasta encontrar el color OBJETIVO: los ToF dicen que salidas estan libres y
    entre ellas va a la celda menos visitada (empate: pared derecha). Un toque a D2 lo detiene."""
    global encontrado
    encontrado = False
    estado(1)
    mano, visitas, bloq = 1, {}, set()   # bloq: salidas donde no pudo avanzar (ToF o punto ciego)
    while not encontrado:
        if rpc("arranque"):
            print("Detenido con el boton")
            return False
        visitas[pos] = visitas.get(pos, 0) + 1
        time.sleep(0.06)
        p = rpc("paredes")
        libre = {-1: not p & 1, 0: not p & 2, 1: not p & 4, 2: True}
        # entre las salidas que los ToF ven libres, la celda menos visitada; empate: pared derecha
        # (no guarda paredes: solo cuenta visitas, asi no se mete en ciclos de islas)
        opciones = [r for r in (mano, 0, -mano) if libre[r] and (pos, (rumbo + r) % 4) not in bloq] or [2]
        def veces(r):
            h = (rumbo + r) % 4
            return visitas.get((pos[0] + DX[h], pos[1] + DY[h]), 0)
        # la camara solo es referencia: desempata entre salidas igual de visitadas (punto muerto de los ToF)
        img = foto() if cam is not None else None
        ve = hacia_objetivo(img) if img is not None else None
        rel = min(opciones, key=lambda r: (veces(r), r != ve, opciones.index(r)))
        if ve is not None and rel == ve:
            print(f"Camara: {COLORES[OBJETIVO]} hacia", {-1: "la izquierda", 0: "el frente", 1: "la derecha"}[ve])
        girar_a((rumbo + rel) % 4)
        if not encontrado and not avanzar(1):
            bloq.add((pos, rumbo))       # no la vuelve a intentar desde esta celda
    return True


def ruta_conocida():
    d = flood(META, True, usar_cam=False)
    return d if d[INICIO[0]][INICIO[1]] < N * N else None


def ruta_rapida(d):
    estado(3)
    while pos not in META:
        x, y = pos
        h = next((h for h in range(4) if not bloqueado(x, y, h, True)
                  and d[x + DX[h]][y + DY[h]] == d[x][y] - 1), None)
        if h is None:
            return False
        n = 0
        cx, cy = x, y
        while (not bloqueado(cx, cy, h, True)
               and d[cx + DX[h]][cy + DY[h]] == d[cx][cy] - 1):
            cx, cy = cx + DX[h], cy + DY[h]
            n += 1
        girar_a(h)
        if not avanzar(n, rapido=True):
            return False
    return True


# ---------- Principal ----------
def borrar():
    global paredes, tentativo, visto
    paredes = [[0] * N for _ in range(N)]
    tentativo = [[0] * N for _ in range(N)]
    visto = [[False] * N for _ in range(N)]
    marcas.clear()
    cam_vio.clear()
    bordes()
    if os.path.exists(ARCHIVO):
        os.remove(ARCHIVO)
    for c in range(1, len(COLORES)):
        cuenta[c] = 0
        rpc("set_cuenta", c, 0)
    estado(5)
    print("Memoria borrada")


def iniciar():
    global REFS, modo
    REFS = lee(ARCH_COL) or lee("/app/colores.json") or REFS   # tambien los de la version anterior
    enviar_refs()
    bordes()
    cargar()
    for c in range(1, len(COLORES)):
        rpc("set_cuenta", c, cuenta[c])
    if USAR_CAM and abrir_camara():
        leer_camara(debug=True)
        estado(0)
    else:
        print("Sin camara: solo VL53L0X")
        estado(6)


def loop():
    global pos, rumbo
    a = rpc("arranque")
    if a == 2:
        borrar()
        return
    if not a:
        time.sleep(0.05)
        return
    pos, rumbo = INICIO, RUMBO_INI
    t = time.time()
    # explora sin fin (pared derecha, cambia de mano en islas) hasta el amarillo
    estado(4 if buscar_color() else 0)
    guardar()
    print(f"Corrida: {time.time() - t:.1f} s, marcas {cuenta[1:]}")


iniciar()
App.run(user_loop=loop)
