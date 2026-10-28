// Chasis robot laberinto (Arduino Nano / ATmega328P) - 120 x 120 mm con ruedas
// Origen: centro del eje de las ruedas, a nivel del piso. X derecha, Y adelante, Z arriba.
//
// PIEZA: "ensamble", "piso1", "piso2", "cuna_motor", "capucha_color", "patin", "espaciador", "prueba"
// PASO:  1-4 muestra el ensamble hasta ese paso (manual de ensamble); 0 = completo
//
// Los sensores se insertan sin tornillos:
//   VL53L0X: bajan por las ranuras de los soportes del piso 1
//   TCS34725: entra deslizando por atras de la capucha
//   OLED: se acuesta en su marco del piso 2 con los pines hacia abajo
//   Protoboards: entran en su marco del piso 2
//
// Tolerancias para FDM con boquilla 0.4 (Bambu Lab). Antes de imprimir todo,
// imprime PIEZA="prueba" y ajusta HOLGURA/RANURA si algo no entra.

PIEZA = "ensamble";
PASO = 0;

$fn = 48;

// ---------- Tolerancias ----------
HOLGURA = 0.2;                 // juego por lado entre pieza impresa y componente
RANURA = 1.6 + 0.4;            // ranura para un PCB de 1.6 mm
M3_PASO = 3.4;                 // M3 pasante (tornillo + tuerca)
M3_ROSCA = 2.8;                // M3 que se atornilla directo al plastico
D_BOTON = 7 + 2 * 0.15;        // boton de panel de 7 mm
D_SWITCH = 6 + 2 * 0.15;       // interruptor de palanca MTS-102 (6 mm)

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
POZO_X = X_RUEDA_INT - 2;                // hueco de la rueda en el piso 1
POZO_Y = 19;

// Pisos
Z1 = EJE_Z + MOT_H / 2;                  // fondo del piso 1 (toca el motor)
SEP = 35;                                // separadores M3 hembra-hembra
Z2 = Z1 + ESP + SEP;                     // fondo del piso 2
POSTES = [[42, 50], [-42, 50], [44, -46], [-44, -46]];

// Componentes
BAT = [65, 37, 19];      // 2S 18650 acostada a lo ancho (X, Y, Z)
BAT_Y = 30;
BAT_PARED = 8;           // alto de los topes que la sujetan
L298 = [43, 43, 27];
L298_Y = -36;
L298_AG = 37;            // separacion de agujeros del L298N (medir el suyo)
TOF = [25, 10.7];        // VL53L0X CJVL53L0XV2 (ancho, alto)
TOF_FRENTE_Y = 54;
TOF_LADO = [50, 34.5];   // (X, Y) de los soportes laterales
COLOR_MOD = 20.5;        // TCS34725 morado (medir el suyo)
COLOR_Y = 34;
COLOR_Z = 5;             // altura de la cara del sensor sobre el suelo
PATIN_Y = -52;
PROTO = [35, 47, 9.5];   // mini protoboard 170 puntos (X, Y, Z)
PROTO_Y = -32.6;
NANO = [18, 44];
OLED = [27.3, 27.8];     // PCB del OLED 0.96" (medir el suyo)
OLED_Y = 17.5;           // pines hacia atras, sobre el hueco entre bateria y L298N
BOTON_XY = [-38, 5];
SWITCH_XY = [38, 5];
PASO_PIN = 2.54;
DUPONT = [2.5, 14];      // conector dupont hembra (lado, largo)

OLED_PINES_Y = OLED_Y - OLED[1] / 2 + 2.5;

// ---------- Utilidades ----------
module cuadrado_redondo(l, r, h) {
  linear_extrude(h) offset(r) square(l - 2 * r, center = true);
}

module agujero(d, h) { translate([0, 0, -0.5]) cylinder(d = d, h = h + 1); }

module avellanado() { translate([0, 0, ESP - 1.6]) cylinder(d1 = M3_PASO, d2 = 6.6, h = 1.61); }

module mostrar(p) { if (PASO == 0 || PASO >= p) children(); }

// ---------- Piezas impresas ----------

// Soporte de VL53L0X: dos postes con ranura; el modulo baja desde arriba y queda mirando a +Y
module soporte_tof() {
  a = TOF[0] + 2 * HOLGURA;
  difference() {
    for (s = [-1, 1]) translate([s * (a / 2 + 0.5) - 2, -2.5, 0]) cube([4, 5, TOF[1] + 1.5]);
    translate([-a / 2, 0.5 - RANURA / 2, -1]) cube([a, RANURA, 20]);
  }
}

