"""Logs REC del robot (consola o recorridos/*.jsonl) -> mapa virtual (mapa_real.png) + calibracion del simulador (real_fit.json).
Uso:  python3 logs2nn.py carpeta_o_archivos...      (5 a 10 recorridos reales)
      python3 logs2nn.py --sim 6                    (prueba: 6 recorridos simulados en WCA, mismo formato)
Despues: python3 afina_nn.py  -> si existe real_fit.json entrena con el simulador calibrado (escenario REAL) y 800 semillas."""
import sys, json, glob, os
import numpy as np

DX, DY = [0, 1, 0, -1], [1, 0, -1, 0]
PARED, LATERAL_PASILLO = 120, 82          # pasillo 168 mm - 2 x 43 mm de la posicion de los ToF laterales

def carga(ruta):
    ev = []
    for l in open(ruta):
        i = l.find("REC ")
        try: ev.append(json.loads(l[i + 4:] if i >= 0 else l))
        except ValueError: pass
    return ev

def recorridos(rutas):
    """Una lista de eventos por corrida (cada 'ini' abre una nueva)."""
    runs = []
    for r in rutas:
        for e in carga(r):
            if e["ev"] == "ini": runs.append([])
            if runs: runs[-1].append(e)
    return [r for r in runs if any(e["ev"] == "fin" for e in r)]

def resumen(run):
    fin = next(e for e in run if e["ev"] == "fin"); av = [e for e in run if e["ev"] == "avanza"]
    gi = [e for e in run if e["ev"] == "gira"]
    return dict(ok=fin["ok"], t=fin["t_fin"], choques=sum(e["choque"] for e in av), giros_mal=sum(e["pedido"] != e["real"] for e in gi),
                avances=len(av), dev_med=float(np.mean([abs(e["dev"]) for e in av])) if av else 0.0)

def calibra(runs):
    """Estima de los logs lo que el simulador necesita. Lo que no se puede medir queda fuera (usa el supuesto WCA)."""
    sig, fall, tot, bias, vt = [], 0, 0, [], []
    for run in runs:
        b = []
        for e in run:
            if e["ev"] != "tof": continue
            raw = np.array(e["raw"], float)
            for j in range(3):
                c = raw[:, j]; m = np.median(c); tot += len(c)
                mal = (c >= 2000) | (np.abs(c - m) > 60) if m < 500 else np.zeros(len(c), bool)
                fall += mal.sum(); bueno = c[~mal]
                if 40 < m < 600 and len(bueno) >= 2: sig.append((bueno.std(ddof=1) - 2) / m)
            med = np.median(raw, axis=0)
            if med[0] < PARED and med[2] < PARED: b.append((med[0] + med[2] - LATERAL_PASILLO) / 2)
        if b: bias.append(np.mean(b))
        av = [e for e in run if e["ev"] == "avanza" and e["mm"] >= 150 and e["dt"] > 0]
        if len(av) >= 4:
            v = np.array([e["mm"] / e["dt"] for e in av]); vt += list(zip([e["t"] for e in av], v / v.mean()))
    fit = {}
    if sig: fit["TOF_SIG"] = round(float(max(0.0, np.median(sig))), 3)      # mediana: las fallas (9999, saltos) no cuentan
    if tot: fit["TOF_FALLA"] = round(float(fall / tot), 3)
    if bias: fit["TOF_OFF"] = round(float(np.sqrt(np.mean(np.square(bias)))), 1)
    if len(vt) >= 10:   # velocidad relativa vs tiempo de corrida; x0.7 por la zona muerta (dv/v = dsag * VEL/(VEL-DEAD)); x180 = T_MAX de afina_nn
        t, v = np.array(vt).T; fit["SAG"] = round(float(np.clip(-np.polyfit(t, v, 1)[0] * 0.7 * 180, 0, 0.5)), 3)
    return fit

def mapa(runs, salida="mapa_real.png"):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    n = len(runs); c = min(n, 5); f, ax = plt.subplots((n + c - 1) // c, c, figsize=(3.6 * c, 3.8 * ((n + c - 1) // c)), squeeze=False)
    for a in ax.flat: a.axis("off")
    for a, run in zip(ax.flat, runs):
        fin = next(e for e in run if e["ev"] == "fin"); s = resumen(run)
        for m in fin["muros"]:
            x, y = m[0], m[1]
            for h, v in enumerate(m[2:6]):
                if v > 0: a.plot(*zip(*[((x, y + 1), (x + 1, y + 1)), ((x + 1, y), (x + 1, y + 1)), ((x, y), (x + 1, y)), ((x, y), (x, y + 1))][h]), "k-", lw=1.2)
        av = [e for e in run if e["ev"] == "avanza"]
        p = np.array([(0, 0)] + [e["pos"] for e in av], float) + .5
        a.plot(p[:, 0], p[:, 1], "-", c="C0", lw=1, alpha=.6); a.scatter(p[:, 0], p[:, 1], c=range(len(p)), s=9, cmap="viridis", zorder=3)
        a.plot(*p[0], "g^")
        for e in av:
            if e["choque"]: a.plot(e["pos"][0] + .5, e["pos"][1] + .5, "rx", ms=8)
        a.set_aspect("equal"); a.set_title(f"{'META' if s['ok'] else 'sin meta'} {s['t']}s  choques {s['choques']}  giros mal {s['giros_mal']}", fontsize=8)
    f.tight_layout(); f.savefig(salida, dpi=100)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--sim"]:                         # prueba sin robot: mismos eventos que main.py
        import sim2d as S, afina_nn as A
        os.makedirs("recorridos_sim", exist_ok=True); rutas = []
        for k in range(int(a[1])):
            P = dict(S.BASE); P.update(A.ESC["WCA"]); r = S.corrida(P, 7000 + k)
            rutas.append(f"recorridos_sim/run{k}.jsonl")
            with open(rutas[-1], "w") as f: f.writelines("REC " + json.dumps(e) + "\n" for e in r["rec"])
    else:
        rutas = [q for x in a for q in (sorted(glob.glob(x + "/*.jsonl")) if os.path.isdir(x) else [x])]
    runs = recorridos(rutas)
    assert runs, "no hay corridas completas (con evento fin) en los logs"
    R = [resumen(r) for r in runs]
    real = dict(n=len(R), ok=float(np.mean([r["ok"] for r in R])), t=float(np.mean([r["t"] for r in R])),
                choques=float(np.mean([r["choques"] for r in R])), giros_mal=float(np.mean([r["giros_mal"] for r in R])),
                dev_med=float(np.mean([r["dev_med"] for r in R])))
    out = dict(fit=calibra(runs), real=real, corridas=R)
    json.dump(out, open("real_fit.json", "w"), indent=1); mapa(runs)
    print(json.dumps(out, indent=1))
