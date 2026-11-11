from arduino.app_utils import *
from arduino.app_bricks.web_ui import WebUI
import cv2
import json
import os
import threading
import time
import base64

print("Python OK, cv2", cv2.__version__)

COLORES = ["PISO", "ROJO", "VERDE", "AZUL", "AMAR"]
OBJETIVO = 4                             # se detiene al encontrar este color (4 = AMAR)
DATOS = "/app/datos"                     # en una subcarpeta: archivos en la raiz de la app confunden a App Lab
os.makedirs(DATOS, exist_ok=True)
ARCH_COL = DATOS + "/colores.json"
# r, g, b normalizados y brillo c; los mismos de refs[] del sketch
REFS = [[0.282, 0.379, 0.333, 153], [0.602, 0.208, 0.188, 581], [0.155, 0.535, 0.309, 636],
        [0.16, 0.329, 0.508, 354], [0.409, 0.449, 0.142, 1836]]
BRILLO_MIN = 1.3                         # una marca refleja al menos 1.3 veces mas que el piso negro

# ---------- Movimiento ----------
DX = [0, 1, 0, -1]
DY = [1, 0, -1, 0]
CELDA = 180                              # mm por avance; la posicion solo sirve para contar visitas
PARED = 120                              # mm: lateral con esto o mas = libre
PARED_F = 130                            # mm: al frente, menos de esto = pared (= PARED_F del sketch)
FRENTE_LIBRE = 150                       # mm: con el frontal leyendo esto o mas, avanza de frente
D_FRENTE_TOF = 130                       # mm donde se detiene el sketch con pared enfrente (= D_FRENTE)
ISLA = 3                                 # visitas a una celda para decir que rodea una isla

# ---------- Camara: solo busca el amarillo ----------
CAM_ID = 0
USAR_CAM = True
ANCHO, ALTO = 320, 240
SAT_MIN, VAL_MIN, FRAC_COLOR = 90, 70, 0.08   # pixel "de color": saturado y no oscuro (piso negro, pared blanca)
HUE_AMAR = (20, 35)                      # h min, h max del amarillo en HSV de OpenCV

pos = (0, 0)
rumbo = 0
cam = None
cam_lock = threading.Lock()
cuenta = [0] * len(COLORES)
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


# ---------- Comunicacion con el MCU ----------
def rpc(nombre, *args):
    while True:
        try:
            return Bridge.call(nombre, *args)
        except Exception:
            time.sleep(0.2)


def estado(e):
    rpc("set_estado", e)


def revisar_color():
    """El sketch manda un color solo si lo leyo 3 veces seguidas; el amarillo es la meta."""
    global encontrado
    c = rpc("color")
    if not c:
        return
    cuenta[c] += 1
    rpc("set_cuenta", c, cuenta[c])
    print(f"Marca {COLORES[c]} cerca de {pos} -> {cuenta[c]}")
    if c == OBJETIVO:
        encontrado = True
        rpc("alto")
        print(f"{COLORES[c]} encontrado: meta")


def esperar():
    while rpc("ocupado"):
        revisar_color()
        time.sleep(0.02)
    revisar_color()


def girar(rel):
    """rel: 1 derecha, -1 izquierda, 2 media vuelta, 0 nada."""
    global rumbo
    if rel:
        rpc("girar", rel)
        esperar()
    rumbo = (rumbo + rel) % 4


def tof3():
    """izq, frente, der: la menor de 3 lecturas de cada VL53L0X (una lectura mala no deja pasar)."""
    d = [9999] * 3
    for _ in range(3):
        time.sleep(0.03)                 # lectura nueva de los VL53L0X
        d = [min(a, rpc("odo", i)) for a, i in zip(d, (6, 5, 7))]
    return d


def avanzar():
    """Una celda por distancia (el sketch para con el frontal); la posicion sale de los mm recorridos."""
    global pos
    rpc("mover", CELDA)
    esperar()
    mm = rpc("odo", 0)
    n = round(mm / CELDA)
    pos = (pos[0] + DX[rumbo] * n, pos[1] + DY[rumbo] * n)
    print(f"Avanzo {mm} mm -> {pos}")


def salidas(izq, frente, der):
    """Salidas libres en orden de la mano izquierda (-1 izq, 0 frente, 1 der); sin ninguna, media vuelta (2)."""
    return [r for r, ok in ((-1, izq >= PARED), (0, frente >= FRENTE_LIBRE), (1, der >= PARED)) if ok] or [2]


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


