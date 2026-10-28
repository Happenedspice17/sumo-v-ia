// Chasis robot laberinto (Arduino Nano / ATmega328P) - 120 x 120 mm con ruedas
// Origen: centro del eje de las ruedas, a nivel del piso. X derecha, Y adelante, Z arriba.
//
// PIEZA: "ensamble", "piso1", "piso2", "cuna_motor", "capucha_color", "patin", "espaciador", "prueba",
//        "placa" (todas las piezas acomodadas en la cama de la X2D), "placa_vista" (igual, con la cama),
//        "sub_piso2" (piso 2 armado en la mesa), "det_motor", "det_l298", "marca" (esfera en MARCA)
// PASO:  1-10 muestra el ensamble hasta ese paso; lo de pasos anteriores sale en gris. 0 = completo a color
//
// Los sensores se insertan sin tornillos:
//   VL53L0X: header recto, pines hacia adentro; bajan por las ranuras de su soporte en el piso 1.
//   TCS34725: entra deslizando por atras de la capucha; sus cables suben por dentro de ella
//   OLED: se acuesta en su marco del piso 2 con los pines hacia abajo
//   Protoboards: entran en su marco del piso 2
// Todos los cables estan modelados con su ruta; cable() imprime "CABLE|nombre|color|mm" para la lista de cables.

PIEZA = "ensamble";
PASO = 0;
MARCA = [0, 0, 0];
UNIDO = false;           // det_arnes: conector T unido

$fn = 48;
$gris = false;

// ---------- Tolerancias: Bambu Lab A2L, boquilla 0.4, capa 0.2, PLA/PETG ----------
// En la A2L (cama movil) los agujeros salen ~0.1 mm chicos y las ranuras ~0.15 mm angostas;
// las medidas de abajo ya lo compensan. Antes de imprimir todo, imprime PIEZA="prueba".
HOLGURA = 0.2;                 // juego por lado entre pieza impresa y componente
RANURA = 1.6 + 0.4;            // ranura para un PCB de 1.6 mm
M3_PASO = 3.4;                 // M3 pasante (tornillo + tuerca)
M3_ROSCA = 2.8;                // M3 que se atornilla directo al plastico
D_BOTON = 7 + 2 * 0.15;        // boton de panel de 7 mm
D_SWITCH = 6 + 2 * 0.15;       // interruptor de palanca MTS-102 (6 mm)

// Cama de impresion: Bambu Lab X2D, 256 x 256 (boquilla principal)
CAMA = 256;
MARGEN = 6;

// ---------- Medidas generales ----------
L = 120;            // lado maximo con ruedas
R_ESQ = 30;         // radio de esquinas (deja girar en un pasillo de 180)
ESP = 3;            // espesor de pisos

// Ruedas y motores N20
D_RUEDA = 34;
A_RUEDA = 20;
MOT_L = 24;         // caja + motor
MOT_A = 12;         // ancho (Y)
MOT_H = 10;         // alto (Z)
EJE_Z = D_RUEDA / 2;
X_RUEDA_INT = L / 2 - A_RUEDA;           // 40
X_MOT_EXT = X_RUEDA_INT - 1.5;           // cara de la caja de engranes
X_MOT = X_MOT_EXT - MOT_L / 2;           // centro del motor
X_MOT_INT = X_MOT_EXT - MOT_L;           // cara de las terminales (14.5)
POZO_X = X_RUEDA_INT - 2;                // hueco de la rueda en el piso 1
POZO_Y = 19;

// Pisos
Z1 = EJE_Z + MOT_H / 2;                  // fondo del piso 1 (toca el motor)
SEP = 35;                                // separadores M3 hembra-hembra
Z2 = Z1 + ESP + SEP;                     // fondo del piso 2
POSTES = [[42, 50], [-42, 50], [44, -46], [-44, -46]];

// Componentes
BAT = [65, 37, 19];      // 2S 18650 acostada a lo ancho (X, Y, Z)
BAT_Y = 7;               // sobre el eje: deja libres los pasillos de los conectores de los VL53L0X
BAT_PARED = 8;           // alto de los topes que la sujetan
L298 = [43, 43, 27];
L298_Y = -37.5;          // 4.5 mm entre su borde y la bateria para doblar los cables de potencia
L298_AG = 37;            // separacion de agujeros del L298N (medir el suyo)
L298_Z = Z1 + ESP + 5;   // cara de abajo de su PCB (sobre espaciadores de 5 mm)
BORNE_Z = L298_Z + 1.6 + 4;              // altura de entrada de los cables a los bornes
TOF = [25, 10.7];        // VL53L0X CJVL53L0XV2 (ancho, alto)
TOF_FRENTE_Y = 54;
TOF_LADO = [50, 34.5];   // (X, Y) de los soportes laterales
HEADER = [2.5, 6, 1.4];  // header recto: plastico, pin largo, punta corta que sale del lado del chip
COLOR_MOD = 20.5;        // TCS34725 morado (medir el suyo)
COLOR_Y = 34;
COLOR_Z = 5;             // altura de la cara del sensor sobre el suelo
PATIN_Y = -52;
PROTO = [35, 47, 9.5];   // mini protoboard 170 puntos (X, Y, Z)
PROTO_Y = -32.6;
NANO = [17.8, 44];
OLED = [27.3, 27.8];     // PCB del OLED 0.96" (medir el suyo)
OLED_Y = 39.4;           // pines hacia atras, sobre el hueco entre bateria y conector frontal
BOTON_XY = [-38, 5];
SWITCH_XY = [38, 5];
PASO_PIN = 2.54;
DUPONT = [2.5, 14];      // conector dupont (lado, largo)
CABLE = 1.4;             // diametro del cable dupont
CABLE_POT = 1.8;         // calibre 22 con forro de silicon (bateria, interruptor, motores)
RAN2_X = 26.5;           // ranuras laterales de cables del piso 2 (centro X)
T_CON = [13, 12.7, 7];   // conector T (Deans): cada mitad (X, Y, Z)
T_POS = [-25, 10, Z1 + ESP + BAT[2]];    // conector T acostado sobre la bateria (borde izq, centro Y, fondo)

OLED_PINES_Y = OLED_Y - OLED[1] / 2 + 2.5;
TOF_PIN_Z = TOF[1] - 1.3;                // fila de pines del VL53L0X, medida desde su borde de abajo
TOF_ATRAS = 0.3 + HEADER[0] + DUPONT[1]; // del centro de la ranura al final del dupont (16.8)
TOF_SUBE = 50 - Z1 - ESP - TOF_PIN_Z;    // el cable frontal sube a 50 mm y va a la ranura derecha

