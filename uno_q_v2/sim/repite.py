"""Reproduce una corrida grabada (datos/logs/NNNN_..._crudo.csv) contra el mapa, con la localizacion real de main.py:
en cada decision imprime lo que el robot vio, donde creia estar (las 3 mejores hipotesis) y que decidio.
Uso: python3 repite.py archivo_crudo.csv     |     python3 repite.py --prueba  (graba una corrida simulada y la repite)"""
import sys
import sim2d as S
G = S.G
REL = {1: "derecha", 0: "frente", -1: "izquierda", 2: "media vuelta"}


def repite(lineas, ver=print):
    G["print"] = lambda *a, **k: ver("   ", *a)
    G["loc_inicia"]()
    G["rumbo"] = 0
    n_s = 0
    for ln in lineas:
        t, tipo, *v = ln.strip().split(",")
        if tipo == "S":
            n_s += 1
        elif tipo == "D":
            izq, fr, der, x, y, rumbo, rel = (int(float(a)) for a in v)
            G["rumbo"] = rumbo
            G["loc_observa"]((izq, fr, der))
            top = sorted(G["creencia"].items(), key=lambda kv: -kv[1])[:3]
            ver(f"{float(t):6.1f} s  vio izq {izq} frente {fr} der {der} -> celdas libres {G['leidas']((izq, fr, der))}; decidio {REL[rel]}; "
                + ("cree estar en " + ", ".join(f"{c} viendo {'NESO'[(h0 + rumbo) % 4]} ({p:.0%})" for (c, h0), p in top) if top else "sin mapa (brujula)"))
        elif tipo == "G":                # tras girar: el avance que sigue va con el rumbo nuevo
            G["rumbo"] = int(v[1])
        elif tipo == "M":
            mm, n, pared = int(float(v[0])), int(v[1]), v[2] == "1"
            G["loc_mueve"](n, pared)
            ver(f"{float(t):6.1f} s  avanzo {mm} mm = {n} celdas" + (", pared enfrente" if pared else "")
                + (f", se abrio {v[3]}" if v[3] != "0" else "") + (f", empezo pared {v[4]}" if v[4] != "0" else ""))
    ver(f"{n_s} lecturas crudas; se perdio {G['perdidas']} veces")
    return max(G["creencia"].items(), key=lambda kv: kv[1])[0] if G["creencia"] else None


if __name__ == "__main__":
    if sys.argv[1] != "--prueba":
        repite(open(sys.argv[1]))
    else:                                # graba D y M de una corrida simulada; al repetirla debe creer lo mismo
        filas, dec, mue = [], G["decidir"], G["loc_mueve"]
        def decidir(*l, **k):
            rel = dec(*l, **k)
            filas.append(f"0,D,{l[0]},{l[1]},{l[2]},0,0,{G['rumbo']},{rel}")
            return rel
        def mueve(k, pared=False):
            filas.extend([f"0,G,0,{G['rumbo']}", f"0,M,{k * 180},{k},{int(pared)},0,0"])
            mue(k, pared)
        G["decidir"], G["loc_mueve"] = decidir, mueve
        r = S.corrida(dict(S.BASE, PISTA=True, EST="pista", ESQ=1, H0=3), 3)
        fin = max(G["creencia"].items(), key=lambda kv: kv[1])[0]
        G["loc_mueve"] = mue
        assert repite(filas, ver=lambda *a: None) == fin, "la repeticion no cree lo mismo que la corrida"
        repite(filas[:8])
        print("OK: la repeticion termina creyendo lo mismo que la corrida", fin, r)
