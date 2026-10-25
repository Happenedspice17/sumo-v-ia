// Chasis robot laberinto - 125 x 125 mm
// Origen: centro del eje de las ruedas, a nivel del piso. X derecha, Y adelante, Z arriba.
// PIEZA: "ensamble", "piso1", "piso2", "soporte_motor", "soporte_tof", "soporte_color",
//        "patin", "mastil", "camara"
// VERSION: "unoq" (con mastil y camara) o "328p"

PIEZA = "ensamble";
VERSION = "unoq";

$fn = 48;

// ---------- Medidas generales ----------
L = 125;            // lado maximo permitido
R_ESQ = 30;         // radio de esquinas (deja girar en un pasillo de 180)
ESP = 3;            // espesor de pisos

// Ruedas y motores N20
D_RUEDA = 34;
A_RUEDA = 20;       // ancho de cada rueda
MOT_L = 24;         // caja + motor
MOT_A = 12;         // ancho (Y)
MOT_H = 10;         // alto (Z)
EJE_Z = D_RUEDA / 2;
X_RUEDA_INT = L / 2 - A_RUEDA;           // 42.5
X_MOT_EXT = X_RUEDA_INT - 1.5;           // cara de la caja de engranes

// Pisos
Z1 = EJE_Z + MOT_H / 2;                  // fondo del piso 1 (toca el motor)
SEP = 32;                                // largo de separadores M3
Z2 = Z1 + ESP + SEP;                     // fondo del piso 2
POZO_Y = D_RUEDA / 2 + 4;                // medio largo del hueco de rueda
POSTES = [[48, 28], [-48, 28], [35, -52], [-35, -52]];
OLED_XY = [29, 46];
BOTON_XY = [-29, 46];

// Componentes
BAT = [37, 65, 19];      // 2S 18650 3000 mAh (X, Y, Z)
BAT_Y = 28;
L298 = [43, 43, 27];
L298_Y = -36;
COLOR_Y = 34;            // centro del sensor de color
COLOR_MOD = 20;
COLOR_Z = 4;             // altura de la cara del sensor sobre el piso
PLACA = [53.4, 68.6];    // huella Arduino UNO R3 / UNO Q
PLACA_Y = -10;
TOF = [25, 10.7, 2];     // modulo VL53L0X GY-530
TOF_FRENTE_Y = 35;
TOF_LADO_X = 40;
OLED = 27;
MASTIL_Y = -54;
MASTIL_H = 120;          // ajustable 90-140 -> camara a 150-200 mm del piso
CAM_INCL = 40;           // grados hacia abajo

// ---------- Utilidades ----------
module cuadrado_redondo(l, r, h) {
  linear_extrude(h)
    offset(r) square(l - 2 * r, center = true);
}

module agujero_m3(h) { cylinder(d = 3.2, h = h + 1); }

// ---------- Piezas ----------
module piso1() {
  difference() {
    translate([0, 0, Z1]) cuadrado_redondo(L, R_ESQ, ESP);
    for (s = [-1, 1])
      translate([s * (X_RUEDA_INT - 2 + 25), 0, Z1 + ESP / 2])
        cube([50, 2 * POZO_Y, ESP + 2], center = true);
    // ventana del sensor de color
    translate([0, COLOR_Y, Z1 + ESP / 2]) cube([14, 14, ESP + 2], center = true);
    // paso de cables
    translate([0, 0, Z1 + ESP / 2]) cube([24, 10, ESP + 2], center = true);
    for (p = POSTES) translate([p[0], p[1], Z1 - 0.5]) agujero_m3(ESP);
    for (s = [-1, 1]) for (y = [-1, 1])
      translate([s * (X_MOT_EXT - MOT_L / 2), y * (MOT_A / 2 + 3), Z1 - 0.5]) agujero_m3(ESP);
    for (x = [-18.5, 18.5]) for (y = [-18.5, 18.5])
      translate([x, L298_Y + y, Z1 - 0.5]) agujero_m3(ESP);
  }
}

module piso2() {
  difference() {
    translate([0, 0, Z2]) cuadrado_redondo(L, R_ESQ, ESP);
    for (p = POSTES) translate([p[0], p[1], Z2 - 0.5]) agujero_m3(ESP);
    // agujeros de la placa (patron UNO)
    for (h = [[2.5, 14.0], [50.7, 15.3], [7.6, 66.1], [35.5, 66.1]])
      translate([-PLACA[0] / 2 + h[0], PLACA_Y - PLACA[1] / 2 + h[1], Z2 - 0.5]) agujero_m3(ESP);
    // paso de cables
    translate([0, 30, Z2 + ESP / 2]) cube([20, 8, ESP + 2], center = true);
    // base del mastil
    translate([0, MASTIL_Y, Z2 + ESP / 2]) cube([10.4, 6.4, ESP + 2], center = true);
    translate([BOTON_XY[0], BOTON_XY[1], Z2 - 0.5]) cylinder(d = 7, h = ESP + 1);   // boton
  }
}

module soporte_motor() {
  // cuna que aprieta el motor contra el piso 1; abierta arriba
  difference() {
    translate([-8, -MOT_A / 2 - 6, 0]) cube([16, MOT_A + 12, MOT_H + 2]);
    translate([-9, -MOT_A / 2 - 0.2, 2]) cube([18, MOT_A + 0.4, MOT_H + 1]);
    for (y = [-1, 1]) translate([0, y * (MOT_A / 2 + 3), -1]) cylinder(d = 3.2, h = 20);
  }
}