// Protoboards: tiras de 5 hoyos a lo ancho (X), 17 columnas a lo largo (Y)
XP = PROTO[0] / 2 + 1.1;                 // centro X de cada protoboard (Nano en -XP, bus en +XP)
ZP = Z2 + ESP + PROTO[2];                // cara de arriba de las protoboards
function hx(c, k) = c + sign(k) * (3.81 + PASO_PIN * (abs(k) - 1));   // hoyo k (1 = junto al canal)
function hy(j) = PROTO_Y + (j - 8) * PASO_PIN;                         // columna j (16 = adelante)
NANO_A = hx(-XP, 2);                     // fila de pines A0..A7, 5V, GND, VIN
NANO_D = hx(-XP, -3);                    // fila de pines D2..D12
NANO_X = (NANO_A + NANO_D) / 2;
function pin_nano(i) = hy(1 + i);        // i = 0 junto al USB (atras)
BUS = [13, 16, 7, 10];                   // columnas del bus: 5V, GND, SDA, SCL (mismo orden que los pines del Nano)
function z_bus(l) = ZP + 16 + (16 - BUS[l]) / 3 * 1.7;   // altura del cable que llega a la linea l

// ---------- Utilidades ----------
function k(c) = $gris ? "gainsboro" : c;
function lon(p, i = 0) = i >= len(p) - 1 ? 0 : norm(p[i + 1] - p[i]) + lon(p, i + 1);

module cuadrado_redondo(l, r, h) {
  linear_extrude(h) offset(r) square(l - 2 * r, center = true);
}

module agujero(d, h) { translate([0, 0, -0.5]) cylinder(d = d, h = h + 1); }

module avellanado() { translate([0, 0, ESP - 1.6]) cylinder(d1 = M3_PASO, d2 = 6.6, h = 1.61); }

// Paso del ensamble: no aparece antes de su paso; en pasos posteriores sale en gris
module paso(p) {
  $gris = PASO > p;
  if (PASO == 0 || PASO >= p) children();
}

module gris() { $gris = true; children(); }

// Cable que pasa por una lista de puntos
module cable(pts, col, d = CABLE, nombre = "") {
  if (nombre != "") echo(str("CABLE|", nombre, "|", col, "|", round(lon(pts))));
  color(k(col)) for (i = [0 : len(pts) - 2]) hull() {
    translate(pts[i]) sphere(d = d, $fn = 8);
    translate(pts[i + 1]) sphere(d = d, $fn = 8);
  }
}

// ---------- Piezas impresas ----------

// Soporte de VL53L0X: dos postes y un canal abajo, todo con ranura; el modulo baja desde arriba
// con el chip a +Y. Entre los postes queda libre el header recto (atras, arriba).
module soporte_tof() {
  a = TOF[0] + 2 * HOLGURA;
  h = TOF[1] + 1.5;
  difference() {
    union() {
      for (s = [-1, 1]) translate([s * (a / 2 + 0.5) - 2, -2.5, 0]) cube([4, 5, h]);
      translate([-a / 2 - 1.5, -2.5, 0]) cube([a + 3, 5, 2]);                 // canal del borde de abajo
    }
    translate([-a / 2, 0.5 - RANURA / 2, -1]) cube([a, RANURA, 20]);
    // entrada abocinada arriba
    hull() {
      translate([-a / 2, 0.5 - RANURA / 2, h - 1.5]) cube([a, RANURA, 0.01]);
      translate([-a / 2 - 0.8, 0.5 - RANURA / 2 - 0.8, h]) cube([a + 1.6, RANURA + 1.6, 0.01]);
    }
  }
}

module piso1() {
  difference() {
    union() {
      cuadrado_redondo(L, R_ESQ, ESP);
      translate([0, 0, ESP]) {
        translate([0, TOF_FRENTE_Y, 0]) soporte_tof();
        for (s = [-1, 1]) translate([s * TOF_LADO[0], TOF_LADO[1], 0]) rotate([0, 0, -s * 90]) soporte_tof();
        // topes de la bateria; fuera de los pasillos de los conectores y de los bornes del L298N
        xb = BAT[0] / 2 + HOLGURA + 1;
        yb = BAT[1] / 2 + HOLGURA + 1;
        for (s = [-1, 1]) {
          for (y = [-1, 1]) translate([s * xb, BAT_Y + y * (yb - 6), BAT_PARED / 2]) cube([2, 10, BAT_PARED], center = true);
          translate([s * 26, BAT_Y - yb, BAT_PARED / 2]) cube([8, 2, BAT_PARED], center = true);
          translate([s * 14, BAT_Y + yb, BAT_PARED / 2]) cube([8, 2, BAT_PARED], center = true);
        }
      }
    }
    for (s = [-1, 1]) translate([s * (POZO_X + 25), 0, ESP / 2]) cube([50, 2 * POZO_Y, ESP + 2], center = true);
    for (s = [-1, 1]) translate([s * 27, -24, ESP / 2]) cube([10, 10, ESP + 2], center = true);  // cables de motores
    translate([0, COLOR_Y - 4.5, ESP / 2]) cube([14, 6, ESP + 2], center = true);       // cables del TCS34725
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    for (s = [-1, 1]) for (y = [-1, 1])
      translate([s * X_MOT, y * (MOT_A / 2 + 3), 0]) { agujero(M3_PASO, ESP); avellanado(); }   // cunas: avellanados, bajo la bateria
    for (x = [-1, 1]) for (y = [-1, 1])
      translate([x * L298_AG / 2, L298_Y + y * L298_AG / 2, 0]) agujero(M3_PASO, ESP); // L298N
    // patin y capucha: avellanados (el del patin queda bajo el L298N)
    translate([0, PATIN_Y, 0]) { agujero(M3_PASO, ESP); avellanado(); }
    for (x = [-1, 1]) translate([x * 17, COLOR_Y, 0]) { agujero(M3_PASO, ESP); avellanado(); }
  }
}

