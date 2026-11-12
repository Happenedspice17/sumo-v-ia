"""Que tan bueno tiene que ser el robot: cada no-idealidad sola (de ideal a peor caso) y su aporte al fallo del WCA.
Salida: objetivos.json = tolerancia maxima por factor (el exito cae menos de TOL puntos del ideal) + especificacion combinada.
Uso: python3 objetivos.py [SEMILLAS=100]"""
import sys, json, multiprocessing as mp
import numpy as np
import sim2d as S
from afina_nn import ESC, base_x, a_P

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
TOL = 0.08                                   # puntos de exito que se aceptan perder contra el ideal (ruido de 100 semillas ~ 4)
SEEDS = list(range(3000, 3000 + N))
FACT = {   # nombre: (parametro del simulador, niveles de ideal a peor caso, unidad para mostrar)
    "Bateria: caida de velocidad al final": ("SAG", [0, .10, .20, .25], "fraccion"),
    "ToF: sesgo por sensor": ("TOF_OFF", [0, 3, 6, 8], "mm"),
    "ToF: error de escala": ("TOF_ESC", [0, .02, .05], "fraccion"),
    "ToF: lecturas malas": ("TOF_FALLA", [0, .01, .03, .05], "fraccion"),
    "Motores: asimetria izq/der": ("ASIM", [.03, .05, .08, .12], "fraccion"),
    "Motores: variacion de K_V": ("KV_SIG", [0, .05, .10, .15], "fraccion"),
    "Motores: zona muerta": ("DEAD_SIG", [0, 4, 8, 12], "PWM"),
    "Giroscopio: deriva": ("GYRO_BIAS", [.03, .05, .08, .12], "grados/s"),
}
IDEAL = dict(T_MAX=180.0)
WCA = ESC["WCA"]

def una(a):
    over, seeds = a
    P = a_P(base_x(), "MEJOR"); P.update(over)
    rs = [S.corrida(P, s) for s in seeds]
    return [r["ok"] for r in rs], [r["choques"] for r in rs]

def evalua(over):
    ch = [SEEDS[i::4] for i in range(4)]
    with mp.Pool(4) as p: r = p.map(una, [(over, c) for c in ch])
    ok = np.mean(sum((q[0] for q in r), [])); choq = np.mean(sum((q[1] for q in r), []))
    return float(ok), float(choq)

if __name__ == "__main__":
    out = dict(n=N, tol=TOL, factores={}, ablacion={})
    ideal = evalua(IDEAL); wca = evalua(WCA); out["ideal"], out["wca"] = ideal, wca
    print("ideal", ideal, "wca", wca, flush=True)
    for nom, (k, niv, un) in FACT.items():
        res = [dict(valor=v, ok=evalua({**IDEAL, k: v})[0]) for v in niv]
        # nivel mas alto que todavia pierde menos de TOL (los niveles estan ordenados de ideal a peor)
        pasa = [r["valor"] for r in res if r["ok"] >= ideal[0] - TOL]
        out["factores"][nom] = dict(param=k, unidad=un, niveles=res, max_ok=max(pasa) if pasa else None)
        sin = evalua({**WCA, k: IDEAL.get(k, S.BASE[k])})
        out["ablacion"][nom] = dict(ok=sin[0], choques=sin[1], mejora=sin[0] - wca[0])   # WCA con ese factor corregido
        print(nom, [(r["valor"], round(r["ok"], 2)) for r in res], "max", out["factores"][nom]["max_ok"], "| WCA sin el:", round(sin[0], 2), flush=True)
    esp = {f["param"]: f["max_ok"] for f in out["factores"].values() if f["max_ok"] is not None}
    for _ in range(4):   # todos a la vez: si junto ya no pasa, se aprieta cada uno un nivel
        r = evalua({**IDEAL, **esp}); print("espec", esp, r, flush=True)
        if r[0] >= ideal[0] - TOL: break
        for f in out["factores"].values():
            v = [x["valor"] for x in f["niveles"]]
            if f["param"] in esp and v.index(esp[f["param"]]) > 0: esp[f["param"]] = v[v.index(esp[f["param"]]) - 1]
    out["especificacion"] = dict(valores=esp, ok=r[0], choques=r[1])
    json.dump(out, open("objetivos.json", "w"), indent=1)
