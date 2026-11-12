import sim2d as S, sys, json, multiprocessing as mp, os
def uno(a):
    P, sd = a; return S.corrida(P, sd)
def lote(P, n):
    with mp.Pool(4) as pool: rs = pool.map(uno, [(P, s) for s in range(n)])
    ok = [r for r in rs if r["ok"]]; ts = sorted(r["t"] for r in ok)
    return dict(ok=round(100*len(ok)/n), t_med=round(ts[len(ts)//2]) if ts else None,
                choq=round(sum(r["choques"] for r in rs)/n, 1), falsos=round(sum(r["falsos"] for r in rs)/n, 2),
                desf=round(100*sum(1 for r in rs if r["desfase"])/n))
def parse(args, base):
    P = dict(base)
    for a in args:
        k, v = a.split("="); P[k] = type(S.BASE[k])(v) if not isinstance(S.BASE[k], bool) else v == "1"
    return P
if __name__ == "__main__":
    n = int(os.environ.get("NS", 200)); base = parse(os.environ.get("BASEP", "").split(), S.BASE) if os.environ.get("BASEP") else dict(S.BASE)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        P = parse(line.split() if line != "-" else [], base)
        print(f"{line:40s}", lote(P, n), flush=True)