module piso2() {
  ap = PROTO[0] + 2 * 0.3;
  lp = PROTO[1] + 2 * 0.3;
  ao = [OLED[0] + 2 * 0.3, OLED[1] + 2 * 0.3];
  difference() {
    union() {
      cuadrado_redondo(L, R_ESQ, ESP);
      translate([0, 0, ESP]) {
        // marco para dos protoboards (Nano a la izquierda, bus I2C a la derecha)
        translate([0, PROTO_Y, 2]) difference() {
          cube([2 * ap + 3 * 1.6, lp + 3.2, 4], center = true);
          for (s = [-1, 1]) translate([s * (ap / 2 + 0.8), 0, 0]) cube([ap, lp, 6], center = true);
          translate([-(ap / 2 + 0.8), -lp / 2, 0]) cube([12, 6, 6], center = true);   // salida del USB
        }
        // marco del OLED
        translate([0, OLED_Y, 1.5]) difference() {
          cube([ao[0] + 3.2, ao[1] + 3.2, 3], center = true);
          cube([ao[0], ao[1], 4], center = true);
        }
      }
    }
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    translate([0, OLED_PINES_Y, ESP / 2]) cube([13, 4.5, ESP + 2], center = true);               // pines del OLED
    translate([0, OLED_Y + 3, ESP / 2]) cube([20, 14, ESP + 2], center = true);                  // aligera
    translate([0, -3, ESP / 2]) cube([60, 6, ESP + 2], center = true);                           // cables de abajo
    for (s = [-1, 1]) translate([s * RAN2_X, TOF_LADO[1], ESP / 2]) cube([16, 22, ESP + 2], center = true); // cables de sensores
    translate([BOTON_XY[0], BOTON_XY[1], 0]) agujero(D_BOTON, ESP);
    translate([SWITCH_XY[0], SWITCH_XY[1], 0]) agujero(D_SWITCH, ESP);
  }
}

module cuna_motor() {
  // aprieta el motor contra el piso 1; 0.3 mm mas baja que el motor para que apriete
  difference() {
    translate([-8, -MOT_A / 2 - 6, 0]) cube([16, MOT_A + 12, 2 + MOT_H - 0.3]);
    translate([-9, -MOT_A / 2 - HOLGURA, 2]) cube([18, MOT_A + 2 * HOLGURA, MOT_H + 1]);
    for (y = [-1, 1]) translate([0, y * (MOT_A / 2 + 3), 0]) agujero(M3_ROSCA, 20);   // M3 avellanado desde el piso 1
  }
}

// Capucha del sensor de color: el TCS34725 entra deslizando por atras (cara del sensor hacia abajo)
// y queda atrapado en una ranura. Al frente lleva el patin delantero.
module capucha_color() {
  h = Z1 - 2;                         // de 2 mm sobre el suelo hasta el piso 1
  a = COLOR_MOD + 2 * HOLGURA;        // ranura del modulo
  v = a - 3;                          // ventana: deja 1.5 mm de apoyo por lado
  z0 = COLOR_Z - 2;                   // fondo de la ranura, medido desde el borde de la capucha
  difference() {
    union() {
      translate([-a / 2 - 2, -a / 2 - 2, 0]) cube([a + 4, a + 4, h]);
      translate([-22, -5, h - 6]) cube([44, 10, 6]);                         // orejas
      translate([0, a / 2 + 4, 3.5]) {                                       // patin delantero, 0.5 mm sobre el suelo
        cylinder(d = 10, h = h - 3.5);
        sphere(d = 10);
      }
    }
    translate([-v / 2, -v / 2, -1]) cube([v, v, h + 2]);                     // ventana de luz
    translate([-a / 2, -a / 2 - 3, z0]) cube([a, a + 3, RANURA]);            // ranura, abierta atras
    translate([-v / 2, -a / 2 - 3, z0]) cube([v, 4 + (a - v) / 2, h]);       // salida de cables: suben por dentro
    for (x = [-1, 1]) translate([x * 17, 0, h - 6]) agujero(M3_ROSCA, 6);
  }
}

module patin() {
  // apoyo deslizante trasero; deja 0.5 mm al suelo. Se atornilla con M3 avellanado desde el piso 1
  h = Z1 - 0.5;
  difference() {
    translate([0, 0, 0.5]) {
      translate([0, 0, 5]) cylinder(d = 10, h = h - 5);
      translate([0, 0, 5]) sphere(d = 10);
    }
    translate([0, 0, Z1 - 10]) cylinder(d = M3_ROSCA, h = 11);
  }
}

module espaciador(h = 5) {
  // separa el L298N del piso 1
  difference() { cylinder(d = 7, h = h); agujero(M3_PASO, h); }
}

module prueba() {
  // agujeros M3, boton, interruptor, ranura de motor y el soporte de VL53L0X
  difference() {
    cube([70, 26, 3]);
    for (i = [0 : 2]) translate([6 + i * 7, 7, 0]) agujero(3.2 + i * 0.2, 3);    // 3.2 / 3.4 / 3.6
    for (i = [0 : 1]) translate([6 + i * 7, 18, 0]) agujero(M3_ROSCA + i * 0.2, 3);
    translate([40, 8, 0]) agujero(D_BOTON, 3);
    translate([40, 19, 0]) agujero(D_SWITCH, 3);
  }
  translate([48, 0, 0]) difference() {
    cube([22, 26, 9]);
    translate([5, 13 - MOT_A / 2 - HOLGURA, 2]) cube([20, MOT_A + 2 * HOLGURA, 10]);
  }
  translate([0, -12, 0]) { cube([36, 12, 3]); translate([18, 6, 3]) soporte_tof(); }
}

// Todas las piezas (menos la de prueba) en la cama de 256 x 256 de la X2D, en su orientacion de impresion
module placa() {
  m = MARGEN;
  translate([m + L / 2, m + L / 2, 0]) piso1();
  translate([CAMA - m - L / 2, m + L / 2, 0]) piso2();
  y2 = 2 * m + L + 18;
  for (i = [0 : 1]) translate([m + 12 + i * 24, y2, 0]) cuna_motor();
  translate([95, y2 + 6, Z1 - 2]) rotate([180, 0, 0]) capucha_color();
  translate([140, y2, Z1]) rotate([180, 0, 0]) patin();
  for (i = [0 : 3]) translate([160 + i * 12, y2, 0]) espaciador();
}

// ---------- Componentes comprados (solo para el ensamble) ----------
module rueda(s) {
  translate([s * (X_RUEDA_INT + A_RUEDA / 2), 0, EJE_Z]) rotate([0, 90, 0]) {
    color(k("black")) difference() {
      cylinder(d = D_RUEDA, h = A_RUEDA, center = true);
      for (z = [-1, 1]) translate([0, 0, z * A_RUEDA / 2]) cylinder(d = D_RUEDA - 10, h = 3, center = true);
    }
    color(k("white")) cylinder(d = D_RUEDA - 10, h = A_RUEDA - 4, center = true);
  }
}

