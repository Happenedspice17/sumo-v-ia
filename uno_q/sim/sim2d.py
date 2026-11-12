"""Simulador 2D del robot en un laberinto 11x11 tipo pista (isla central 3x3 con 2 entradas, bucles).
Fisica simple (diferencial, PWM -> mm/s, inercia al frenar), ToF con cono, ruido y fallas, giroscopio con deriva,
choques por contacto del cuerpo (cuadrado 120 mm, esquinas R30). Python = funciones reales de main.py."""
import sys, types, random, math, os

# ---------- main.py real (decidir, anota, ubica, frontera...) ----------
for m in ["arduino", "arduino.app_utils", "arduino.app_bricks", "arduino.app_bricks.web_ui", "cv2"]:
    sys.modules[m] = types.ModuleType(m)
sys.modules["cv2"].__version__ = "stub"
class _UI:
    def expose_api(self, *a): pass
sys.modules["arduino.app_bricks.web_ui"].WebUI = _UI
MAIN = os.environ.get("MAIN", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "python", "main.py"))
SRC = open(MAIN).read().replace('"/app/datos"', repr(__import__("tempfile").mkdtemp())).rsplit("try:\n    iniciar()", 1)[0]
import io, contextlib
CODE = compile(SRC, "main", "exec")
NULO = open(os.devnull, "w")
G = {}
with contextlib.redirect_stdout(NULO):
    exec(CODE, G)
import builtins
G["print"] = lambda *a, **k: None

N, C, MED = 11, 180.0, 6.0          # celdas, mm por celda, media pared
DX, DY = [0, 1, 0, -1], [1, 0, -1, 0]

# ---------- Laberinto ----------
def laberinto(seed, bucles=0.06):
    rnd = random.Random(seed)
    W = {(x, y): [True] * 4 for x in range(N) for y in range(N)}
    def abre(c, h):
        W[c][h] = False; W[(c[0] + DX[h], c[1] + DY[h])][(h + 2) % 4] = False
    m = N // 2
    sala = {(x, y) for x in range(m - 1, m + 2) for y in range(m - 1, m + 2)}
    for c in sala:                                  # sala central abierta por dentro
        for h in range(4):
            if (c[0] + DX[h], c[1] + DY[h]) in sala: abre(c, h)
    seen = set(sala); st = [(0, 0)]; seen.add((0, 0))
    while st:
        c = st[-1]
        hs = [h for h in range(4) if (c[0] + DX[h], c[1] + DY[h]) in W and (c[0] + DX[h], c[1] + DY[h]) not in seen]
        if not hs: st.pop(); continue
        h = rnd.choice(hs); abre(c, h); n2 = (c[0] + DX[h], c[1] + DY[h]); seen.add(n2); st.append(n2)
    # 2 entradas a la sala, en lados distintos
    bordes = [(c, h) for c in sala for h in range(4) if (c[0] + DX[h], c[1] + DY[h]) not in sala]
    lados = rnd.sample(range(4), 2)
    for ld in lados:
        abre(*rnd.choice([b for b in bordes if b[1] == ld]))
    # bucles: quita paredes internas fuera de la sala
    for c in list(W):
        for h in (0, 1):
            n2 = (c[0] + DX[h], c[1] + DY[h])
            if n2 in W and W[c][h] and c not in sala and n2 not in sala and rnd.random() < bucles:
                abre(c, h)
    return W

def pista_real():
    """La pista de las fotos (pista.py), con y hacia arriba como el simulador. Devuelve (W, meta)."""
    W = {(x, N - 1 - y): p for (x, y), p in G["pista_celdas"]().items()}
    return W, (G["PISTA_META"][0], N - 1 - G["PISTA_META"][1])


