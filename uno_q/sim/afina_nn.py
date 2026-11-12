"""Red neuronal chica (numpy, 2 capas x 16, ~600 pesos) que aprende simulador: parametros del sketch -> exito/choques/tiempo.
Luego busca los parametros que maximizan el puntaje en cada escenario. Uso: python3 afina_nn.py [N_MUESTRAS] [SEMILLAS]
Salida: afina_out.json (WCA, MEJOR, ROBUSTO) + tabla de sensibilidad."""
import sys, os, json, random, multiprocessing as mp
import numpy as np
import sim2d as S

# parametros a ajustar: (min, max, entero?)  -- los que se calibran en el sketch
RNG = dict(MS_CELDA=(500, 900, 1), VEL_EXPLORA=(100, 200, 1), VEL_GIRO=(100, 180, 1), VEL_MIN=(60, 110, 1),
           AJUSTE_DER=(-25, 5, 1), D_FRENTE=(25, 45, 1), D_LADO=(35, 50, 1), KC=(0.4, 1.6, 0), KG=(0.5, 4.0, 0),
           PARED_F=(45, 75, 1), SALTO=(80, 160, 1), CHOQUE_G=(1.2, 2.5, 0))
K = list(RNG)

ESC = {  # escenarios fisicos
    "MEJOR": dict(T_MAX=180.0),  # todo calibrado, sin camara (ToF solo), motores ideales
    "WCA": dict(T_MAX=180.0, SAG=0.25, TOF_OFF=8.0, TOF_ESC=0.05, KV_SIG=0.10, DEAD_SIG=8.0, ASIM=0.08, TOF_FALLA=0.03, VIB="alta", GYRO_BIAS=0.08),
}

REAL = json.load(open("real_fit.json")) if os.path.exists("real_fit.json") else None
if REAL:   # simulador calibrado con los recorridos reales; lo que no se midio conserva el supuesto WCA (pesimista)
    ESC["REAL"] = {**ESC["WCA"], **REAL["fit"]}
PEOR = "REAL" if REAL else "WCA"

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
def a_x(p): return [p[k] for k in K]

def mutar(x, rnd, s=0.12):
    return [min(max(v + rnd.gauss(0, s) * (RNG[k][1] - RNG[k][0]), RNG[k][0]), RNG[k][1]) for k, v in zip(K, x)]

def evoluciona(esc, G, N0, NG, seeds, rnd):
    """Generacion 0 al azar; luego la red propone hijos de los mejores, el simulador los califica y la red reentrena."""
    xs = muestras(N0, rnd) + [base_x()]; Y = list(lote(xs, esc, seeds)); hist = []
    nn = NN(len(K), 1)
    for g in range(G + 1):
        sc = np.array([puntaje(*y) for y in Y]); mu, sd = sc.mean(), sc.std() + 1e-9
        X = np.array([norm(x) for x in xs]); nn.fit(X, ((sc - mu) / sd)[:, None], ep=800 if g else 2000)
        if g == 0:
            n = len(X) * 4 // 5; pr = nn(X[n:])[:, 0]; z = ((sc - mu) / sd)[n:]
        top = np.argsort(-sc)[:8]
        hist.append(dict(gen=g, mejor=float(sc.max()), media=float(sc.mean()), ok=float(Y[top[0]][0]), choques=float(Y[top[0]][1]), t=float(Y[top[0]][2]), n=len(xs)))
        print(esc, "gen", g, {k: round(v, 3) for k, v in hist[-1].items()}, flush=True)
        if g == G: break
        cand = [mutar(xs[rnd.choice(top)], rnd, .12 * (1 - g / (G + 1)) + .03) for _ in range(4000)] + muestras(1000, rnd)
        P_ = nn(np.array([norm(c) for c in cand]))[:, 0]
        hijos = [cand[j] for j in np.argsort(-P_)[:NG]]
        xs += hijos; Y += list(lote(hijos, esc, seeds))
    sc = np.array([puntaje(*y) for y in Y]); b = int(np.argmax(sc))
    return xs[b], dict(hist=hist, sens=sens(nn, norm(xs[b]), mu, sd), top=[xs[i] for i in np.argsort(-sc)[:8]], sc=sc.tolist(), pred=pr.tolist(), real=z.tolist())

def sens(nn, b, mu, sd):
    base = nn(b[None])[0, 0]; d = {}
    for i, k in enumerate(K):
        m = []
        for e in (-.5, .5):
            z = b.copy(); z[i] = np.clip(z[i] + e, -1, 1); m.append(nn(z[None])[0, 0])
        d[k] = float((base - np.mean(m)) * sd)
    return d

def traza(x, esc, seed):
    r = S.corrida(a_P(x, esc), seed); return r

