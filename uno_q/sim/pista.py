"""Pista real (fotos del 12-nov), 11 x 11 celdas de 18 cm, vista desde la foto 3 (el que toma la foto abajo).
Coordenadas: x de izquierda a derecha, y de arriba (lado opuesto al fotografo) hacia abajo, 0..11 en lineas de reticula.
H: paredes horizontales (linea y, de x a x+1). V: paredes verticales (linea x, de y a y+1). Los muros exteriores van aparte.
Corregir aqui si algo no coincide con la pista."""
N = 11
H = {1: [1, 3, 4, 5, 7, 10], 2: [2, 3, 4, 7, 8, 9, 10], 3: [3, 4, 5, 8, 9, 10], 4: [1, 2, 5, 9, 10],
     5: [0, 1, 5, 6, 10], 6: [0, 4, 9], 7: [1, 3], 8: [1, 5, 7], 9: [4, 5, 6, 10], 10: [4, 6, 8, 9]}
V = {1: [1, 3, 6, 8, 10], 2: [0, 1, 2, 6, 9, 10], 3: [0, 4, 5, 7, 9, 10], 4: [4, 5, 7, 8], 5: [2, 5, 6, 7, 10],
     6: [1, 3], 7: [1, 3, 4, 5, 8], 8: [3, 5, 6, 7, 9], 9: [0, 4, 6, 8, 9], 10: [5, 6, 8, 9]}
META = (6, 6)            # amarillo (columna, fila) en estas coordenadas
ESQUINAS = {"abajo-der": (10, 10), "abajo-izq": (0, 10), "arriba-izq": (0, 0), "arriba-der": (10, 0)}


def celdas():
    """{(x, y): [N, E, S, O]} con True = pared; N = hacia arriba de la foto (y - 1)."""
    W = {(x, y): [y == 0, x == N - 1, y == N - 1, x == 0] for x in range(N) for y in range(N)}
    for y, xs in H.items():
        for x in xs:
            if y > 0: W[(x, y - 1)][2] = True
            if y < N: W[(x, y)][0] = True
    for x, ys in V.items():
        for y in ys:
            if x > 0: W[(x - 1, y)][1] = True
            if x < N: W[(x, y)][3] = True
    return W
