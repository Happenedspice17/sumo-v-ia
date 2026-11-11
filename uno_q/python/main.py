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
ARCH_MAPA = DATOS + "/mapa.json"
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
FRENTE_LIBRE = 220                       # mm: frente libre; a la mitad entre pared en su celda (~130) y en la siguiente (~310)
D_FRENTE_TOF = 130                       # mm donde se detiene el sketch con pared enfrente (= D_FRENTE)
VOTO_MAX = 5                             # cada lectura vota pared (+1) o libre (-1); tope para que el mapa se corrija
ISLA = 3                                 # visitas a una celda para decir que rodea una isla
Y_COLOR = 36                             # mm del eje al sensor de color (adelante)

# ---------- Camara: solo busca el amarillo ----------
CAM_ID = 0
USAR_CAM = True
ANCHO, ALTO = 320, 240
SAT_MIN, VAL_MIN, FRAC_COLOR = 90, 70, 0.08   # pixel "de color": saturado y no oscuro (piso negro, pared blanca)
HUE_AMAR = (20, 35)                      # h min, h max del amarillo en HSV de OpenCV
# Blanco = pared (el piso es negro y no lleva blanco). ZONA_PASO: piso por donde va a pasar, en fraccion de la imagen
BLANCO_LO, BLANCO_HI = (0, 0, 170), (180, 60, 255)
ZONA_PASO = (0.30, 0.55, 0.70, 1.00)
BLANCO_MAX = 0.15                        # fraccion de blanco en ZONA_PASO para ir lento

pos = (0, 0)
rumbo = 0
cam = None
cam_lock = threading.Lock()
cuenta = [0] * len(COLORES)
encontrado = False
# Mapa: celda -> [N, E, S, O] con 1 pared, 0 libre, None sin dato; colores: celda -> color; meta: celda del amarillo
muros = {}
colores = {}
meta = None
# Para la pagina web: durante una corrida lee esto (lo actualiza el robot) en vez de pedirle al Bridge
corriendo = False
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
def rpc(nombre, *args):
    while True:
        try:
            return Bridge.call(nombre, *args)
        except Exception:
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
    if c == OBJETIVO:
        encontrado, meta = True, cel
        rpc("alto")
        print(f"{COLORES[c]} encontrado en {cel}: meta")
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
    rumbo = (rumbo + rel) % 4


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
    Si la camara ve blanco en el camino va lento. Devuelve los ToF que saltaron (0 = ninguno)."""
    global pos
    rpc("mover", CELDA, int(blanco_adelante()))
    esperar(True)
    mm, saltos = rpc("odo", 0), rpc("odo", 3)
    vivo["mm"], vivo["saltos"] = mm, saltos
    n = round(mm / CELDA)
    for _ in range(n):                   # por donde paso no hay pared, seguro
        sig = vecino(pos, rumbo)
        celda(pos)[rumbo] = celda(sig)[(rumbo + 2) % 4] = -VOTO_MAX
        pos = sig
    print(f"Avanzo {mm} mm -> {pos}" + (f", salto en ToF {saltos}" if saltos else ""))
    return saltos


def salidas(izq, frente, der):
    """Salidas libres: primero de frente, luego mano izquierda (0 frente, -1 izq, 1 der); sin ninguna, media vuelta."""
    return [r for r, ok in ((0, frente >= FRENTE_LIBRE), (-1, izq >= PARED), (1, der >= PARED)) if ok] or [2]


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
                        "colores": [[*c, k] for c, k in colores.items()], "meta": meta})


def cargar():
    global meta
    d = lee(ARCH_MAPA)
    if not d:
        return
    muros.update({(x, y): [v or 0 for v in p] for x, y, *p in d["muros"]})
    colores.update({(x, y): k for x, y, k in d["colores"]})
    meta = tuple(d["meta"]) if d["meta"] else None
    for k in colores.values():
        cuenta[k] += 1
    print(f"Mapa: {len(muros)} celdas, meta {meta}")


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


def hacia_objetivo(img):
    """Si la camara ve amarillo en el piso: -1 izquierda, 0 al frente, 1 derecha (None si no lo ve).
    Mira la mitad de abajo de la imagen partida en tercios y elige el tercio con mas amarillo."""
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img[int(h * 0.4):], cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (HUE_AMAR[0], SAT_MIN, VAL_MIN), (HUE_AMAR[1], 255, 255)) > 0
    tercios = [m[:, i * w // 3:(i + 1) * w // 3].mean() for i in range(3)]
    i = max(range(3), key=tercios.__getitem__)
    return i - 1 if tercios[i] >= FRAC_COLOR / 2 else None


def frac_blanco(img):
    """Fraccion de blanco (pared) en el piso por donde va a pasar."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = ZONA_PASO
    hsv = cv2.cvtColor(img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)], cv2.COLOR_BGR2HSV)
    return (cv2.inRange(hsv, BLANCO_LO, BLANCO_HI) > 0).mean()