class Mapa:
    """Paredes como lineas de la reticula: v[k][j] pared en x = k*C entre y j*C..(j+1)*C; h[i][k] en y = k*C."""
    def __init__(s, W):
        s.v = [[(k == 0 or k == N) or W[(k - 1, j)][1] for j in range(N)] for k in range(N + 1)]
        s.h = [[(k == 0 or k == N) or W[(i, k - 1)][0] for k in range(N + 1)] for i in range(N)]
        s.poste = [[any(s._toca(a, b)) for b in range(N + 1)] for a in range(N + 1)]
    def _toca(s, a, b):
        yield b > 0 and s.v[a][b - 1]; yield b < N and s.v[a][b]
        yield a > 0 and s.h[a - 1][b]; yield a < N and s.h[a][b]
    def vw(s, k, y):  # pared vertical en linea k a la altura y
        j = int(y // C)
        return 0 <= k <= N and 0 <= j < N and s.v[k][j]
    def hw(s, x, k):
        i = int(x // C)
        return 0 <= k <= N and 0 <= i < N and s.h[i][k]
    def dentro(s, x, y):
        """Punto dentro de una pared o poste (o fuera de la pista)."""
        if x < MED or y < MED or x > N * C - MED or y > N * C - MED: return True
        k, l = round(x / C), round(y / C)
        nx, ny = abs(x - k * C) < MED, abs(y - l * C) < MED
        if nx and ny: return s.poste[k][l]
        if nx: return s.vw(k, y)
        if ny: return s.hw(x, l)
        return False
    def rayo(s, x, y, a, maxd=2000.0):
        """Distancia a la primera cara de pared/poste por el rayo (a en rad, 0 = +y, horario)."""
        dx, dy = math.sin(a), math.cos(a)
        best = maxd
        # lineas verticales
        if abs(dx) > 1e-6:
            k = math.floor(x / C) + (1 if dx > 0 else 0)
            while True:
                xf = k * C - (MED if dx > 0 else -MED)
                t = (xf - x) / dx
                if t > best: break
                if t >= 0:
                    yy = y + t * dy
                    if s.vw(k, yy): best = t; break
                k += 1 if dx > 0 else -1
                if k < 0 or k > N: break
        if abs(dy) > 1e-6:
            k = math.floor(y / C) + (1 if dy > 0 else 0)
            while True:
                yf = k * C - (MED if dy > 0 else -MED)
                t = (yf - y) / dy
                if t > best: break
                if t >= 0:
                    xx = x + t * dx
                    if s.hw(xx, k): best = t; break
                k += 1 if dy > 0 else -1
                if k < 0 or k > N: break
        return best

# contorno del robot (cuadrado 120, esquinas R30), marco del robot: x derecha, y adelante, centro = eje
CONTORNO = []
for i in range(4):
    cx, cy = (30 if i in (0, 3) else -30), (30 if i < 2 else -30)
    a0 = [0, 90, 180, 270][i]
    for k in range(4):
        a = math.radians(a0 + 30 * k)
        CONTORNO.append((cx + 30 * math.cos(a), cy + 30 * math.sin(a)))
# el chasis va adelantado: TOF_F_Y 54 al frente; el eje esta ~6 mm atras del centro geometrico


TOFS = [(-43, 40, -math.pi / 2), (0, 54, 0.0), (43, 40, math.pi / 2)]   # izq, frente, der (marco robot)

# ---------- Parametros (sketch + fisica) ----------
BASE = dict(
    # sketch
    MS_CELDA=700, MS_90=250, VEL_EXPLORA=140, VEL_LENTO=100, VEL_GIRO=130, VEL_MIN=80, AJUSTE_DER=-10,
    PARED_S=120, PARED_F=55, D_FRENTE=30, D_CERCA=5, FRENA_K=2, D_LADO=41, KC=0.8, KD=0.0, RANGO=600,
    SALTO=120, N_SALTO=2, TRAS_SALTO=110, KG=2.0, ADELANTO=6, DERIVA_CORR=True,
    CHOQUE="confirma", CHOQUE_G=1.5, CHOQUE_FUERTE=2.5, CONFIRMA_MS=250, RETRO_MS=450, VEL_RETRO=110, ATORADO_MS=400,
    MPU=True, ALINEAR=True, CARRIL=True, FIX_HECHO=True, ALIN_SENSA=False, STALL=False, ESQUIVA=True, CENTRA_F=600, ABRE=True, EST="brujula", CONOCE=False, PISTA=False, ESQ=-1, AMAR_W=135, AMAR_H=150, AMAR_DX=-40, AMAR_DY=-10, AMAR_MARGEN=25, CIERRA=False, CAMBIOS=0, MANO_N=25, RUIDO=0.6, PEN=1.0,
    # python
    PARED=120, FRENTE_LIBRE=120, VOTO_MAX=5, PASILLO=3, MUESTRAS=3, AGREGA="min", CENTRO_ON=True,
    # fisica
    K_V=3.0, DEAD=40, TRACK=100.0, ASIM=0.03, TOF_SIG=0.03, TOF_FALLA=0.01, CONO=2, GYRO_BIAS=0.03,
    VIB="normal", T_MAX=480.0,
    # no idealidades (0 = ideal): caida de bateria, error ToF, motores
    SAG=0.0, TOF_OFF=0.0, TOF_ESC=0.0, KV_SIG=0.0, DEAD_SIG=0.0,
)

VIB = {"normal": (0.15, 0.85, 0.22), "alta": (0.5, 1.3, 0.4)}   # golpes/s al avanzar, mediana g, sigma log

class Robot:
    def __init__(s, P, W, seed):
        s.P, s.M, s.r = P, Mapa(W), random.Random(seed * 7919 + 1)
        r = s.r
        s.asim = 1 + r.gauss(-0.03, P["ASIM"])          # el izquierdo un poco mas debil (como en pista)
        s.bias = r.gauss(0, P["GYRO_BIAS"])             # grados/s de deriva del giroscopio
        s.kv = P["K_V"] * (1 + r.gauss(0, P["KV_SIG"])); s.dead = P["DEAD"] + r.gauss(0, P["DEAD_SIG"])
        s.toff = [r.gauss(0, P["TOF_OFF"]) for _ in range(3)]; s.tesc = [1 + r.gauss(0, P["TOF_ESC"]) for _ in range(3)]
        s.t = 0.0
        s.choques = s.detectados = s.falsos = s.atorones = 0
        s.contacto = False
        s.dist = [9999] * 3; s.nsalto = [0] * 3; s.tof_t = 0.0
        # esquina al azar, mirando hacia un lado abierto
        esqs = [(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)]
        esq = r.choice(esqs) if P["ESQ"] < 0 else esqs[P["ESQ"]]
        s.x, s.y = (esq[0] + .5) * C + r.gauss(0, 5), (esq[1] + .5) * C + r.gauss(0, 5)
        hs = [h for h in range(4) if not W[esq][h]]
        s.h0 = r.choice(hs)
        s.th = math.radians(90 * s.h0 + r.gauss(0, 2))  # rumbo real (rad, 0 = +y, horario)
        s.yaw = 0.0                                     # yaw del giroscopio (grados, horario)
        s.ref = 0.0
        s.th0 = s.th
        s.vL = s.vR = 0.0
        s.traj = []

    # --- sensores ---
    def tof_real(s, i):
        P, r = s.P, s.r
        px, py, a = TOFS[i]
        c, sn = math.cos(s.th), math.sin(s.th)
        x = s.x + px * c + py * sn
        y = s.y - px * sn + py * c
        d = min(s.M.rayo(x, y, s.th + a + math.radians(o)) * math.cos(math.radians(o)) for o in (-P["CONO"], 0, P["CONO"]))
        if r.random() < P["TOF_FALLA"]:
            return 9999 if r.random() < .7 else r.uniform(5, d)
        d = d * s.tesc[i] + s.toff[i] + r.gauss(0, 2 + P["TOF_SIG"] * d)
        return 9999 if d > 2000 else max(1, int(d))

    def lee_tofs(s, avanzando, f_falta):
        """Como tofLee(): cambio brusco confirmado en N_SALTO lecturas; avisa saltos."""
        ev = []
        for i in range(3):
            d = s.tof_real(i)
            brusco = abs(d - s.dist[i]) >= s.P["SALTO"]
            if not brusco: s.nsalto[i] = 0
            else:
                s.nsalto[i] += 1
                if s.nsalto[i] < s.P["N_SALTO"]: continue
                s.nsalto[i] = 0
            antes = s.dist[i]
            s.dist[i] = d
            if brusco and avanzando: ev.append((i, antes))
        return ev

    def frescos(s):
        for _ in range(3):
            s.dist = [s.tof_real(i) for i in range(3)]

    # --- movimiento ---
    def cuerpo_choca(s, x, y, th):
        c, sn = math.cos(th), math.sin(th)
        return any(s.M.dentro(x + px * c + py * sn, y - px * sn + py * c) for px, py in CONTORNO)

    def paso(s, pwmL, pwmR, dt=0.01):
        P = s.P
        sag = 1 - P["SAG"] * min(1.0, s.t / P["T_MAX"])   # bateria: menos velocidad y mas zona muerta con el tiempo
        def v(p, k): return math.copysign(max(0, abs(p) - s.dead / sag) * s.kv * sag * k, p)
        tl, tr = v(pwmL, s.asim), v(pwmR, 1.0)
        a = 1 - math.exp(-dt / 0.05)                    # motores: 50 ms de constante de tiempo
        s.vL += (tl - s.vL) * a; s.vR += (tr - s.vR) * a
        vv = (s.vL + s.vR) / 2
        w = (s.vL - s.vR) / P["TRACK"]                  # rad/s horario
        w += s.r.gauss(0, 0.02)                         # patinaje
        nth = s.th + w * dt
        nx, ny = s.x + vv * dt * math.sin(nth), s.y + vv * dt * math.cos(nth)
        if s.cuerpo_choca(nx, ny, nth):
            if not s.contacto and s.t - getattr(s, "t_cont", -9) > 1.0:
                s.choques += 1
                s.golpe = 1.0 + abs(vv) / 180 + s.r.uniform(0, .6)   # g del impacto
            s.contacto = True; s.t_cont = s.t
            s.vL = s.vR = 0
            # resbala un poco contra la pared: prueba solo girar o solo avanzar
            if not s.cuerpo_choca(s.x, s.y, nth): s.th = nth
        else:
            s.contacto = False
            s.x, s.y, s.th = nx, ny, nth
        s.n = getattr(s, 'n', 0) + 1
        if s.n % 20 == 0: s.traj.append((s.x, s.y, s.t))
        s.yaw = math.degrees(s.th - s.th0) + s.bias * s.t + s.r.gauss(0, 0.1)
        s.t += dt

    def frena(s):
        for _ in range(3): s.paso(0, 0)                  # inercia
        s.vL = s.vR = 0

    # --- comandos del sketch ---
    def girar(s, grados, alin=False):
        P = s.P
        if not alin: s.ref += grados
        dirL = 1 if grados > 0 else -1
        if not P["MPU"]:
            dur = max(abs(grados) * P["MS_90"] / 90, 30) / 1000
            t0 = s.t
            while s.t - t0 < dur: s.paso(dirL * P["VEL_GIRO"], -dirL * P["VEL_GIRO"])
            s.frena(); return
        t0 = s.t; ymov, tmov = s.yaw, s.t; aton = 0; tdes = 0
        dur = max(abs(grados) * P["MS_90"] / 90, 30) / 1000
        while True:
            if tdes:
                if s.t < tdes: s.paso(-P["VEL_MIN"], -P["VEL_MIN"]); continue
                tdes = 0; ymov, tmov = s.yaw, s.t
            if abs(s.yaw - ymov) > 2: ymov, tmov = s.yaw, s.t
            elif s.t - tmov > P["ATORADO_MS"] / 1000:
                aton += 1; s.atorones += 1
                if aton > 2: break
                tdes = s.t + 0.2; continue
            f = (s.ref - s.yaw) * dirL
            if f <= min(P["ADELANTO"], abs(grados) / 3) or s.t - t0 >= max(3 * dur, 1.5): break
            vg = (P["VEL_GIRO"] + P["VEL_MIN"]) / 2 if f < 25 else P["VEL_GIRO"]
            s.paso(dirL * vg, -dirL * vg)
        s.frena()

    def alinear(s, lim):
        if not s.P["MPU"]: return
        e = s.ref - s.yaw
        if abs(e) < 3 or abs(e) > lim: return
        s.girar(round(e), alin=True)

    def mover(s, mm, lento=False):
        """Port de control() para AVANZA. Devuelve (hecho, saltos, choque)."""
        P = s.P
        s.frescos()
        vmax = P["VEL_LENTO"] if lento else P["VEL_EXPLORA"]
        total = pedido = max(mm, 1)
        dur = max(total * P["MS_CELDA"] / C, 50) / 1000
        t_ini = s.t
        objetivo = max(s.dist[1] - total, P["D_FRENTE"]) if s.dist[1] < P["RANGO"] else -1
        saltos = 0; choque = 0; dmin = 9999; tbaja = s.t; vel = P["VEL_MIN"]
        tchoque = 0; fchoque = 0; pico = 0; tretro = 0
        ecen = None; decen = 0; tcen = 0; tpar = 0
        prox_tof = s.t; prox_vib = s.t + s.r.expovariate(VIB[P["VIB"]][0] + 1e-9)
        if P["FIX_HECHO"] and objetivo >= 0 and s.dist[1] - total < P["D_FRENTE"]:
            total = max(s.dist[1] - P["D_FRENTE"], 0)      # pared antes de lo pedido: solo cuenta lo que cabe
        st = {"total": total, "objetivo": objetivo, "t_ini": t_ini, "dur": dur}
        def falta():
            if st["objetivo"] >= 0: f = s.dist[1] - st["objetivo"]
            else: f = st["total"] - st["total"] * (s.t - st["t_ini"]) / st["dur"]
            return max(0, min(f, st["total"]))
        def faltan(fa, f):
            st["total"] += f - fa
            if s.dist[1] < P["RANGO"]:
                st["objetivo"] = max(s.dist[1] - f, P["D_FRENTE"])
                if P["FIX_HECHO"] and s.dist[1] - f < P["D_FRENTE"]:
                    st["total"] -= f - max(s.dist[1] - P["D_FRENTE"], 0)
            else:
                st["objetivo"] = -1
                st["t_ini"] = s.t - (st["total"] - f) * P["MS_CELDA"] / C / 1000
                st["dur"] = max(st["total"] * P["MS_CELDA"] / C, 50) / 1000
        def fin():
            hecho = st["total"] - falta()
            s.frena()
            return hecho, saltos, choque
        was_contact = False
        while True:
            if s.en_meta(): return fin()                # el sketch para solo al ver amarillo
            # ToF cada 33 ms
            if s.t >= prox_tof:
                prox_tof = s.t + 0.033
                f0 = falta()
                for i, antes in s.lee_tofs(True, f0):
                    if s.dist[i] > antes: saltos |= 1 << i
                    if i == 1: faltan(f0, f0)
                    elif s.dist[i] > antes and s.dist[i] >= P["PARED_S"]: faltan(f0, P["TRAS_SALTO"])
            # acelerometro: golpes de vibracion y de choque
            g = 0
            if s.t >= prox_vib:
                rate, med, sig = VIB[P["VIB"]]
                g = med * math.exp(s.r.gauss(0, sig)) if s.t - t_ini > 0.15 else 0
                prox_vib = s.t + s.r.expovariate(rate)
            if s.contacto and not was_contact: g = max(g, s.golpe)
            was_contact = s.contacto
            if P["MPU"] and P["CHOQUE"] != "no" and g:
                pico = max(pico, g)
                if not tretro and not tchoque and s.t - t_ini > 0.15 and g > P["CHOQUE_G"]:
                    if P["CHOQUE"] == "golpe":
                        if not s.contacto: s.falsos += 1
                        else: s.detectados += 1
                        choque = 1; tretro = s.t + P["RETRO_MS"] / 1000
                    else:
                        tchoque, fchoque = s.t, s.dist[1]
            if tchoque and s.t - tchoque > P["CONFIRMA_MS"] / 1000:
                trabado = fchoque - s.dist[1] < 10 if fchoque < P["RANGO"] else pico > P["CHOQUE_FUERTE"]
                tchoque = 0
                if trabado:
                    if s.contacto or s.atorado_reciente(): s.detectados += 1
                    else: s.falsos += 1
                    choque = 1; tretro = s.t + P["RETRO_MS"] / 1000
            if tretro:
                if s.t < tretro: s.paso(-P["VEL_RETRO"], -P["VEL_RETRO"]); continue
                return fin()
            t = s.t - t_ini
            if P["STALL"] and not tretro:
                if s.t - st.get("t_st", t_ini) >= 0.5:
                    if s.dist[1] < P["RANGO"] and s.dist[1] > P["PARED_F"] and st.get("f_st", 9999) - s.dist[1] < 10 \
                            and s.t - t_ini > 0.6:
                        if s.contacto or s.atorado_reciente(): s.detectados += 1
                        else: s.falsos += 1
                        choque = 1; tretro = s.t + P["RETRO_MS"] / 1000; continue
                    st["t_st"], st["f_st"] = s.t, s.dist[1]
            paredF = s.dist[1] < P["PARED_F"]
            if s.dist[1] < dmin - 3: dmin = s.dist[1]; tbaja = s.t
            if paredF and s.t - tbaja > 0.3: return fin()
            if s.dist[1] <= P["D_FRENTE"]:
                if s.dist[1] < P["D_FRENTE"] - P["D_CERCA"] and t < st["dur"] + 0.8:
                    s.paso(-P["VEL_MIN"], -P["VEL_MIN"]); continue
                return fin()
            if st["objetivo"] < 0 and s.dist[1] < P["RANGO"]:
                fa = falta()
                st["objetivo"] = max(s.dist[1] - fa, P["D_FRENTE"])
                if P["FIX_HECHO"] and s.dist[1] - fa < P["D_FRENTE"]:
                    st["total"] -= fa - max(s.dist[1] - P["D_FRENTE"], 0)
            f = falta()
            if f <= 0 or t > 3 * st["dur"]: return fin()
            if st["total"] - f > pedido + P["TRAS_SALTO"]: return fin()
            zona = C / 4
            tope = P["VEL_MIN"] + (vmax - P["VEL_MIN"]) * f / zona if f < zona else vmax
            if s.dist[1] < P["D_FRENTE"] + 100: tope = min(tope, P["VEL_MIN"] + P["FRENA_K"] * (s.dist[1] - P["D_FRENTE"]))
            vel = min(vel + 6, tope)
            # centrado
            L, R = s.dist[0] < P["PARED_S"], s.dist[2] < P["PARED_S"]
            e = 0
            if L and R: e = s.dist[0] - s.dist[2]
            elif L: e = 2 * (s.dist[0] - P["D_LADO"])
            elif R: e = 2 * (P["D_LADO"] - s.dist[2])
            if not P["CARRIL"]: L = R = False; e = 0
            if not (L or R): tcen = 0; decen = 0
            elif not tcen: tcen, ecen, decen = s.t, e, 0
            elif s.t - tcen >= 0.1:
                decen = (e - ecen) / (s.t - tcen); ecen, tcen = e, s.t
            corr = max(-40, min(40, P["KC"] * e + P["KD"] * decen)) + P["AJUSTE_DER"] / 2
            if P["MPU"] and P["KG"]:
                corr += max(-20, min(20, P["KG"] * (s.yaw - s.ref)))
                if P["DERIVA_CORR"] and L and R and abs(e) < 15 and abs(decen) < 15:
                    if not tpar: tpar = s.t
                    elif s.t - tpar > 0.3:
                        d = s.yaw - s.ref
                        if abs(d) < 12: s.ref += 0.5 * d
                        tpar = s.t
                else: tpar = 0
            s.paso(vel - corr, vel + corr)

    def centra_frente(s, lim):
        """Con pared enfrente a menos de lim: avanza o retrocede hasta quedar a D_FRENTE + k celdas de ella."""
        P = s.P
        s.frescos()
        f = s.dist[1]
        if f >= lim: return
        obj = P["D_FRENTE"] + C * round((f - P["D_FRENTE"]) / C)
        t0 = s.t
        while s.t - t0 < 1.0:
            if s.t - getattr(s, "_ct", -1) >= 0.033:
                s._ct = s.t; s.lee_tofs(False, 0)
            e = s.dist[1] - obj
            if abs(e) <= 4: break
            v = P["VEL_MIN"] if abs(e) > 15 else P["VEL_MIN"] - 10
            s.paso(v if e > 0 else -v, v if e > 0 else -v)
        s.frena()

    def atorado_reciente(s):
        return s.cuerpo_choca(s.x + 3 * math.sin(s.th), s.y + 3 * math.cos(s.th), s.th)

    # --- verdad ---
    def celda_real(s):
        return int(s.x // C), int(s.y // C)
    def en_meta(s):
        cx, cy = s.x + 34 * math.sin(s.th), s.y + 34 * math.cos(s.th)
        mx, my = getattr(s, "meta", (N // 2, N // 2))
        P = s.P
        dx, dy = (P["AMAR_DX"], P["AMAR_DY"]) if P["PISTA"] else (0, 0)
        return (abs(cx - (mx + .5) * C - dx) < P["AMAR_W"] / 2 - P["AMAR_MARGEN"] and
                abs(cy - (my + .5) * C - dy) < P["AMAR_H"] / 2 - P["AMAR_MARGEN"])


def decide_alt(P, g, lect, rb, est):
    """Estrategias sin mapa de paredes: solo ToF de esta celda + rumbo del giroscopio + posicion aproximada."""
    izq, fr, der = lect
    libres = [r for r, ok in ((-1, izq >= P["PARED"]), (0, fr >= P["FRENTE_LIBRE"]), (1, der >= P["PARED"])) if ok]
    if not libres: return 2
    est["n"] += 1
    if P["EST"] == "mano_cambia":
        mano = -1 if (est["n"] // P["MANO_N"]) % 2 == 0 else 1
        for r in (mano, 0, -mano):
            if r in libres: return r
    # brujula: hacia el centro con la posicion aproximada; castiga salidas ya tomadas desde esa celda aproximada
    pos, rumbo, signo = g["pos"], g["rumbo"], g["signo"]
    cx = 5 * signo[0] - pos[0] if signo[0] else 0
    cy = 5 * signo[1] - pos[1] if signo[1] else 0
    nrm = math.hypot(cx, cy) or 1
    mejor, rm = None, None
    for r in libres:
        h = (rumbo + r) % 4
        u = est["usos"].get((pos, h), 0)
        sc = (g["DX"][h] * cx + g["DY"][h] * cy) / nrm - P["PEN"] * u + rb.r.gauss(0, P["RUIDO"])
        if mejor is None or sc > mejor: mejor, rm = sc, r
    h = (rumbo + rm) % 4
    est["usos"][(pos, h)] = est["usos"].get((pos, h), 0) + 1
    return rm


def corrida(P, seed):
    if P["PISTA"]:
        W, meta = pista_real()
        W = {c: list(p) for c, p in W.items()}
        rr = random.Random(seed + 99)
        def pon(c, h, v):
            W[c][h] = v; n = (c[0] + DX[h], c[1] + DY[h])
            if n in W: W[n][(h + 2) % 4] = v
        if P["CIERRA"]:                                          # cierra la entrada de arriba del cuarto (en la foto)
            pon((7, N - 1 - 5), 0, True)
        hechos = 0
        while hechos < P["CAMBIOS"]:                             # mueve paredes internas al azar (la pista "cambio")
            c = (rr.randrange(1, N - 1), rr.randrange(1, N - 1)); h = rr.randrange(4)
            W2 = {k: list(v) for k, v in W.items()}
            pon(c, h, not W[c][h])
            vis, st = {meta}, [meta]                              # que la meta siga alcanzable desde las 4 esquinas
            while st:
                a = st.pop()
                for hh in range(4):
                    b = (a[0] + DX[hh], a[1] + DY[hh])
                    if not W[a][hh] and b not in vis: vis.add(b); st.append(b)
            if all(e in vis for e in [(0, 0), (N - 1, 0), (0, N - 1), (N - 1, N - 1)]): hechos += 1
            else: W.clear(); W.update(W2)
    else:
        W, meta = laberinto(seed), (N // 2, N // 2)
    rb = Robot(P, W, seed)
    rb.meta = meta
    g = G
    for k in ("PARED", "FRENTE_LIBRE", "VOTO_MAX", "PASILLO"):
        g[k] = P[k]
    g["CENTRO"] = 5 if P["CENTRO_ON"] else 0
    g["ESTRATEGIA"] = P["EST"] if P["EST"] in ("mapa", "pista") else "brujula"
    g["RUIDO"], g["CASTIGO"] = P["RUIDO"], P["PEN"]
    g["usos"].clear(); random.seed(seed); g["loc_inicia"]()
    if P["CONOCE"]:                                              # el usuario eligio la esquina en el menu
        esq = rb.celda_real(); v = (1 if esq[0] == 0 else -1, 1 if esq[1] == 0 else -1)
        for _ in range(rb.h0): v = (-v[1], v[0])
        g["signo"][:] = list(v)
    g["muros"].clear(); g["vistas"].clear(); g["pos"], g["rumbo"] = (0, 0), 0; g["signo"][:] = [0, 0]
    # marco: celda real -> celda de Python (rumbo inicial h0 = +y de Python)
    h0 = rb.h0; c0 = rb.celda_real()
    def a_python(c):
        dx, dy = c[0] - c0[0], c[1] - c0[1]
        for _ in range(h0): dx, dy = -dy, dx                     # rota al marco del robot
        return (dx, dy)
    desfase = 0; decisiones = 0; abre = []; est = {"n": 0, "usos": {}}
    ev = []                                                      # mismo formato REC que main.py en el robot real
    def rec(e, **d): ev.append(dict(ev=e, t=round(rb.t, 2), **d))
    rec("ini", ms_celda=P["MS_CELDA"], estrategia=P["EST"])
    def fin(ok): rec("fin", ok=ok, t_fin=round(rb.t, 1), t_meta=round(rb.t, 1) if ok else None, muros=[[*c, *p] for c, p in g["muros"].items()])
    def tof3(n):
        d = [9999] * 3; lst = [[], [], []]
        for _ in range(n):
            for _ in range(5): rb.paso(0, 0)
            rb.dist = [rb.tof_real(i) for i in range(3)]
            for i in range(3): lst[i].append(rb.dist[i])
        rec("tof", pos=list(g["pos"]), rumbo=g["rumbo"], raw=[[lst[i][k] for i in range(3)] for k in range(n)])
        if P["AGREGA"] == "min": return [min(l) for l in lst]
        return [sorted(l)[len(l) // 2] for l in lst]
    while rb.t < P["T_MAX"]:
        if rb.en_meta():
            fin(1); return dict(ok=1, t=rb.t, choques=rb.choques, det=rb.detectados, falsos=rb.falsos,
                                     desfase=desfase, dec=decisiones, traj=rb.traj, W=W, meta=meta, rec=ev)
        if P["ALIN_SENSA"]: rb.alinear(45)
        lect = tof3(P["MUESTRAS"])
        rb.t += 0.25                                              # rpc, decidir, prints
        g["anota"](*lect); g["ubica"](*lect); g["vistas"].add(g["pos"])
        if a_python(rb.celda_real()) != g["pos"]: desfase += 1
        rel = decide_alt(P, g, lect, rb, est) if P["EST"] == "mano_cambia" else g["decidir"](*lect, abre=abre if P["ABRE"] else [])
        decisiones += 1
        rec("decide", rel=rel, lect=lect, pos=list(g["pos"]), rumbo=g["rumbo"])
        # girar + verifica_giro (con MPU)
        if rel:
            rb.girar(90 * rel); rec("gira", pedido=rel, real=rel)
            if P["MPU"]:
                dev = rb.yaw - rb.ref
                if abs(dev) > 10:
                    rb.alinear(180); dev = rb.yaw - rb.ref
                k = round(dev / 90)
                if k:
                    rb.ref += 90 * k - 0; rel += k
            for _ in range(10): rb.paso(0, 0)
        g["rumbo"] = (g["rumbo"] + rel) % 4
        rumbo = g["rumbo"]
        n = P["PASILLO"] if rel == 0 and lect[0] < P["PARED"] and lect[2] < P["PARED"] else 1
        if P["ALINEAR"]: rb.alinear(45)
        t0 = rb.t; hecho, saltos, choque = rb.mover(int(C * n))
        rec("avanza", pedido=int(C * n), mm=round(hecho), dt=round(rb.t - t0, 2), saltos=saltos, choque=choque, dev=round(rb.yaw - rb.ref), pos=list(g["pos"]))
        abre = [r for r, b in ((-1, 1), (1, 4)) if saltos & b]
        if rb.en_meta(): continue
        if choque:                                                # vuelve_al_carril
            izq, _, der = tof3(2)
            gg = 0
            if min(izq, der) < 35: gg = 20 if izq < der else -20
            elif P["ESQUIVA"]: gg = 15 if rb.r.random() < .5 else -15     # sin pared cerca: un poste; prueba un lado
            if gg and P["MPU"]:
                rb.ref += gg; rb.alinear(45)
                rb.mover(50, True)
                rb.ref -= gg; rb.alinear(45)
        if P["CENTRA_F"]: rb.centra_frente(P["CENTRA_F"])
        k = round(hecho / C)
        g["loc_mueve"](k)
        for i in range(k):
            pos = g["pos"]; cel = g["celda"]
            if i:
                cel(pos)[(rumbo - 1) % 4] = cel(pos)[(rumbo + 1) % 4] = P["VOTO_MAX"]; g["vistas"].add(pos)
            sig = g["vecino"](pos, rumbo)
            cel(pos)[rumbo] = cel(sig)[(rumbo + 2) % 4] = -P["VOTO_MAX"]
            g["pos"] = sig
    fin(0)
    return dict(ok=0, t=rb.t, choques=rb.choques, det=rb.detectados, falsos=rb.falsos, desfase=desfase, dec=decisiones, traj=rb.traj, W=W, meta=meta, rec=ev)


def lote(P, seeds):
    rs = [corrida(P, s) for s in seeds]
    ok = [r for r in rs if r["ok"]]
    ts = sorted(r["t"] for r in ok)
    return dict(ok=len(ok), n=len(rs), t_med=ts[len(ts) // 2] if ts else None,
                choques=sum(r["choques"] for r in rs) / len(rs), det=sum(r["det"] for r in rs) / len(rs),
                falsos=sum(r["falsos"] for r in rs) / len(rs),
                desf=sum(1 for r in rs if r["desfase"]) / len(rs))

if __name__ == "__main__":
    P = dict(BASE)   # BASE = lo que hoy trae el codigo
    for a in sys.argv[1:]:
        k, v = a.split("="); P[k] = type(BASE[k])(v) if not isinstance(BASE[k], bool) else v == "1"
    import time; t = time.time()
    print(lote(P, range(int(os.environ.get("NS", 4)))), round(time.time() - t, 1), "s")