// N20: caja de engranes afuera, motor adentro; terminales y capacitor de 100 nF en la cara interior
module motor(s) {
  translate([0, 0, EJE_Z]) {
    color(k("gold")) translate([s * (X_MOT_EXT - 4.5), 0, 0]) cube([9, MOT_A, MOT_H], center = true);
    color(k("silver")) translate([s * (X_MOT_INT + 7.5), 0, 0]) intersection() {
      cube([15, MOT_A, MOT_H], center = true);
      rotate([0, 90, 0]) cylinder(d = MOT_A, h = 15, center = true);
    }
    color(k("silver")) translate([s * (X_MOT_EXT + 3), 0, 0]) rotate([0, 90, 0]) cylinder(d = 3, h = 6, center = true);
    color(k("white")) translate([s * (X_MOT_INT - 0.4), 0, 0]) cube([0.8, 9, 7], center = true);
    for (y = [-1, 1]) color(k("orange")) translate([s * (X_MOT_INT - 1.2), y * 3.5, 1]) cube([1.6, 1.2, 0.4], center = true);
    color(k("yellow")) translate([s * (X_MOT_INT - 2), 0, 2.3]) rotate([0, 90, 0]) cylinder(d = 4.5, h = 2, center = true);
  }
}

// Cables de un motor (s = -1 izquierdo, +1 derecho). final = false: solo suben por la ranura (paso 1)
module cables_motor(s, final = true) {
  nom = s < 0 ? "Motor izq" : "Motor der";
  out = s < 0 ? ["OUT1", "OUT2"] : ["OUT3", "OUT4"];
  for (i = [0 : 1]) {
    y = (i == 0 ? 1 : -1) * 3.5;
    xr = s * (27 + (i - 0.5) * 3);
    yb = L298_Y + (i == 0 ? 7.5 : 2.5);
    pts = concat([[s * (X_MOT_INT - 1.2), y, EJE_Z + 1], [s * (X_MOT_INT - 3), y, 19],
                  [s * 11, y - 3, 19], [s * 11, -27, 19], [xr, -27, 19]],
                 final ? [[xr, -27, BORNE_Z - 2], [xr, yb, BORNE_Z], [s * 21.5, yb, BORNE_Z]]
                       : [[xr, -27, 42]]);
    cable(pts, i == 0 ? "yellow" : "white", CABLE_POT, final ? str(nom, " -> ", out[i]) : "");
  }
}

module postes(z, h) {
  for (p = POSTES) color(k("silver")) translate([p[0], p[1], z]) cylinder(d = 5.5, h = h, $fn = 6);
}

// Tornillo M3 de largo l, cabeza en z = 0 y cuerpo hacia -Z. plano = avellanado
module tornillo(l, plano = false) {
  color(k("dimgray")) {
    if (plano) translate([0, 0, -1.6]) cylinder(d1 = 3, d2 = 6, h = 1.6);
    else cylinder(d = 5.5, h = 3);
    translate([0, 0, -l]) cylinder(d = 3, h = l);
  }
}

// Fila de pines con sus conectores dupont (sin cable). Pines hacia +Z desde z = 0 (cara del plastico);
// "atras" es lo que sale del otro lado. sin: indice del pin que queda sin dupont.
module pines(n, largo = 6, atras = 1, dupont = true, sin = -1) {
  for (i = [0 : n - 1]) translate([(i - (n - 1) / 2) * PASO_PIN, 0, 0]) {
    color(k("gold")) translate([-0.32, -0.32, -atras]) cube([0.64, 0.64, largo + atras]);
    if (dupont && i != sin) color(k("black")) translate([-DUPONT[0] / 2, -DUPONT[0] / 2, 0]) cube([DUPONT[0], DUPONT[0], DUPONT[1]]);
  }
}

// Dupont macho clavado en un hoyo de protoboard (h = [x, y])
module dupont_macho(h) {
  color(k("black")) translate([h[0] - DUPONT[0] / 2, h[1] - DUPONT[0] / 2, ZP]) cube([DUPONT[0], DUPONT[0], DUPONT[1]]);
  color(k("gold")) translate([h[0] - 0.32, h[1] - 0.32, ZP - 6]) cube([0.64, 0.64, 6]);
}

// Ruta de arriba: del punto p (ya sobre el piso 2) a un hoyo h de protoboard.
// Va a la altura lz, corre por el carril ly, sube a zt frente a las protoboards y baja al hoyo.
function ruta(p, h, ly, lz, zt, zfin) =
  [p, [p[0], p[1], lz], [p[0], ly, lz], [h[0], ly, lz], [h[0], ly, zt], [h[0], h[1], zt], [h[0], h[1], zfin]];

module arriba(p, h, col, ly, lz, zt, nombre = "", dupont = true) {
  cable(ruta(p, h, ly, lz, zt, dupont ? ZP + DUPONT[1] : ZP), col, dupont ? CABLE : CABLE_POT, nombre);
  if (dupont) dupont_macho(h);
}

COL_TOF = ["red", "black", "cyan", "royalblue", "white", "green"];   // VIN GND SCL SDA GPIO1 XSHUT
SEN_TOF = ["VIN", "GND", "SCL", "SDA", "GPIO1", "XSHUT"];

// Conector del VL53L0X: header recto (plastico atras), 5 dupont hacia -Y (GPIO1 sin conectar) y cables.
// recto > 0: cable recto de ese largo (prueba de choques); si no, el cable se dobla y sube "sube" mm.
// va != 0: despues de subir, los cables van de lado hasta x = va y suben "sube2" mm mas.
module tof_conector(recto = 0, sube = 14, va = 0, sube2 = 0, nombre = "") {
  y0 = -0.3 - HEADER[0];                 // cara de atras del plastico
  yd = -TOF_ATRAS;                       // final del dupont
  color(k("dimgray")) translate([-3 * PASO_PIN, y0, TOF_PIN_Z - 1.25]) cube([6 * PASO_PIN, HEADER[0], 2.5]);
  translate([0, y0, TOF_PIN_Z]) rotate([90, 0, 0]) pines(6, HEADER[1], 1.6 + HEADER[0] + HEADER[2], sin = 4);
  for (i = [0 : 5]) if (i != 4) {
    x = (i - 2.5) * PASO_PIN;
    if (recto > 0) cable([[x, yd, TOF_PIN_Z], [x, yd - recto, TOF_PIN_Z]], COL_TOF[i]);
    else {
      z = TOF_PIN_Z + sube + (va == 0 ? 0 : i * 1.5);
      xv = va + (i - 2.5) * 1.5;
      cable(concat([[x, yd, TOF_PIN_Z]],
                   [for (a = [0 : 30 : 90]) [x, yd - 1 - 3 * sin(a), TOF_PIN_Z + 3 - 3 * cos(a)]],
                   [[x, yd - 4, z]],
                   va == 0 ? [] : [[xv, yd - 4, z], [xv, yd - 4, z + sube2]]), COL_TOF[i], CABLE,
            nombre == "" ? "" : str(nombre, " ", SEN_TOF[i], " (abajo)"));
    }
  }
}

