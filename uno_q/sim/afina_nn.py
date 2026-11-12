"""Red neuronal chica (numpy, 2 capas x 16, ~600 pesos) que aprende simulador: parametros del sketch -> exito/choques/tiempo.
Luego busca los parametros que maximizan el puntaje en cada escenario. Uso: python3 afina_nn.py [N_MUESTRAS] [SEMILLAS]
Salida: afina_out.json (WCA, MEJOR, ROBUSTO) + tabla de sensibilidad."""
import sys, json, random, multiprocessing as mp
import numpy as np
import sim2d as S

# parametros a ajustar: (min, max, entero?)  -- los que se calibran en el sketch
RNG = dict(MS_CELDA=(500, 900, 1), VEL_EXPLORA=(100, 200, 1), VEL_GIRO=(100, 180, 1), VEL_MIN=(60, 110, 1),
           AJUSTE_DER=(-25, 5, 1), D_FRENTE=(25, 45, 1), D_LADO=(35, 50, 1), KC=(0.4, 1.6, 0), KG=(0.5, 4.0, 0),
           PARED_F=(45, 75, 1), SALTO=(80, 160, 1), CHOQUE_G=(1.2, 2.5, 0))
K = list(RNG)

ESC = {  # escenarios fisicos
    "MEJOR": dict(),  # todo calibrado, sin camara (ToF solo), motores ideales
    "WCA": dict(SAG=0.25, TOF_OFF=8.0, TOF_ESC=0.05, KV_SIG=0.10, DEAD_SIG=8.0, ASIM=0.08, TOF_FALLA=0.03, VIB="alta", GYRO_BIAS=0.08),
}

def a_P(x, esc):
    P = dict(S.BASE); P.update(ESC[esc])
    for k, v in zip(K, x):
        lo, hi, i = RNG[k]; P[k] = int(round(v)) if i else float(v)
    P["VEL_MIN"] = min(P["VEL_MIN"], P["VEL_EXPLORA"] - 10)
    return P

def corre(a):
    x, esc, seeds = a
    rs = [S.corrida(a_P(x, esc), s) for s in seeds]
    ok = np.mean([r["ok"] for r in rs]); ch = np.mean([r["choques"] for r in rs])
    t = np.mean([r["t"] if r["ok"] else S.BASE["T_MAX"] for r in rs])
    return ok, ch, t

def puntaje(ok, ch, t):  # exito domina; luego choques; luego tiempo
    return ok - 0.02 * ch - 0.0005 * t

def lote(xs, esc, seeds):
    with mp.Pool(4) as p: return np.array(p.map(corre, [(x, esc, seeds) for x in xs]))

class NN:
    def __init__(s, n_in, n_out, h=16, seed=0):
        r = np.random.default_rng(seed)
        s.W = [r.normal(0, .5, (n_in, h)), r.normal(0, .5, (h, h)), r.normal(0, .5, (h, n_out))]; s.b = [np.zeros(h), np.zeros(h), np.zeros(n_out)]
    def f(s, x):
        a = [x]
        for i in range(2): a.append(np.tanh(a[-1] @ s.W[i] + s.b[i]))
        return a, a[-1] @ s.W[2] + s.b[2]
    def __call__(s, x): return s.f(x)[1]
    def fit(s, X, Y, ep=3000, lr=0.02):
        m = [np.zeros_like(w) for w in s.W + s.b]; v = [np.zeros_like(w) for w in s.W + s.b]
        for e in range(1, ep + 1):
            a, y = s.f(X); d = 2 * (y - Y) / len(X)
            gW = [None] * 3; gb = [None] * 3
            for i in (2, 1, 0):
                gW[i] = a[i].T @ d; gb[i] = d.sum(0)
                if i: d = (d @ s.W[i].T) * (1 - a[i] ** 2)
            ps = s.W + s.b
            for j, g in enumerate(gW + gb):  # Adam
                m[j] = .9 * m[j] + .1 * g; v[j] = .999 * v[j] + .001 * g * g
                ps[j] -= lr * (m[j] / (1 - .9 ** e)) / (np.sqrt(v[j] / (1 - .999 ** e)) + 1e-8)

def norm(x): return np.array([(x[i] - RNG[k][0]) / (RNG[k][1] - RNG[k][0]) for i, k in enumerate(K)]) * 2 - 1

def muestras(n, rnd):
    return [[rnd.uniform(RNG[k][0], RNG[k][1]) for k in K] for _ in range(n)]

def base_x(): return [S.BASE[k] for k in K]

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    NSD = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    rnd = random.Random(1); out = {}
    for esc in ("MEJOR", "WCA"):
        xs = muestras(N, rnd) + [base_x()]
        Y = lote(xs, esc, range(100, 100 + NSD))
        X = np.array([norm(x) for x in xs]); sc = np.array([puntaje(*y) for y in Y])
        nn = NN(len(K), 1); mu, sd = sc.mean(), sc.std() + 1e-9
        ntr = int(.8 * len(X)); nn.fit(X[:ntr], ((sc - mu) / sd)[:ntr, None])
        pred = nn(X[ntr:])[:, 0]; r2 = 1 - np.sum((pred - ((sc - mu) / sd)[ntr:]) ** 2) / np.sum(((sc - mu) / sd)[ntr:] ** 2)
        nn.fit(X, ((sc - mu) / sd)[:, None], ep=1500)
        # busqueda sobre la red: muchos candidatos baratos, se verifican los mejores en el simulador
        cand = muestras(20000, rnd); P_ = nn(np.array([norm(c) for c in cand]))[:, 0]
        top = [cand[i] for i in np.argsort(-P_)[:12]]
        ver = lote(top, esc, range(1000, 1000 + 3 * NSD))
        sv = [puntaje(*y) for y in ver]; best = top[int(np.argmax(sv))]
        bx = lote([base_x()], esc, range(1000, 1000 + 3 * NSD))[0]
        out[esc] = dict(params={k: (round(v) if RNG[k][2] else round(v, 2)) for k, v in zip(K, best)},
                        R2_val=round(float(r2), 2), nuevo=dict(zip(("ok", "choques", "t"), map(float, ver[int(np.argmax(sv))]))),
                        actual=dict(zip(("ok", "choques", "t"), map(float, bx))))
        # sensibilidad: cuanto cae el puntaje predicho al mover cada parametro +-25% de su rango
        b = norm(best); sens = {}
        for i, k in enumerate(K):
            d = []
            for e in (-.5, .5):
                z = b.copy(); z[i] = np.clip(z[i] + e, -1, 1); d.append(nn(z[None])[0, 0] * sd + mu)
            sens[k] = round(float(nn(b[None])[0, 0] * sd + mu - np.mean(d)), 3)
        out[esc]["sensibilidad"] = dict(sorted(sens.items(), key=lambda kv: -kv[1]))
        print(esc, json.dumps(out[esc], indent=1), flush=True)
    # robusto: un solo juego de parametros que funcione en ambos (promedio ponderado, peor caso manda)
    cand = [list(out[e]["params"].values()) for e in out] + muestras(40, rnd)
    rob = []
    for c in cand:
        r = [puntaje(*lote([c], e, range(2000, 2000 + 3 * NSD))[0]) for e in ESC]; rob.append((min(r), c))
    m, c = max(rob, key=lambda z: z[0])
    out["ROBUSTO"] = dict(params={k: (round(v) if RNG[k][2] else round(v, 2)) for k, v in zip(K, c)}, peor_puntaje=round(m, 3))
    print("ROBUSTO", out["ROBUSTO"])
    json.dump(out, open("afina_out.json", "w"), indent=1)
