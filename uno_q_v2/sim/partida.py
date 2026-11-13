"""Orden de partida: llega/tiempo por esquina y rumbo en la pista real. Uso: python3 partida.py 300 normal|tontos [PARAM=valor ...]
tontos = vibracion alta, ToF con el doble de ruido y 3 % de fallas, deriva x3, 2 paredes cambiadas, y tambien saliendo viendo a una pared."""
import sys, multiprocessing as mp
import sim2d as S
def uno(a): return S.corrida(*a)
NOM = {0: "abajo-izq", 1: "abajo-der", 2: "arriba-izq", 3: "arriba-der"}   # en la foto
HN = {0: "arriba", 1: "derecha", 2: "abajo", 3: "izquierda"}             # sim: 0=+y = arriba en la foto
N = int(sys.argv[1]); modo = sys.argv[2]
extra = dict(VIB="alta", TOF_SIG=0.06, TOF_FALLA=0.03, GYRO_BIAS=0.1, CAMBIOS=2) if modo == "tontos" else {}
for a in sys.argv[3:]:                   # PARAM=valor del simulador
    k, v = a.split("="); extra[k] = v == "1" if isinstance(S.BASE[k], bool) else type(S.BASE[k])(v)
W, _ = S.pista_real()
esqs = [(0, 0), (10, 0), (0, 10), (10, 10)]
with mp.Pool(4) as pool:
    for e in range(4):
        for h in range(4):
            abierta = not W[esqs[e]][h]
            if modo != "tontos" and not abierta: continue
            P = dict(S.BASE, PISTA=True, EST="pista", ESQ=e, H0=h, **extra)
            rs = pool.map(uno, [(P, s) for s in range(N)])
            ok = [r for r in rs if r["ok"]]; ts = sorted(r["t"] for r in ok)
            print(f"{NOM[e]:10s} foto{(esqs[e][0], 10 - esqs[e][1])} viendo {HN[h]:9s} {'' if abierta else '(a pared)'} "
                  f"llega {100*len(ok)//N}% t_med {round(ts[len(ts)//2]) if ts else None}s t_p90 {round(ts[int(len(ts)*.9)]) if ts else None}s "
                  f"choq {sum(r['choques'] for r in rs)/N:.1f} perd {sum(r['perd'] for r in rs)/N:.2f} "
                  f"se_perdio {sum(1 for r in rs if r['perd'])} y_llego {sum(1 for r in rs if r['perd'] and r['ok'])} brujula {sum(r['brujula'] for r in rs)}", flush=True)