def grafica(out, base, ESCN):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    f = plt.figure(figsize=(17, 11)); gs = f.add_gridspec(3, 4)
    for j, e in enumerate(ESCN):
        h = out[e]["hist"]; a = f.add_subplot(gs[0, 2 * j:2 * j + 2])
        a.plot([q["gen"] for q in h], [q["mejor"] for q in h], "o-", c="C2", label="mejor de la generacion")
        a.plot([q["gen"] for q in h], [q["media"] for q in h], "s--", c="C0", label="promedio poblacion")
        a.axhline(out[e]["actual"]["score"], c="r", ls=":", label="parametros actuales")
        a.set_title(f"{e}: puntaje por generacion (exito - 0.02*choques - 0.0005*t)"); a.set_xlabel("generacion"); a.legend(fontsize=8)
    for j, e in enumerate(ESCN):
        a = f.add_subplot(gs[1, j]); s = out[e]["sens"]; ks = sorted(s, key=s.get)
        a.barh(ks, [s[k] for k in ks], color="C1"); a.set_title(f"{e}: sensibilidad (cuanto importa cada ajuste)", fontsize=9)
        a = f.add_subplot(gs[1, 2 + j]); a.scatter(out[e]["real"], out[e]["pred"], s=10); lo, hi = min(out[e]["real"]), max(out[e]["real"])
        a.plot([lo, hi], [lo, hi], "k:"); a.set_title(f"{e}: la red predice vs simulador (R2={out[e]['R2']})", fontsize=9)
    seed = 1000
    for j, (e, nom) in enumerate([(PEOR, PEOR + " actual"), (PEOR, PEOR + " afinado")]):
        x = base if j == 0 else out[PEOR]["x_mejor"]; r = traza(x, e, seed)
        a = f.add_subplot(gs[2, j]); Wl = r["W"]; N = S.N; C = S.C
        for (cx, cy), p in Wl.items():
            for h, (x0, y0, x1, y1) in enumerate([(cx, cy + 1, cx + 1, cy + 1), (cx + 1, cy, cx + 1, cy + 1), (cx, cy, cx + 1, cy), (cx, cy, cx, cy + 1)]):
                if p[h]: a.plot([x0, x1], [y0, y1], "k-", lw=1)
        tj = np.array(r["traj"]) if r["traj"] else np.zeros((0, 3))
        if len(tj): a.scatter(tj[:, 0] / C, tj[:, 1] / C, c=tj[:, 2], s=3, cmap="viridis"); a.plot(tj[0, 0] / C, tj[0, 1] / C, "g^"); 
        a.plot(r["meta"][0] + .5, r["meta"][1] + .5, "y*", ms=16, mec="k")
        a.set_title(f"{nom}: {'llego' if r['ok'] else 'NO llego'} en {r['t']:.0f}s, {r['choques']} choques", fontsize=9); a.set_aspect("equal"); a.axis("off")
    a = f.add_subplot(gs[2, 2:]); a.axis("off")
    tx = "PARAMETROS (actual -> " + PEOR + " afinado | MEJOR afinado | ROBUSTO)\n" + "\n".join(
        f"{k:12s} {S.BASE[k]!s:>6} -> {out[PEOR]['params'][k]!s:>6} | {out['MEJOR']['params'][k]!s:>6} | {out['ROBUSTO']['params'][k]!s:>6}" for k in K)
    a.text(0, 1, tx, family="monospace", va="top", fontsize=9)
    f.tight_layout(); f.savefig("afina_resumen.png", dpi=110)

def resumen(x, esc, seeds):
    seeds = list(seeds); ch_ = [seeds[i::4] for i in range(4)]       # semillas repartidas en los 4 nucleos
    with mp.Pool(4) as p: r = p.map(corre, [(x, esc, c) for c in ch_])
    ok, ch, t = np.average(r, axis=0, weights=[len(c) for c in ch_]); return dict(ok=float(ok), choques=float(ch), t=float(t), score=float(puntaje(ok, ch, t)))

if __name__ == "__main__":
    G = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    N0 = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    NG = int(sys.argv[3]) if len(sys.argv) > 3 else 16
    rnd = random.Random(1); out = {}; ESCN = ("MEJOR", PEOR); VER = range(1000, 1200)
    for e in ESCN:
        x, d = evoluciona(e, G, N0, NG, range(100, 108), rnd)
        n = len(d["pred"]); d["R2"] = round(1 - float(np.sum((np.array(d["pred"]) - np.array(d["real"])) ** 2) / np.sum(np.array(d["real"]) ** 2)), 2)
        d.pop("sc")
        cs = d.pop("top") + [base_x()]               # los mejores + los parametros actuales, con semillas frescas
        x = max(cs, key=lambda c: resumen(c, e, range(500, 530))["score"])
        d["params"] = {k: (round(v) if RNG[k][2] else round(v, 2)) for k, v in zip(K, x)}; d["x_mejor"] = [round(v, 3) for v in x]
        d["nuevo"] = resumen(a_x(d["params"]), e, VER); d["actual"] = resumen(base_x(), e, VER)
        out[e] = d
        print(e, "VERIFICADO (30 semillas nuevas) actual:", d["actual"], "afinado:", d["nuevo"], flush=True)
    cand = {"MEJOR": a_x(out["MEJOR"]["params"]), PEOR: a_x(out[PEOR]["params"])}
    rob = []
    for n_, c in cand.items():
        r = [resumen(c, e, VER) for e in ESCN]; rob.append((min(q["score"] for q in r), n_, c, r))
    m, n_, c, r = max(rob, key=lambda z: z[0])
    out["ROBUSTO"] = dict(params={k: (round(v) if RNG[k][2] else round(v, 2)) for k, v in zip(K, c)}, base=n_, resultados=dict(zip(ESCN, r)))
    print("ROBUSTO", out["ROBUSTO"])
    if REAL: out["sim_vs_real"] = dict(real=REAL["real"], sim_actual=out[PEOR]["actual"])   # que tanto se parece el simulador a la pista
    grafica(out, base_x(), ESCN)
    json.dump(out, open("afina_out.json", "w"), indent=1)