// VL53L0X con header recto: chip a +Y, pines hacia -Y en el borde de arriba
module tof_modulo(sube = 14, va = 0, sube2 = 0, nombre = "") {
  color(k("green")) translate([0, 0.5, TOF[1] / 2]) cube([TOF[0], 1.6, TOF[1]], center = true);
  color(k("black")) translate([0, 1.8, TOF[1] / 2]) cube([4.4, 1, 2.4], center = true);
  for (i = [0 : 5]) color(k("silver")) translate([(i - 2.5) * PASO_PIN, 1.3, TOF_PIN_Z]) rotate([-90, 0, 0]) cylinder(d1 = 1.8, d2 = 0.8, h = 0.8);
  tof_conector(0, sube, va, sube2, nombre);
}

COL_OLED = ["black", "red", "cyan", "royalblue"];   // GND VCC SCL SDA
SEN_OLED = ["GND", "VCC", "SCL", "SDA"];

// OLED acostado: espaciador del header dentro de la ranura y pines hacia abajo.
// recto > 0: cable recto hacia abajo (prueba de choques); si no, va a la ranura derecha del piso 2.
module oled_conector(recto = 0, nombre = "") {
  zd = -HEADER[0] - DUPONT[1];
  color(k("dimgray")) translate([0, OLED_PINES_Y, -HEADER[0] / 2]) cube([4 * PASO_PIN, 2.5, HEADER[0]], center = true);
  translate([0, OLED_PINES_Y, -HEADER[0]]) mirror([0, 0, 1]) pines(4, HEADER[1], 1.6 + HEADER[0] + HEADER[2]);
  for (i = [0 : 3]) {
    x = (i - 1.5) * PASO_PIN;
    z = zd - 3 - i * 1.6;
    if (recto > 0) cable([[x, OLED_PINES_Y, zd], [x, OLED_PINES_Y, zd - recto]], COL_OLED[i]);
    else cable([[x, OLED_PINES_Y, zd], [x, OLED_PINES_Y, z], [20 + i * 1.5, OLED_PINES_Y, z], [20 + i * 1.5, OLED_PINES_Y, 4]],
               COL_OLED[i], CABLE, nombre == "" ? "" : str(nombre, " ", SEN_OLED[i], " (abajo)"));
  }
}

module oled_modulo(nombre = "") {
  color(k("navy")) translate([0, OLED_Y, 1.5]) cube([OLED[0], OLED[1], 3], center = true);
  color(k("black")) translate([0, OLED_Y + 2, 3]) cube([26, 19, 0.6], center = true);
  oled_conector(0, nombre);
}

COL_TCS = ["red", "black", "cyan", "royalblue"];    // VIN GND SCL SDA
SEN_TCS = ["VIN", "GND", "SCL", "SDA"];

// Cables del TCS34725 (coordenadas del robot): suben por dentro de la capucha, cruzan el piso 1
// por su ranura, van a la izquierda por debajo del conector frontal y suben a la ranura del piso 2.
module tcs_cables() {
  y0 = COLOR_Y - COLOR_MOD / 2 + 1.3;
  yr = COLOR_Y - 4.5;
  for (i = [0 : 3]) {
    x = (i - 1.5) * PASO_PIN;
    z = Z1 + ESP + 2.5 + i * 1.5;
    xs = -20 - i * 1.5;
    cable([[x, y0, COLOR_Z + 2.6], [x, y0, 12], [x, yr, 18], [x, yr, z], [xs, yr, z], [xs, yr, Z2 + ESP + 4]],
          COL_TCS[i], CABLE, str("TCS34725 ", SEN_TCS[i], " (abajo)"));
  }
}

// TCS34725 (cara del sensor hacia abajo) con sus 4 cables soldados
module tcs_modulo() {
  color(k("purple")) cube([COLOR_MOD, COLOR_MOD, 1.6], center = true);
  color(k("white")) translate([0, 0, -1.3]) cube([3, 3, 1], center = true);
  for (i = [0 : 6]) color(k("silver")) translate([(i - 3) * PASO_PIN, -COLOR_MOD / 2 + 1.3, 0.8]) cylinder(d = 1.6, h = 0.2);
}

// Boton e interruptor con su cuerpo bajo el piso 2
module boton() {
  color(k("black")) cylinder(d = 10, h = 6);
  color(k("dimgray")) translate([0, 0, -ESP - 12]) cylinder(d = 7, h = 12);
  for (x = [-1, 1]) color(k("silver")) translate([x * 2 - 0.4, -1, -ESP - 17]) cube([0.8, 2, 5]);
}

module interruptor() {
  color(k("silver")) cylinder(d = 3, h = 10);
  color(k("silver")) cylinder(d = 8, h = 1.5, $fn = 6);
  color(k("dimgray")) translate([-4, -6.5, -ESP - 10]) cube([8, 13, 10]);
  for (y = [-1, 0, 1]) color(k("silver")) translate([-1, y * 4.7 - 0.25, -ESP - 15]) cube([2, 0.5, 5]);
}

// Borne de tornillo de n vias, paso 5 mm, abierto hacia +Y local (girado "giro" grados)
module borne(n, p, giro) {
  translate(p) rotate([0, 0, giro]) {
    color(k("dodgerblue")) difference() {
      translate([-n * 2.5, -3.75, 0]) cube([n * 5, 7.5, 10]);
      for (i = [0 : n - 1]) translate([(i - (n - 1) / 2) * 5, 2, 4]) cube([3.2, 4, 3.2], center = true);
    }
    for (i = [0 : n - 1]) color(k("silver")) translate([(i - (n - 1) / 2) * 5, -0.5, 9.6]) cylinder(d = 3.5, h = 0.6);
  }
}

// L298N: bornes de motores a los lados, borne de potencia y header de logica al frente (+Y), disipador atras
module l298() {
  translate([0, L298_Y, L298_Z]) {
    color(k("firebrick")) difference() {
      translate([-21.5, -21.5, 0]) cube([43, 43, 1.6]);
      for (x = [-1, 1]) for (y = [-1, 1]) translate([x * L298_AG / 2, y * L298_AG / 2, 0]) agujero(3.2, 1.6);
    }
    color(k("black")) translate([-11.5, -19.5, 1.6]) cube([23, 3, 22]);                  // chip
    color(k("dimgray")) translate([-11.5, -16.5, 1.6]) difference() {                    // disipador
      cube([23, 13, 25]);
      for (i = [0 : 4]) translate([1.5 + i * 4.5, 3, 4]) cube([2.5, 11, 22]);
    }
    for (s = [-1, 1]) borne(2, [s * (21.5 - 3.75), 5, 1.6], s < 0 ? 90 : -90);          // OUT1-2 / OUT3-4
    borne(3, [13, 21.5 - 3.75, 1.6], 0);                                                  // 5V GND 12V
    // header de logica: ENA IN1 IN2 IN3 IN4 ENB, con los pines de 5V de los jumpers atras
    for (i = [0 : 5]) translate([1 - i * PASO_PIN, 18.5, 1.6]) {
      color(k("black")) translate([-1.27, -1.27, 0]) cube([2.54, 2.54, 2.5]);
      color(k("gold")) translate([-0.32, -0.32, 0]) cube([0.64, 0.64, 8.5]);
      if (i == 0 || i == 5) translate([0, -PASO_PIN, 0]) {
        color(k("black")) translate([-1.27, -1.27, 0]) cube([2.54, 2.54, 2.5]);
        color(k("gold")) translate([-0.32, -0.32, 0]) cube([0.64, 0.64, 8.5]);
      }
    }
    color(k("black")) translate([2.6, 15.9, 1.6]) cube([2.54, 5.1, 6]);                 // jumper 5V-EN (se queda)
  }
}