module piso1() {
  difference() {
    union() {
      cuadrado_redondo(L, R_ESQ, ESP);
      translate([0, 0, ESP]) {
        translate([0, TOF_FRENTE_Y, 0]) soporte_tof();
        for (s = [-1, 1]) translate([s * TOF_LADO[0], TOF_LADO[1], 0]) rotate([0, 0, -s * 90]) soporte_tof();
        // topes de la bateria en las esquinas; dejan libre el centro de cada lado para los cables
        xb = BAT[0] / 2 + HOLGURA + 1;
        yb = BAT[1] / 2 + HOLGURA + 1;
        for (s = [-1, 1]) {
          for (y = [-1, 1]) translate([s * xb, BAT_Y + y * (yb - 6), BAT_PARED / 2]) cube([2, 10, BAT_PARED], center = true);
          translate([s * 16.5, BAT_Y - yb, BAT_PARED / 2]) cube([9, 2, BAT_PARED], center = true);
          translate([s * 25, BAT_Y + yb, BAT_PARED / 2]) cube([10, 2, BAT_PARED], center = true);
        }
      }
    }
    for (s = [-1, 1]) translate([s * (POZO_X + 25), 0, ESP / 2]) cube([50, 2 * POZO_Y, ESP + 2], center = true);
    translate([0, 0, ESP / 2]) cube([24, 10, ESP + 2], center = true);                 // paso de cables
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    for (s = [-1, 1]) for (y = [-1, 1])
      translate([s * X_MOT, y * (MOT_A / 2 + 3), 0]) agujero(M3_PASO, ESP);            // cunas de motor
    for (x = [-1, 1]) for (y = [-1, 1])
      translate([x * L298_AG / 2, L298_Y + y * L298_AG / 2, 0]) agujero(M3_PASO, ESP); // L298N
    // patin y capucha: avellanados, quedan bajo el L298N y la bateria
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
    translate([0, TOF_FRENTE_Y - 2, ESP / 2]) cube([24, 5, ESP + 2], center = true);             // cables del VL53L0X frontal
    for (s = [-1, 1]) translate([s * (TOF_LADO[0] - 2), TOF_LADO[1], ESP / 2]) cube([5, 20, ESP + 2], center = true);   // laterales
    translate([BOTON_XY[0], BOTON_XY[1], 0]) agujero(D_BOTON, ESP);
    translate([SWITCH_XY[0], SWITCH_XY[1], 0]) agujero(D_SWITCH, ESP);
  }
}