def blanco_adelante():
    """La camara ve blanco en el camino: va lento. El frontal hace el doble check (el sketch para a 130 mm)."""
    img = foto() if cam is not None else None
    if img is None or frac_blanco(img) < BLANCO_MAX:
        return False                     # negro: sigue normal
    f = rpc("odo", 5)
    print("Camara: blanco adelante, " + (f"el frontal lo confirma a {f} mm" if f < D_FRENTE_TOF + CELDA
                                         else "el frontal no ve nada (punto ciego?)") + ": voy lento")
    return True


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
    mapa = {"pos": pos, "celdas": len(muros), "meta": meta, "fase": fase_act}
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
    if corriendo:                        # ultima lectura de tof3 (la que uso para decidir)
        izq, frente, der, mueve, falta = vivo["izq"], vivo["frente"], vivo["der"], fase_act in ("GIRA", "AVANZA"), None
    else:
        izq, frente, der = rpc("odo", 6), rpc("odo", 5), rpc("odo", 7)
        mueve, falta = bool(rpc("odo", 2) & 8), rpc("odo", 1)
    accion, rel = que_haria(izq, frente, der, mueve)
    return limpio({"izq": izq, "frente": frente, "der": der, "pared": PARED, "pared_f": PARED_F,
                   "falta": falta, "mueve": mueve, "accion": accion, "rel": rel, "fase": fase_act})


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
        return {"img": None}
    ve = hacia_objetivo(img)
    b = frac_blanco(img)
    h, w = img.shape[:2]
    x0, y0, x1, y1 = ZONA_PASO               # rojo = ve blanco (pared) en el camino, verde = negro
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w) - 1, int(y1 * h) - 1),
                  (0, 0, 255) if b >= BLANCO_MAX else (0, 255, 0), 2)
    if ve is not None:                   # marca el tercio donde ve el amarillo
        x0 = (ve + 1) * w // 3
        cv2.rectangle(img, (x0, int(h * 0.4)), (x0 + w // 3 - 1, h - 1), (0, 255, 255), 2)
    img = cv2.resize(img, (160, 120))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 40])
    return limpio({"img": base64.b64encode(buf).decode(), "amarillo": ve, "blanco": round(b, 2)})


def limpio(x):
    """Pasa tipos de numpy a tipos de Python para que FastAPI los pueda mandar."""
    return json.loads(json.dumps(x, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


ui = WebUI()
ui.expose_api("GET", "/api/lectura", api_lectura)
ui.expose_api("GET", "/api/guardar", api_guardar)
ui.expose_api("GET", "/api/foto", api_foto)
ui.expose_api("GET", "/api/tof", api_tof)


# ---------- Estrategia ----------
def decidir(izq, frente, der, visitas, usos, saltos):
    """De frente, si no izquierda, si no derecha. Tras un salto: la salida nueva mas lejana.
    Con 3 visitas a la celda (isla): la salida menos usada; la camara desempata hacia el amarillo."""
    ops = salidas(izq, frente, der)
    nuevas = [r for r in ops if r != 2 and vecino(pos, (rumbo + r) % 4) not in muros]
    if saltos and nuevas:
        return max(nuevas, key=lambda r: {-1: izq, 0: frente, 1: der}[r])
    if visitas[pos] >= ISLA:
        img = foto() if cam is not None else None
        ve = hacia_objetivo(img) if img is not None else None
        return min(ops, key=lambda r: (usos.get((pos, (rumbo + r) % 4), 0), r != ve, ops.index(r)))
    return ops[0]


def buscar_color():
    """Maquina de estados: SENSA (3 ToF, 3 lecturas; ESCANEA con 5 tras un salto) -> DECIDE -> GIRA -> AVANZA.
    Todo se decide quieto. El color se revisa todo el tiempo; amarillo o un toque a D2 la terminan."""
    global encontrado
    encontrado = False
    estado(1)
    visitas, usos, saltos, f = {}, {}, 0, "SENSA"
    while not encontrado:
        if rpc("arranque"):
            print("Detenido con el boton")
            return False
        fase(f)
        if f in ("SENSA", "ESCANEA"):
            visitas[pos] = visitas.get(pos, 0) + 1
            lect = tof3(5 if f == "ESCANEA" else 3)
            anota(*lect)
            f = "DECIDE"
        elif f == "DECIDE":
            rel = decidir(*lect, visitas, usos, saltos)
            h = (rumbo + rel) % 4
            usos[(pos, h)] = usos.get((pos, h), 0) + 1
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
    REFS = lee(ARCH_COL) or lee("/app/colores.json") or REFS   # tambien los de la version anterior
    enviar_refs()
    cargar()
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
    global pos, rumbo, encontrado, corriendo
    pos, rumbo, encontrado = (0, 0), 0, False   # cada corrida empieza en la misma celda viendo al mismo lado
    t = time.time()
    corriendo = True
    try:
        ok = (meta is not None and seguir_ruta()) or buscar_color()
    finally:
        corriendo = False
        fase("")
    guardar()
    estado(4 if ok else 0)
    print(f"Corrida: {time.time() - t:.1f} s, marcas {cuenta[1:]}")


iniciar()
App.run(user_loop=loop)