module espaciadores_l298() {
  for (x = [-1, 1]) for (y = [-1, 1]) translate([x * L298_AG / 2, L298_Y + y * L298_AG / 2, 0]) {
    color(k("orange")) translate([0, 0, Z1 + ESP]) espaciador();
    translate([0, 0, L298_Z + 1.6]) tornillo(16);
    color(k("silver")) translate([0, 0, Z1 - 2.4]) cylinder(d = 6.2, h = 2.4, $fn = 6);
  }
}

// Bateria 2S: dos 18650 lado a lado; cable principal y de balanceo salen por la izquierda
module bateria() {
  translate([0, BAT_Y, Z1 + ESP]) {
    color(k("royalblue")) hull() for (y = [-1, 1]) translate([0, y * (BAT[1] / 2 - BAT[2] / 2), BAT[2] / 2])
      rotate([0, 90, 0]) cylinder(d = BAT[2], h = BAT[0], center = true);
    color(k("white")) translate([-BAT[0] / 2 + 6, BAT[1] / 2 - 0.05, 6]) cube([20, 0.1, 7]);
  }
  // cable principal al conector T macho
  for (i = [0 : 1]) {
    y = T_POS[1] + (i == 0 ? -3 : 3);
    cable([[-BAT[0] / 2, y, Z1 + ESP + 15], [-BAT[0] / 2 - 2, y, Z1 + ESP + 17], [-BAT[0] / 2 - 2, y, T_POS[2] + 2],
           [T_POS[0] - 2, y, T_POS[2] + 3.5], [T_POS[0], y, T_POS[2] + 3.5]], i == 0 ? "black" : "red", 2);
  }
  // balanceo (JST-XH de 3 pines) acostado sobre la bateria
  for (i = [0 : 2]) {
    y = 20 + (i - 1) * 1.2;
    cable([[-BAT[0] / 2, y, Z1 + ESP + 15], [-BAT[0] / 2 - 1.5, y, Z1 + ESP + 17], [-BAT[0] / 2 - 1.5, y, T_POS[2] + 2],
           [-30, y, T_POS[2] + 2]], ["black", "red", "red"][i], 1);
  }
  color(k("white")) translate([-30, 17, T_POS[2]]) cube([10, 6, 5]);
}

// Conector T (Deans): macho de la bateria y hembra del robot. unido = false: la hembra queda 6 mm aparte
module conector_t(macho = true, hembra = true, unido = true) {
  translate([T_POS[0], T_POS[1] - T_CON[1] / 2, T_POS[2]]) {
    if (macho) color(k("red")) cube(T_CON);
    if (hembra) translate([T_CON[0] + (unido ? 0 : 6), 0, 0]) color(k("crimson")) difference() {
      cube(T_CON);
      translate([-0.1, 2, 2]) cube([3, T_CON[1] - 4, 3]);
    }
  }
}

X_T = T_POS[0] + 2 * T_CON[0];           // salida de los cables de la hembra (unida)
SW_PIN = [SWITCH_XY[0], SWITCH_XY[1], Z2 - 15 + 0.5];   // punta de la pata central del interruptor

// Arnes de potencia: conector T hembra, interruptor y cables a los bornes del L298N y al Nano.
// unido = false: la hembra queda 6 mm separada (se conecta en el ultimo paso)
module arnes_potencia(unido = true) {
  dx = unido ? 0 : 6;
  zt = T_POS[2] + T_CON[2] / 2;
  // T rojo -> pata exterior del interruptor
  cable([[X_T + dx, T_POS[1] + 3, zt], [X_T + dx + 4, T_POS[1] + 3, zt], [30, T_POS[1] + 3, zt - 0.5],
         [36, SW_PIN[1] + 4.7, SW_PIN[2] + 0.5], [SW_PIN[0] - 0.5, SW_PIN[1] + 4.7, SW_PIN[2]]], "red", CABLE_POT,
        "Conector T rojo -> interruptor");
  // T negro -> GND del L298N
  cable([[X_T + dx, T_POS[1] - 3, zt], [X_T + dx + 4, T_POS[1] - 3, zt], [12.2, -4, zt - 0.5],
         [12.2, -13.8, zt - 0.5], [12.2, -13.8, BORNE_Z + 2.5], [12.2, -15, BORNE_Z], [12.2, L298_Y + 21.5, BORNE_Z]],
        "black", CABLE_POT, "Conector T negro -> L298N GND");
  // interruptor -> 12V del L298N
  cable([SW_PIN, [34, SW_PIN[1] - 1, SW_PIN[2] + 1], [18, -4, SW_PIN[2] + 1], [18, -13.8, SW_PIN[2] + 1],
         [18, -13.8, BORNE_Z + 2.5], [18, -15, BORNE_Z], [18, L298_Y + 21.5, BORNE_Z]], "orange", CABLE_POT,
        "Interruptor -> L298N 12V");
  // interruptor -> VIN del Nano (sube por la ranura central)
  cable([SW_PIN, [34, SW_PIN[1] - 2, SW_PIN[2] + 3], [27, -3, Z2 - 8], [27, -3, Z2 + ESP + 2]], "orange", CABLE_POT,
        "Interruptor -> Nano VIN (abajo)");
  // GND del L298N -> GND del Nano
  cable([[13.8, L298_Y + 21.5, BORNE_Z], [13.8, -15, BORNE_Z], [13.8, -13.8, BORNE_Z + 2.5], [13.8, -13.8, zt + 1],
         [13.5, -3, Z2 - 8], [13.5, -3, Z2 + ESP + 2]], "black", CABLE_POT, "L298N GND -> Nano GND (abajo)");
}