module soporte_color() {
  // capucha que tapa la luz ambiente; el modulo va dentro, cara a COLOR_Z del piso
  h = Z1 - 2;
  difference() {
    translate([-13, -13, 0]) cube([26, 26, h]);
    translate([-11, -11, -1]) cube([22, 22, h - 2 + 1]);
    translate([0, 0, h - 3]) cylinder(d = 6, h = 5);
  }
}

module patin() {
  // apoyo deslizante: deja 0.5 mm al piso
  h = Z1 - 0.5;
  translate([0, 0, 0.5]) {
    translate([0, 0, 5]) cylinder(d = 10, h = h - 5);
    translate([0, 0, 5]) sphere(d = 10);
  }
}

module soporte_tof() {
  // escuadra: el sensor se atornilla en la cara +Y (mira hacia +Y)
  difference() {
    union() {
      translate([-15, 0, 0]) cube([30, 3, 18]);
      translate([-15, -9, 0]) cube([30, 12, 3]);
    }
    for (x = [-10, 10]) translate([x, -1, 12]) rotate([-90, 0, 0]) cylinder(d = 2.2, h = 5);
    translate([0, -4.5, -1]) cylinder(d = 3.2, h = 5);
  }
}

module mastil() {
  // perfil de 10 x 6 con ranura para ajustar altura
  difference() {
    translate([-5, -3, 0]) cube([10, 6, MASTIL_H]);
    translate([0, -4, 20]) hull() {
      rotate([-90, 0, 0]) cylinder(d = 3.2, h = 8);
      translate([0, 0, MASTIL_H - 40]) rotate([-90, 0, 0]) cylinder(d = 3.2, h = 8);
    }
  }
}

module camara() {
  // modulo de camara USB 32 x 32
  color("dimgray") translate([-16, -4, -16]) cube([32, 8, 32]);
  color("black") rotate([-90, 0, 0]) cylinder(d = 12, h = 10);
}

// ---------- Componentes comprados (solo para el ensamble) ----------
module rueda(s) {
  color("black") translate([s * (X_RUEDA_INT + A_RUEDA / 2), 0, EJE_Z])
    rotate([0, 90, 0]) cylinder(d = D_RUEDA, h = A_RUEDA, center = true);
}

module motor(s) {
  color("gold") translate([s * (X_MOT_EXT - MOT_L / 2), 0, EJE_Z])
    cube([MOT_L, MOT_A, MOT_H], center = true);
}

module ensamble() {
  color("lightsteelblue") piso1();
  color("lightsteelblue", 0.9) piso2();
  for (s = [-1, 1]) {
    rueda(s);
    motor(s);
    color("orange") translate([s * (X_MOT_EXT - MOT_L / 2), 0, Z1 - MOT_H - 2]) soporte_motor();
  }
  for (p = POSTES) color("silver") translate([p[0], p[1], Z1 + ESP]) cylinder(d = 5, h = SEP);
  color("orange") for (y = [52, -52]) translate([0, y, 0]) patin();
  color("orange") translate([0, COLOR_Y, 2]) soporte_color();
  color("purple") translate([0, COLOR_Y, COLOR_Z + 1]) cube([COLOR_MOD, COLOR_MOD, 2], center = true);
  color("royalblue") translate([0, BAT_Y, Z1 + ESP + BAT[2] / 2]) cube(BAT, center = true);
  color("red") translate([0, L298_Y, Z1 + ESP + L298[2] / 2]) cube(L298, center = true);
  color(VERSION == "unoq" ? "teal" : "darkcyan")
    translate([0, PLACA_Y, Z2 + ESP + 5 + 7]) cube([PLACA[0], PLACA[1], 14], center = true);
  // VL53L0X: frente, izquierda, derecha
  color("orange") translate([0, TOF_FRENTE_Y - 3, Z2 + ESP]) soporte_tof();
  color("green") translate([0, TOF_FRENTE_Y + 0.5, Z2 + ESP + 12]) cube([TOF[0], 1.6, TOF[1]], center = true);
  for (s = [-1, 1]) {
    color("orange") translate([s * (TOF_LADO_X - 3), 0, Z2 + ESP])
      rotate([0, 0, -s * 90]) soporte_tof();
    color("green") translate([s * (TOF_LADO_X + 0.5), 0, Z2 + ESP + 12]) cube([1.6, TOF[0], TOF[1]], center = true);
  }
  color("white") translate([OLED_XY[0], OLED_XY[1], Z2 + ESP + 3]) cube([OLED, OLED, 4], center = true);
  color("black") translate([BOTON_XY[0], BOTON_XY[1], Z2 + ESP + 3]) cylinder(d = 12, h = 6, center = true);
  if (VERSION == "unoq") {
    color("orange") translate([0, MASTIL_Y, Z2]) mastil();
    translate([0, MASTIL_Y + 8, Z2 + MASTIL_H + 5]) rotate([-CAM_INCL, 0, 0]) camara();
  }
}

if (PIEZA == "ensamble") ensamble();
else if (PIEZA == "piso1") translate([0, 0, -Z1]) piso1();
else if (PIEZA == "piso2") translate([0, 0, -Z2]) piso2();
else if (PIEZA == "soporte_motor") rotate([180, 0, 0]) soporte_motor();
else if (PIEZA == "soporte_tof") soporte_tof();
else if (PIEZA == "soporte_color") soporte_color();
else if (PIEZA == "patin") rotate([180, 0, 0]) patin();
else if (PIEZA == "mastil") rotate([0, 90, 0]) mastil();