def hacia_objetivo(img):
    """Si la camara ve amarillo en el piso: -1 izquierda, 0 al frente, 1 derecha (None si no lo ve).
    Mira la mitad de abajo de la imagen partida en tercios y elige el tercio con mas amarillo."""
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img[int(h * 0.4):], cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (HUE_AMAR[0], SAT_MIN, VAL_MIN), (HUE_AMAR[1], 255, 255)) > 0
    tercios = [m[:, i * w // 3:(i + 1) * w // 3].mean() for i in range(3)]
    i = max(range(3), key=tercios.__getitem__)
    return i - 1 if tercios[i] >= FRAC_COLOR / 2 else None


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


def api_lectura():
    v = lectura()
    odo = {"falta": rpc("odo", 1), "frente": rpc("odo", 5), "paredes": rpc("odo", 2), "mm": rpc("odo", 0)}
    return {"v": v, "color": COLORES[clasifica(v)], "colores": COLORES, "refs": REFS, "odo": odo}


def que_haria(izq, frente, der, mueve):
    """Simulacion para pruebas: que haria el robot con lo que leen los ToF ahora (no mueve nada)."""
    if frente < D_FRENTE_TOF - 10:
        return "Retrocede: muy pegado a la pared de enfrente", 2
    if mueve and frente < PARED_F:
        return f"Frena: pared a {frente} mm, se detiene a {D_FRENTE_TOF} mm", 0
    rel = salidas(izq, frente, der)[0]
    return {0: "Sigue de frente 1 celda",
            1: "Gira 90° a la derecha y avanza 1 celda",
            -1: "Gira 90° a la izquierda y avanza 1 celda",
            2: "Media vuelta (180°) y avanza 1 celda"}[rel], rel


def api_tof():
    izq, frente, der = rpc("odo", 6), rpc("odo", 5), rpc("odo", 7)
    mueve = bool(rpc("odo", 2) & 8)
    accion, rel = que_haria(izq, frente, der, mueve)
    return limpio({"izq": izq, "frente": frente, "der": der, "pared": PARED, "pared_f": PARED_F,
                   "falta": rpc("odo", 1), "mueve": mueve, "accion": accion, "rel": rel})


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
    img = foto() if cam is not None else None   # vigilar_cam la busca si no esta
    if img is None:
        return {"img": None}
    ve = hacia_objetivo(img)
    h, w = img.shape[:2]
    if ve is not None:                   # marca el tercio donde ve el amarillo
        x0 = (ve + 1) * w // 3
        cv2.rectangle(img, (x0, int(h * 0.4)), (x0 + w // 3 - 1, h - 1), (0, 255, 255), 2)
    img = cv2.resize(img, (160, 120))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    return {"img": base64.b64encode(buf).decode(), "amarillo": ve}


def limpio(x):
    """Pasa tipos de numpy a tipos de Python para que FastAPI los pueda mandar."""
    return json.loads(json.dumps(x, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


ui = WebUI()
ui.expose_api("GET", "/api/lectura", api_lectura)
ui.expose_api("GET", "/api/guardar", api_guardar)
ui.expose_api("GET", "/api/foto", api_foto)
ui.expose_api("GET", "/api/tof", api_tof)


# ---------- Estrategia ----------
def buscar_color():
    """Explora hasta el amarillo. En cada paso lee los 3 ToF (la menor de 3 lecturas) y sigue la mano izquierda;
    si ya paso 3 veces por esa celda (rodea una isla) toma la salida que ha usado menos. Un toque a D2 lo detiene."""
    global encontrado, pos, rumbo
    encontrado = False
    pos, rumbo = (0, 0), 0
    estado(1)
    visitas, usos = {}, {}
    while not encontrado:
        if rpc("arranque"):
            print("Detenido con el boton")
            return False
        visitas[pos] = visitas.get(pos, 0) + 1
        izq, frente, der = tof3()
        ops = salidas(izq, frente, der)
        rel = ops[0]
        if visitas[pos] >= ISLA:
            # la camara solo desempata entre salidas igual de usadas
            img = foto() if cam is not None else None
            ve = hacia_objetivo(img) if img is not None else None
            rel = min(ops, key=lambda r: (usos.get((pos, (rumbo + r) % 4), 0), r != ve, ops.index(r)))
        h = (rumbo + rel) % 4
        usos[(pos, h)] = usos.get((pos, h), 0) + 1
        print(f"ToF izq {izq} frente {frente} der {der} en {pos}:",
              {1: "derecha", 0: "frente", -1: "izquierda", 2: "media vuelta"}[rel])
        girar(rel)
        if not encontrado:
            avanzar()
    return True


# ---------- Principal ----------
def borrar():
    for c in range(1, len(COLORES)):
        cuenta[c] = 0
        rpc("set_cuenta", c, 0)
    estado(5)
    print("Conteo borrado")


def iniciar():
    global REFS
    REFS = lee(ARCH_COL) or lee("/app/colores.json") or REFS   # tambien los de la version anterior
    enviar_refs()
    for c in range(1, len(COLORES)):
        rpc("set_cuenta", c, cuenta[c])
    if USAR_CAM and abrir_camara():
        estado(0)
    else:
        print("Sin camara: la sigo buscando")
        estado(6)
    if USAR_CAM:                         # en segundo plano: no frena el arranque de la app
        threading.Thread(target=vigilar_cam, daemon=True).start()


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


def loop():
    a = rpc("arranque")
    if a == 2:
        borrar()
        return
    if not a:
        time.sleep(0.05)
        return
    t = time.time()
    estado(4 if buscar_color() else 0)
    print(f"Corrida: {time.time() - t:.1f} s, marcas {cuenta[1:]}")


iniciar()
App.run(user_loop=loop)