// Cables del header de logica del L298N: suben por la ranura central del piso 2
L298_LOG = [[1, "ENA", "mediumpurple", 7], [1 - PASO_PIN, "IN1", "sienna", 5], [1 - 2 * PASO_PIN, "IN2", "sienna", 4],
            [1 - 3 * PASO_PIN, "IN3", "sienna", 3], [1 - 4 * PASO_PIN, "IN4", "sienna", 2],
            [1 - 5 * PASO_PIN, "ENB", "mediumpurple", 6]];     // x, pin, color, pin de la fila D del Nano
NANO_D_NOM = ["D12", "D11", "D10", "D9", "D8", "D7", "D6", "D5", "D4", "D3", "D2", "GND"];

module cables_l298_logica() {
  zd = L298_Z + 1.6 + 2.5;
  for (c = L298_LOG) {
    x = c[0];
    color(k("black")) translate([x - DUPONT[0] / 2, -19 - DUPONT[0] / 2, zd]) cube([DUPONT[0], DUPONT[0], DUPONT[1]]);
    cable([[x, -19, zd + DUPONT[1]], [x, -19, zd + DUPONT[1] + 3], [x, -3, Z2 - 4], [x, -3, Z2 + ESP + 2]], c[2], CABLE,
          str("L298N ", c[1], " (abajo)"));
  }
}

// Cables del boton: de sus patas a la ranura central
module cables_boton() {
  for (i = [0 : 1]) {
    x = BOTON_XY[0] + (i == 0 ? -2 : 2);
    cable([[x, BOTON_XY[1], Z2 - 16.5], [x, BOTON_XY[1] - 4, Z2 - 15], [-28.5 + i * 1.5, -3, Z2 - 8],
           [-28.5 + i * 1.5, -3, Z2 + ESP + 2]], i == 0 ? "hotpink" : "black", CABLE, str("Boton ", i == 0 ? "D2" : "GND", " (abajo)"));
  }
}

module protoboards() {
  for (s = [-1, 1]) translate([s * XP, PROTO_Y, Z2 + ESP]) {
    color(k("white")) translate([-PROTO[0] / 2, -PROTO[1] / 2, 0]) cube(PROTO);
    color(k("silver")) for (j = [0 : 16]) for (kk = [-5 : 5]) if (kk != 0)
      translate([hx(0, kk) - 0.4, hy(j) - PROTO_Y - 0.4, PROTO[2] - 0.05]) cube([0.8, 0.8, 0.1]);
  }
}

module nano() {
  translate([NANO_X, pin_nano(7) - 1, ZP + 2.5 + 0.8]) {
    color(k("darkcyan")) cube([NANO[0], NANO[1], 1.6], center = true);
    color(k("black")) translate([0, 0, 1.3]) rotate([0, 0, 45]) cube([7, 7, 1], center = true);
    color(k("silver")) translate([0, -NANO[1] / 2 + 3.5, 2.4]) cube([9, 7.5, 3.2], center = true);
  }
  for (x = [NANO_A, NANO_D]) for (i = [0 : 14]) translate([x, pin_nano(i), ZP]) {
    color(k("black")) translate([-1.27, -1.27, 0]) cube([2.54, 2.54, 2.5]);
    color(k("gold")) translate([-0.32, -0.32, -6]) cube([0.64, 0.64, 10]);
  }
}

COL_BUS = ["red", "black", "royalblue", "cyan"];
NOM_BUS = ["5V", "GND", "SDA", "SCL"];
NANO_A_BUS = [11, 13, 7, 8];             // pin de la fila A del Nano para 5V, GND, A4 (SDA), A5 (SCL)

// Puentes de la protoboard: unen las dos mitades de cada columna del bus y llevan 5V, GND, SDA y SCL del Nano
module puentes() {
  for (l = [0 : 3]) {
    y = hy(BUS[l]);
    cable([[hx(XP, -1), y, ZP], [hx(XP, -1), y, ZP + 2], [hx(XP, 1), y, ZP + 2], [hx(XP, 1), y, ZP]], COL_BUS[l], 0.8,
          str("Puente bus ", NOM_BUS[l]));
    yn = pin_nano(NANO_A_BUS[l]);
    cable([[hx(-XP, 3), yn, ZP], [hx(-XP, 3), yn, ZP + 2], [hx(XP, -5), y, ZP + 2], [hx(XP, -5), y, ZP]], COL_BUS[l], 0.8,
          str("Puente Nano ", ["5V", "GND", "A4", "A5"][l], " -> bus ", NOM_BUS[l]));
  }
}

// Linea del bus de cada color de cable de sensor
function linea(c) = c == "red" ? 0 : c == "black" ? 1 : c == "royalblue" ? 2 : 3;

// Cables sobre el piso 2: de las ranuras a los hoyos de las protoboards
module cables_arriba() {
  zs = Z2 + ESP;
  // VL53L0X izquierdo, frente y derecho
  for (t = [0 : 2]) for (i = [0, 1, 2, 3, 5]) {
    xk = (i - 2.5) * PASO_PIN;
    p = t == 0 ? [-TOF_LADO[0] + TOF_ATRAS + 4, TOF_LADO[1] + xk, zs + 4]
      : t == 2 ? [TOF_LADO[0] - TOF_ATRAS - 4, TOF_LADO[1] - xk, zs + 4]
      : [23 + (i - 2.5) * 1.5, TOF_FRENTE_Y - TOF_ATRAS - 4, Z1 + ESP + TOF_PIN_Z + TOF_SUBE + i * 1.5 + 14];
    w = i == 5 ? 4 : i;
    nom = str("VL53L0X ", ["izq", "frente", "der"][t], " ", SEN_TOF[i]);
    ly = [16, 16, 8][t] + w * 1.6;
    lz = [zs + 5, zs + 15, zs + 11][t];
    if (i == 5) arriba(p, [hx(-XP, 4), pin_nano(3 + t)], "green", ly, lz, ZP + 17 + t * 1.7, str(nom, " -> Nano A", t));
    else {
      l = linea(COL_TOF[i]);
      arriba(p, [hx(XP, [-2, 2, 3][t]), hy(BUS[l])], COL_TOF[i], ly, lz, z_bus(l), str(nom, " -> bus ", NOM_BUS[l]));
    }
  }
  // TCS34725 y OLED
  for (i = [0 : 3]) {
    l = linea(COL_TCS[i]);
    arriba([-20 - i * 1.5, COLOR_Y - 4.5, zs + 4], [hx(XP, -3), hy(BUS[l])], COL_TCS[i], 4 + i * 1.6, zs + 8,
           z_bus(l), str("TCS34725 ", SEN_TCS[i], " -> bus ", NOM_BUS[l]));
    lo = linea(COL_OLED[i]);
    arriba([20 + i * 1.5, OLED_PINES_Y, zs + 4], [hx(XP, -4), hy(BUS[lo])], COL_OLED[i], 2 + i * 1.6, zs + 7,
           z_bus(lo), str("OLED ", SEN_OLED[i], " -> bus ", NOM_BUS[lo]));
  }
  // L298N -> pines D del Nano (cinta frente a las protoboards)
  for (n = [0 : 5]) {
    c = L298_LOG[n];
    arriba([c[0], -3, zs + 2], [hx(-XP, -4), pin_nano(c[3])], c[2], -6.2, zs + 2 + n * 1.3, ZP + 16 + n * 1.7,
           str("L298N ", c[1], " -> Nano ", NANO_D_NOM[c[3]]));
  }
  // boton -> D2 y GND (fila D)
  for (i = [0 : 1])
    arriba([-28.5 + i * 1.5, -3, zs + 2], [hx(-XP, -5), pin_nano(10 + i)], i == 0 ? "hotpink" : "black", -4.5,
           zs + 2 + i * 1.3, ZP + 16 + i * 1.7, str("Boton ", i == 0 ? "D2" : "GND", " -> Nano ", NANO_D_NOM[10 + i]));
  // potencia: VIN y GND del Nano (cable calibre 22 directo a la protoboard)
  arriba([27, -3, zs + 2], [hx(-XP, 4), pin_nano(14)], "orange", 1, zs + 1.5, ZP + 3, "Interruptor -> Nano VIN", false);
  arriba([13.5, -3, zs + 2], [hx(-XP, 4), pin_nano(13)], "black", -1, zs + 1.5, ZP + 4.5, "L298N GND -> Nano GND", false);
}