module cuna_motor() {
  // aprieta el motor contra el piso 1; 0.3 mm mas baja que el motor para que apriete
  difference() {
    translate([-8, -MOT_A / 2 - 6, 0]) cube([16, MOT_A + 12, 2 + MOT_H - 0.3]);
    translate([-9, -MOT_A / 2 - HOLGURA, 2]) cube([18, MOT_A + 2 * HOLGURA, MOT_H + 1]);
    for (y = [-1, 1]) translate([0, y * (MOT_A / 2 + 3), 0]) agujero(M3_PASO, 20);
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
    translate([-v / 2, -a / 2 - 3, z0]) cube([v, 4, h]);                     // salida de cables atras
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
  // agujeros M3, boton, interruptor, ranura de motor y un soporte de VL53L0X
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

// ---------- Componentes comprados (solo para el ensamble) ----------
module rueda(s) {
  color("black") translate([s * (X_RUEDA_INT + A_RUEDA / 2), 0, EJE_Z])
    rotate([0, 90, 0]) cylinder(d = D_RUEDA, h = A_RUEDA, center = true);
}

module motor(s) {
  color("gold") translate([s * X_MOT, 0, EJE_Z]) cube([MOT_L, MOT_A, MOT_H], center = true);
}

module postes(z, h) {
  for (p = POSTES) color("silver") translate([p[0], p[1], z]) cylinder(d = 5.5, h = h, $fn = 6);
}

// Fila de pines con sus conectores dupont y cables. Pines hacia +Z desde z = 0.
module pines(n, largo = 6, dupont = true, cables = ["red", "black", "royalblue", "cyan", "green", "orange"]) {
  for (k = [0 : n - 1]) translate([(k - (n - 1) / 2) * PASO_PIN, 0, 0]) {
    color("gold") translate([-0.32, -0.32, -1]) cube([0.64, 0.64, largo + 1]);
    if (dupont) {
      color("black") translate([-DUPONT[0] / 2, -DUPONT[0] / 2, 0.5]) cube([DUPONT[0], DUPONT[0], DUPONT[1]]);
      color(cables[k % len(cables)]) translate([0, 0, DUPONT[1] + 0.5]) cylinder(d = 1.4, h = 6, $fn = 8);
    }
  }
}

// VL53L0X con header en angulo recto: los pines salen hacia arriba por detras del PCB
module tof_modulo() {
  color("green") translate([0, 0.5, TOF[1] / 2]) cube([TOF[0], 1.6, TOF[1]], center = true);
  color("black") translate([0, 1.8, TOF[1] / 2]) cube([4.4, 1, 2.4], center = true);
  color("dimgray") translate([0, -1.55, TOF[1] - 1.3]) cube([6 * PASO_PIN, 2.5, 2.5], center = true);
  translate([0, -1.55, TOF[1] - 0.05]) pines(6, cables = ["red", "black", "cyan", "royalblue", "white", "green"]);
}

// OLED acostado: espaciador del header dentro de la ranura y pines hacia abajo
module oled_modulo() {
  color("navy") translate([0, OLED_Y, 1.5]) cube([OLED[0], OLED[1], 3], center = true);
  color("black") translate([0, OLED_Y + 2, 3]) cube([26, 19, 0.6], center = true);
  color("dimgray") translate([0, OLED_PINES_Y, -1.25]) cube([4 * PASO_PIN, 2.5, 2.5], center = true);
  translate([0, OLED_PINES_Y, -2.5]) mirror([0, 0, 1]) pines(4, cables = ["black", "red", "cyan", "royalblue"]);
}

// TCS34725 con 4 cables soldados que salen por atras (cara del sensor hacia abajo)
module tcs_modulo() {
  color("purple") cube([COLOR_MOD, COLOR_MOD, 1.6], center = true);
  color("white") translate([0, 0, -1.3]) cube([3, 3, 1], center = true);
  for (k = [0 : 6]) color("silver") translate([(k - 3) * PASO_PIN, -COLOR_MOD / 2 + 1.3, 0.8]) cylinder(d = 1.6, h = 0.2);
  cab = ["red", "black", "cyan", "royalblue"];
  for (k = [0 : 3]) color(cab[k]) translate([(k - 1.5) * PASO_PIN, -COLOR_MOD / 2 + 1.3, 1]) {
    cylinder(d = 1.4, h = 3, $fn = 8);
    translate([0, 0, 3]) rotate([90, 0, 0]) cylinder(d = 1.4, h = 14, $fn = 8);
  }
}

// Boton e interruptor con su cuerpo bajo el piso 2
module boton() {
  color("black") cylinder(d = 10, h = 6);
  color("dimgray") translate([0, 0, -ESP - 12]) cylinder(d = 7, h = 12);
  for (x = [-1, 1]) color("silver") translate([x * 2 - 0.4, -1, -ESP - 17]) cube([0.8, 2, 5]);
}

module interruptor() {
  color("silver") cylinder(d = 3, h = 10);
  color("dimgray") translate([-4, -6.5, -ESP - 10]) cube([8, 13, 10]);
  for (y = [-1, 0, 1]) color("silver") translate([-1, y * 4.7 - 0.25, -ESP - 15]) cube([2, 0.5, 5]);
}

module ensamble() {
  mostrar(1) {
    color("lightsteelblue") translate([0, 0, Z1]) piso1();
    for (s = [-1, 1]) {
      rueda(s);
      motor(s);
      color("orange") translate([s * X_MOT, 0, Z1 - MOT_H - 2 + 0.3]) cuna_motor();
    }
  }
  mostrar(2) {
    color("orange") translate([0, PATIN_Y, 0]) patin();
    color("orange") translate([0, COLOR_Y, 2]) capucha_color();
    translate([0, COLOR_Y, COLOR_Z + 0.8]) tcs_modulo();
  }
  mostrar(3) {
    color("royalblue") translate([0, BAT_Y, Z1 + ESP + BAT[2] / 2]) cube(BAT, center = true);
    color("red") translate([0, L298_Y, Z1 + ESP + 5 + L298[2] / 2]) cube(L298, center = true);
    translate([0, TOF_FRENTE_Y, Z1 + ESP]) tof_modulo();
    for (s = [-1, 1]) translate([s * TOF_LADO[0], TOF_LADO[1], Z1 + ESP]) rotate([0, 0, -s * 90]) tof_modulo();
    postes(Z1 + ESP, SEP);
  }
  mostrar(4) {
    xp = PROTO[0] / 2 + 1.1;
    color("lightsteelblue", 0.9) translate([0, 0, Z2]) piso2();
    for (s = [-1, 1]) color("white") translate([s * xp, PROTO_Y, Z2 + ESP + PROTO[2] / 2]) cube(PROTO, center = true);
    color("darkcyan") translate([-xp, PROTO_Y + 1, Z2 + ESP + PROTO[2] + 4]) cube([NANO[0], NANO[1], 1.6], center = true);
    color("silver") translate([-xp, PROTO_Y + 1 - NANO[1] / 2 + 3, Z2 + ESP + PROTO[2] + 6.4]) cube([9, 7.5, 3.2], center = true);
    translate([0, 0, Z2 + ESP]) oled_modulo();
    translate([BOTON_XY[0], BOTON_XY[1], Z2 + ESP]) boton();
    translate([SWITCH_XY[0], SWITCH_XY[1], Z2 + ESP]) interruptor();
  }
}

if (PIEZA == "ensamble") ensamble();
else if (PIEZA == "piso1") piso1();
else if (PIEZA == "piso2") piso2();
else if (PIEZA == "cuna_motor") cuna_motor();
else if (PIEZA == "capucha_color") translate([0, 0, Z1 - 2]) rotate([180, 0, 0]) capucha_color();
else if (PIEZA == "patin") translate([0, 0, Z1]) rotate([180, 0, 0]) patin();
else if (PIEZA == "espaciador") espaciador();
else if (PIEZA == "prueba") prueba();
