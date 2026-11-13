"""Prueba de cuadrar(): el robot real de main.py (cuadrar, cuadra_angulo) contra un sketch simulado, en celdas al azar
de la pista y chueco hasta +-25 grados. Uso: python3 barrido.py [n]"""
import sys, math, random
import sim2d as S
G, C = S.G, S.C
W, _ = S.pista_real()
rnd = random.Random(1)
res, nada, peor = [], 0, 0
for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 1000):
    rb = S.Robot(dict(S.BASE, ESQ=0), W, rnd.randrange(10 ** 6))
    cel, h, err = (rnd.randrange(11), rnd.randrange(11)), rnd.randrange(4), rnd.uniform(-25, 25)
    rb.x, rb.y = (cel[0] + .5) * C + rnd.gauss(0, 8), (cel[1] + .5) * C + rnd.gauss(0, 8)
    rb.th = math.radians(90 * h + err)
    rb.th0, rb.ref, rb.yaw = rb.th, 0.0, 0.0
    def rpc(nombre, *a):
        if nombre == "ajustar":
            if a[0]: rb.ref = rb.yaw + a[0]
            return 1
        if nombre == "alinear":
            if rb.cuerpo_choca(rb.x, rb.y, rb.th): return 0
            rb.alinear(a[0]); return 0
        if nombre == "odo":
            if a[0] == 16: return round((rb.yaw - rb.ref) * 10)
            return rb.tof_real({6: 0, 5: 1, 7: 2}[a[0]])
        return 0
    G["rpc"], G["esperar"] = rpc, lambda *a: None
    G["time"] = type("T", (), {"sleep": staticmethod(lambda s: None), "time": staticmethod(lambda: 0)})
    msgs = []
    G["print"] = lambda *a, **k: msgs.append(a[0])
    G["cuadrar"]()
    fin = abs((math.degrees(rb.th) - 90 * h + 180) % 360 - 180)
    peor += fin > max(abs(err), 5) + 3
    if "sin pared" in msgs[-1]: nada += 1
    else: res.append(fin)
res.sort(); n = len(res)
print(f"cuadro {n}, sin pared clara {nada}; error final mediana {res[n // 2]:.1f} p90 {res[int(n * .9)]:.1f} peor {res[-1]:.1f} grados; quedo peor que antes: {peor}")
assert res[n // 2] < 3 and res[int(n * .9)] < 8 and peor < (n + nada) // 50