module ensamble() {
  paso(1) {
    color(k("lightsteelblue")) translate([0, 0, Z1]) piso1();
    for (s = [-1, 1]) {
      motor(s);
      color(k("orange")) translate([s * X_MOT, 0, Z1 - MOT_H - 2 + 0.3]) cuna_motor();
      for (y = [-1, 1]) translate([s * X_MOT, y * (MOT_A / 2 + 3), Z1 + ESP]) tornillo(12, true);
      if (PASO == 1 || PASO == 2) cables_motor(s, false);
    }
  }
  paso(2) {
    for (s = [-1, 1]) rueda(s);
    color(k("orange")) translate([0, PATIN_Y, 0]) patin();
    translate([0, PATIN_Y, Z1 + ESP]) tornillo(10, true);
    color(k("orange")) translate([0, COLOR_Y, 2]) capucha_color();
    for (x = [-1, 1]) translate([x * 17, COLOR_Y, Z1 + ESP]) tornillo(10, true);
    translate([0, COLOR_Y, COLOR_Z + 0.8]) tcs_modulo();
    tcs_cables();
  }
  paso(3) {
    espaciadores_l298();
    l298();
    if (PASO == 0 || PASO >= 3) for (s = [-1, 1]) cables_motor(s);
  }
  paso(4) {
    bateria();
    conector_t(true, false);
  }
  paso(5) {
    translate([0, TOF_FRENTE_Y, Z1 + ESP]) tof_modulo(TOF_SUBE, 23, 14, "VL53L0X frente");
    for (s = [-1, 1]) translate([s * TOF_LADO[0], TOF_LADO[1], Z1 + ESP]) rotate([0, 0, -s * 90])
      tof_modulo(Z2 + 7 - Z1 - ESP - TOF_PIN_Z, 0, 0, s < 0 ? "VL53L0X izq" : "VL53L0X der");
  }
  paso(6) {
    postes(Z1 + ESP, SEP);
    for (p = POSTES) translate([p[0], p[1], Z1]) rotate([180, 0, 0]) tornillo(8);
    cables_l298_logica();
  }
  // paso 7 del manual: el piso 2 se arma en la mesa (PIEZA = "sub_piso2")
  paso(8) {
    color(k("lightsteelblue")) translate([0, 0, Z2]) piso2();
    for (p = POSTES) translate([p[0], p[1], Z2 + ESP]) tornillo(8);
    protoboards();
    nano();
    puentes();
    translate([0, 0, Z2 + ESP]) oled_modulo("OLED");
    translate([BOTON_XY[0], BOTON_XY[1], Z2 + ESP]) boton();
    translate([SWITCH_XY[0], SWITCH_XY[1], Z2 + ESP]) interruptor();
    cables_boton();
    if (PASO == 8 || PASO == 9) conector_t(false, true, false);
    arnes_potencia(PASO == 0 || PASO >= 10);
  }
  paso(9) cables_arriba();
  paso(10) conector_t(false, true, true);
}

// Piso 2 armado en la mesa (paso 7 del manual), en su posicion dentro del robot
module sub_piso2() {
  color("lightsteelblue") translate([0, 0, Z2]) piso2();
  for (p = POSTES) translate([p[0], p[1], Z2 + ESP]) tornillo(8);
  protoboards();
  nano();
  puentes();
  translate([0, 0, Z2 + ESP]) oled_modulo();
  translate([BOTON_XY[0], BOTON_XY[1], Z2 + ESP]) boton();
  translate([SWITCH_XY[0], SWITCH_XY[1], Z2 + ESP]) interruptor();
}

if (PIEZA == "ensamble") ensamble();
else if (PIEZA == "piso1") piso1();
else if (PIEZA == "piso2") piso2();
else if (PIEZA == "cuna_motor") cuna_motor();
else if (PIEZA == "capucha_color") translate([0, 0, Z1 - 2]) rotate([180, 0, 0]) capucha_color();
else if (PIEZA == "patin") translate([0, 0, Z1]) rotate([180, 0, 0]) patin();
else if (PIEZA == "espaciador") espaciador();
else if (PIEZA == "prueba") prueba();
else if (PIEZA == "placa") placa();
else if (PIEZA == "placa_vista") {
  color("orange") placa();
  color("dimgray") translate([0, 0, -1.01]) cube([CAMA, CAMA, 1]);
}
else if (PIEZA == "sub_piso2") sub_piso2();
else if (PIEZA == "det_motor") { motor(-1); cables_motor(-1, false); }
else if (PIEZA == "det_l298") { l298(); espaciadores_l298(); }
else if (PIEZA == "det_arnes") {
  gris() { color(k("lightsteelblue")) translate([0, 0, Z1]) piso1(); bateria(); conector_t(true, false); espaciadores_l298(); }
  l298();
  conector_t(false, true, UNIDO);
  arnes_potencia(UNIDO);
  translate([SWITCH_XY[0], SWITCH_XY[1], Z2 + ESP]) interruptor();
}
else if (PIEZA == "marca") color("red") translate(MARCA) sphere(d = 1.5, $fn = 12);
