from arduino.app_utils import *
from collections import deque
import cv2
import json
import os
import time

print("Python OK, cv2", cv2.__version__)

# ---------- Laberinto ----------
N = 16                                   # 3 m / 18 cm
INICIO = (0, 0)
RUMBO_INI = 0                            # 0=N 1=E 2=S 3=O
META = {(7, 7), (7, 8), (8, 7), (8, 8)}
COLORES = ["PISO", "ROJO", "VERDE", "AZUL", "AMAR"]
ARCHIVO = "/app/mapa.json"

DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
BIT = [1, 2, 4, 8]

# ---------- Camara ----------
# Los VL53L0X leen las paredes de la celda actual. La camara mira la celda
# siguiente y adelanta sus paredes al mapa como "tentativas".
CAM_ID = 0
ANCHO, ALTO = 320, 240
# Regiones (x0, y0, x1, y1) en fraccion de la imagen; ajustar con /app/cal.jpg
ROI = {
    "frente2": (0.35, 0.05, 0.65, 0.25),   # pared del fondo de la celda siguiente
    "izq2":    (0.05, 0.25, 0.25, 0.55),   # pared izquierda de la celda siguiente
    "der2":    (0.75, 0.25, 0.95, 0.55),   # pared derecha de la celda siguiente
}
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


def guardar():
    datos = {"paredes": paredes, "visto": visto,
             "marcas": [[x, y, c] for (x, y), c in marcas.items()]}
    with open(ARCHIVO, "w") as f:
        json.dump(datos, f)


def cargar():
    global paredes, visto
    if not os.path.exists(ARCHIVO):
        return
    with open(ARCHIVO) as f:
        datos = json.load(f)
    paredes, visto = datos["paredes"], datos["visto"]
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
    if not usar_cam or visto[x][y] or visto[nx][ny]:
        return False
    return bool(tentativo[x][y] & BIT[h])


def flood(objetivos, solo_conocido, usar_cam=True):
    inf = N * N
    d = [[inf] * N for _ in range(N)]
    q = deque()
    for x, y in objetivos:
        d[x][y] = 0
        q.append((x, y))
    while q:
        x, y = q.popleft()
        for h in range(4):
            if bloqueado(x, y, h, solo_conocido, usar_cam):
                continue
            nx, ny = x + DX[h], y + DY[h]
            if d[nx][ny] <= d[x][y] + 1:
                continue
            d[nx][ny] = d[x][y] + 1
            q.append((nx, ny))
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
    ev = rpc("color")
    if not ev:
        return
    c, k = ev % 16, ev // 16
    x, y = origen[0] + DX[h] * k, origen[1] + DY[h] * k
    if (x, y) in marcas:
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


def avanzar(n, rapido=False):
    global pos
    origen = pos
    rpc("mover", n, int(rapido))
    esperar(origen, rumbo)
    pos = (pos[0] + DX[rumbo] * n, pos[1] + DY[rumbo] * n)


# ---------- Vision ----------
def abrir_camara():
    global cam
    cam = cv2.VideoCapture(CAM_ID)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
    cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not cam.isOpened():
        cam = None
    return cam is not None


def foto():
    for _ in range(3):
        cam.grab()
    ok, img = cam.read()
    return img if ok else None


def leer_camara(debug=False):
    if cam is None:
        return None
    img = foto()
    if img is None:
        return None
    h, w = img.shape[:2]
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), PARED_LO, PARED_HI)
    res = {}
    for k, (x0, y0, x1, y1) in ROI.items():
        a, b = (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h))
        res[k] = mask[a[1]:b[1], a[0]:b[0]].mean() / 255 > UMBRAL
        if debug:
            cv2.rectangle(img, a, b, (0, 0, 255) if res[k] else (0, 255, 0), 2)
    if debug:
        cv2.imwrite("/app/cal.jpg", img)
        cv2.imwrite("/app/mask.jpg", mask)
    return res


def sensar():
    x, y = pos
    if visto[x][y]:
        return
    time.sleep(0.06)                     # deja que los VL53L0X den una lectura nueva
    p = rpc("paredes")
    for bit, rel in ((1, -1), (2, 0), (4, 1)):
        if p & bit:
            set_pared(x, y, (rumbo + rel) % 4)
    visto[x][y] = True

    nx, ny = x + DX[rumbo], y + DY[rumbo]
    if p & 2 or not dentro(nx, ny) or visto[nx][ny]:
        return
    c = leer_camara()
    if c is None:
        return
    for k, rel in (("frente2", 0), ("izq2", -1), ("der2", 1)):
        if c[k]:
            set_pared(nx, ny, (rumbo + rel) % 4, tentativo)


# ---------- Estrategias ----------
def explorar(objetivos, est):
    estado(est)
    while pos not in objetivos:
        sensar()
        d = flood(objetivos, False)
        x, y = pos
        if d[x][y] >= N * N:
            d = flood(objetivos, False, usar_cam=False)   # la camara pudo ver paredes falsas
        if d[x][y] >= N * N:
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
        avanzar(1)
    sensar()
    guardar()
    return True


def ruta_conocida():
    d = flood(META, True)
    return d if d[INICIO[0]][INICIO[1]] < N * N else None


def ruta_rapida(d):
    estado(3)
    while pos not in META:
        x, y = pos
        h = next(h for h in range(4) if not bloqueado(x, y, h, True)
                 and d[x + DX[h]][y + DY[h]] == d[x][y] - 1)
        n = 0
        cx, cy = x, y
        while (not bloqueado(cx, cy, h, True)
               and d[cx + DX[h]][cy + DY[h]] == d[cx][cy] - 1):
            cx, cy = cx + DX[h], cy + DY[h]
            n += 1
        girar_a(h)
        avanzar(n, rapido=True)


# ---------- Principal ----------
def borrar():
    global paredes, tentativo, visto
    paredes = [[0] * N for _ in range(N)]
    tentativo = [[0] * N for _ in range(N)]
    visto = [[False] * N for _ in range(N)]
    marcas.clear()
    bordes()
    if os.path.exists(ARCHIVO):
        os.remove(ARCHIVO)
    for c in range(1, len(COLORES)):
        cuenta[c] = 0
        rpc("set_cuenta", c, 0)
    estado(5)
    print("Memoria borrada")


def iniciar():
    bordes()
    cargar()
    for c in range(1, len(COLORES)):
        rpc("set_cuenta", c, cuenta[c])
    if abrir_camara():
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
    d = ruta_conocida()
    if d:
        ruta_rapida(d)
        estado(4)
    else:
        explorar(META, 1)
        explorar({INICIO}, 2)
        estado(0)
    guardar()
    print(f"Corrida: {time.time() - t:.1f} s, marcas {cuenta[1:]}")


iniciar()
App.run(user_loop=loop)
