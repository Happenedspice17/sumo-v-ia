"""Reconstruye por donde fue el robot en una corrida grabada: el camino mas probable sobre el mapa de la pista que
cuadra con lo que vieron los ToF en cada decision y con cada avance, que sale de una esquina y termina en el amarillo
(Viterbi con el mismo modelo que la localizacion de main.py). Es una reconstruccion, no una medicion.
Uso: python3 reconstruye.py corridas/corrida2.csv [salida.json]"""
import sys, math, json
import sim2d as S
G = S.G
PN, PDX, PDY, META = G["PN"], G["PDX"], G["PDY"], G["PISTA_META"]


def lee(ruta):
    """[{t, lect, rumbo, rel, tg, rumbo2, tm, mm, n, pared}] por decision, y eventos [(t, texto)]."""
    pasos, ev = [], []
    for ln in open(ruta):
        t, tipo, *v = ln.strip().split(",", 2)[:2] + ln.strip().split(",")[2:]
        t = float(t)
        if tipo == "D":
            pasos.append(dict(t=t, lect=[int(v[0]), int(v[1]), int(v[2])], rumbo=int(v[5]), rel=int(v[6])))
        elif tipo == "G":
            pasos[-1].update(tg=t, rumbo2=int(v[1]))
        elif tipo == "M":
            pasos[-1].update(tm=t, mm=int(v[0]), n=int(v[1]), pared=v[2] == "1")
        elif tipo == "E":
            ev.append((t, ",".join(v)))
    return pasos, ev


def ve(c, h, lect):
    """log de que tan bien cuadra lo que vieron los ToF en la celda c viendo hacia h."""
    p = 1.0
    for rel, o in zip((-1, 0, 1), G["leidas"](lect)):
        m = G["tramo"](c, (h + rel) % 4, G["VE"])
        p *= 0.7 if m == o else 0.25 if 0 < o < m else 0.1 if o == m + 1 else 0.03
    return math.log(p)


def camino(pasos):
    """Estado = (celda, rumbo real). Un giro puede fallar un cuarto de vuelta (5 % a cada lado), un avance puede
    quedar una celda corto o largo, y al perderse el rumbo puede haber cambiado. Devuelve (logp, [(celda, rumbo)])."""
    G["loc_inicia"]()
    esq = ((0, 0), (PN - 1, 0), (0, PN - 1), (PN - 1, PN - 1))
    sc = {(c, h): ve(c, h, pasos[0]["lect"]) for c in esq for h in range(4)}
    atras = []
    for i, p in enumerate(pasos):
        nv, bp = {}, {}
        for (c, h), s in sc.items():
            ops = []
            if "tm" not in p:                          # perdido: barrio en su lugar; el rumbo pudo quedar en otro cuarto
                ops = [((c, h), 0.8), ((c, (h + 1) % 4), 0.1), ((c, (h - 1) % 4), 0.1)]
            else:
                k = max(p["n"], 0)
                for dh, wh in ((0, 0.9), (1, 0.05), (-1, 0.05)):
                    h2 = (h + p["rel"] + dh) % 4
                    run = G["tramo"](c, h2, k + 4)
                    if p["pared"]:
                        ks = [(run, 0.7 if abs(run - k) <= 1 else 0.2 if run - k <= 3 else 0.02)]
                    else:
                        ks = [(min(kk, run), w) for kk, w in ((k, 0.6), (k - 1, 0.17), (k + 1, 0.17), (k + 2, 0.06)) if kk >= 0]
                    ops += [(((c[0] + PDX[h2] * kk, c[1] + PDY[h2] * kk), h2), wh * w) for kk, w in ks]
            for d, w in ops:
                v = s + math.log(w)
                if i + 1 < len(pasos):
                    v += ve(d[0], d[1], pasos[i + 1]["lect"])
                if v > nv.get(d, -1e18):
                    nv[d], bp[d] = v, (c, h)
        sc = nv
        atras.append(bp)
    fin = [(v, k) for k, v in sc.items() if k[0] == META]
    if not fin:
        return None
    v, k = max(fin)
    cs = [k]
    for bp in reversed(atras):
        cs.append(bp[cs[-1]])
    return v, cs[::-1]


if __name__ == "__main__":
    pasos, ev = lee(sys.argv[1])
    r = camino(pasos)
    assert r, "ningun camino desde una esquina hasta el amarillo cuadra con el log"
    logp, cs = r
    print(f"salida {cs[0][0]} viendo {'NESO'[cs[0][1]]}; log-verosimilitud {logp:.1f} en {len(pasos)} decisiones")
    for p, (a, h), b in zip(pasos, cs, cs[1:]):
        print(f"{p['t']:6.1f} s {a} viendo {'NESO'[h]} vio {G['leidas'](p['lect'])} mapa "
              f"{[G['tramo'](a, (h + r) % 4, G['VE']) for r in (-1, 0, 1)]} -> {b[0]} {'NESO'[b[1]]}" + ("" if "tm" in p else "  (perdido)"))
    if len(sys.argv) > 2:
        W = G["pista_celdas"]()
        json.dump(dict(n=PN, meta=META, estados=cs, eventos=ev, pasos=pasos,
                       muros=[[x, y, W[(x, y)]] for x in range(PN) for y in range(PN)]), open(sys.argv[2], "w"))
