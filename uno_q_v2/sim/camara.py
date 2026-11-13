"""Prueba de la vision de main.py (cam_puntos, cam_ve) en poses al azar de la pista: centro de celda +-10 mm, +-4 grados.
1) Con el modelo rapido de camara del simulador (Robot.cam_pts): miles de poses.
2) Con una IMAGEN binaria dibujada (blanco = pared) que pasa por cam_puntos, como la foto real: pocas poses (es lento).
Uso: python3 camara.py [PARAM=valor ...]   (p. ej. CAM_PX=2 CAM_INCL_ERR=2)"""
import sys, math, random
import numpy as np
import sim2d as S
G, C = S.G, S.C
W, _ = S.pista_real(); Wf = G["pista_celdas"](); PDX, PDY = G["PDX"], G["PDY"]
extra = {}
for a in sys.argv[1:]:
    k, v = a.split("="); extra[k] = v == "1" if isinstance(S.BASE[k], bool) else type(S.BASE[k])(v)
P = dict(S.BASE, ESQ=0, **extra)
rb = S.Robot(P, W, 1)


def imagen():
    """Lo que veria la camara: un pixel es blanco si entre el lente y su punto del piso hay una pared."""
    b = np.zeros((G["ALTO"], G["ANCHO"]), bool)
    c, sn = math.cos(rb.th), math.sin(rb.th)
    lx, ly = rb.x + G["CAM_Y0"] * sn, rb.y + G["CAM_Y0"] * c
    for v in range(0, G["ALTO"], 2):
        for u in range(0, G["ANCHO"], 2):
            q = G["cam_piso"](u, v)
            if q is None: continue
            x, y = q[0], q[1] - G["CAM_Y0"]
            b[v:v + 2, u:u + 2] = rb.M.rayo(lx, ly, rb.th + math.atan2(x, y)) < math.hypot(x, y)
    return b


def mide(n, con_imagen, rnd):
    st = dict(frente_ok=0, frente_mal=0, frente_sin=0, lados_ok=0, lados_mal=0, lados_sin=0, ang_sin=0); aerr = []
    for _ in range(n):
        cf, h, err = (rnd.randrange(11), rnd.randrange(11)), rnd.randrange(4), rnd.gauss(0, 4)
        rb.x, rb.y = (cf[0] + .5) * C + rnd.gauss(0, 10), (10 - cf[1] + .5) * C + rnd.gauss(0, 10)
        rb.th = math.radians(90 * h + err); rb.incl_err = rnd.gauss(0, P["CAM_INCL_ERR"])
        pts = G["cam_puntos"](imagen()) if con_imagen else rb.cam_pts()
        if not pts: continue
        v = G["cam_ve"](pts)
        libres, c = 0, cf
        while not Wf[c][h] and libres < G["VE_CAM"]: c = (c[0] + PDX[h], c[1] + PDY[h]); libres += 1
        st["frente_sin" if v["frente"] is None else "frente_ok" if v["frente"] == libres else "frente_mal"] += 1
        nn = cf
        for j in (1, 2):
            if j > libres: break
            nn = (nn[0] + PDX[h], nn[1] + PDY[h])
            for o, rel in zip(v["lados"][j], (-1, 1)):
                st["lados_sin" if o is None else "lados_ok" if o == Wf[nn][(h + rel) % 4] else "lados_mal"] += 1
        if v["ang"] is None: st["ang_sin"] += 1
        else: aerr.append(abs(v["ang"] + err))
    aerr.sort()
    print(st, "| error de angulo: mediana %.1f, p90 %.1f grados" % (aerr[len(aerr) // 2], aerr[int(len(aerr) * .9)]) if aerr else "")
    return st


if __name__ == "__main__":
    for q in [(0, 200), (-84, 300), (84, 150), (30, 600)]:           # ida y vuelta de la geometria
        b = G["cam_piso"](*G["cam_pixel"](*q)); assert abs(b[0] - q[0]) < 1e-6 and abs(b[1] - q[1]) < 1e-6
    print("modelo rapido:"); a = mide(3000, False, random.Random(5))
    print("imagen dibujada:"); b = mide(40, True, random.Random(6))
    for s in (a, b):
        assert s["frente_ok"] > 9 * s["frente_mal"] and s["lados_ok"] > 6 * s["lados_mal"], "la camara se equivoca demasiado"
    print("OK")
