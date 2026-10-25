// Chasis robot laberinto (Arduino UNO R3 / ATmega328P) - 125 x 125 mm
// Origen: centro del eje de las ruedas, a nivel del piso. X derecha, Y adelante, Z arriba.
//
// PIEZA: "ensamble", "piso1", "piso2", "piso3", "cuna_motor", "capucha_color", "patin",
//        "escuadra_tof", "espaciador", "prueba"
// PASO:  1-5 muestra el ensamble hasta ese paso (manual de ensamble); 0 = completo
//
// Tolerancias para FDM con boquilla 0.4 (Bambu Lab): ver la seccion "Tolerancias".
// Antes de imprimir todo, imprime PIEZA="prueba" y ajusta HOLGURA si algo no entra.

PIEZA = "ensamble";
PASO = 0;

$fn = 48;

// ---------- Tolerancias ----------
HOLGURA = 0.2;                 // juego por lado entre pieza impresa y componente
M3_PASO = 3.4;                 // M3 pasante (tornillo + tuerca)
M3_ROSCA = 2.8;                // M3 que se atornilla directo al plastico
M2_ROSCA = 1.8;                // M2 que se atornilla directo al plastico
D_BOTON = 7 + 2 * 0.15;        // boton de panel de 7 mm
D_SWITCH = 6 + 2 * 0.15;       // interruptor de palanca MTS-102 (6 mm)

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
X_MOT = X_MOT_EXT - MOT_L / 2;           // centro del motor

// Pisos
Z1 = EJE_Z + MOT_H / 2;                  // fondo del piso 1 (toca el motor)
SEP = 35;                                // separadores M3 piso 1 -> 2
Z2 = Z1 + ESP + SEP;                     // fondo del piso 2
SEP3 = 25;                               // separadores M3 piso 2 -> 3
Z3 = Z2 + ESP + SEP3;                    // fondo del piso 3
P3 = [110, 104];                         // piso 3 (X, Y)
P3_Y = -8;
R3 = 15;
POZO_Y = D_RUEDA / 2 + 4;                // medio largo del hueco de rueda
POSTES = [[48, 28], [-48, 28], [35, -52], [-35, -52]];

// Componentes
BAT = [37, 65, 19];      // 2S 18650 3000 mAh (X, Y, Z)
BAT_Y = 28;
L298 = [43, 43, 27];
L298_Y = -36;
L298_AG = 37;            // separacion de agujeros del L298N (medir el suyo)
COLOR_Y = 34;            // centro del sensor de color
COLOR_MOD = 20.5;        // TCS34725 morado (medir el suyo)
COLOR_Z = 5;             // altura de la cara del sensor sobre el suelo
PATIN_Y = 52;
PLACA = [53.4, 68.6];    // Arduino UNO R3
PLACA_Y = -10;
AG_UNO = [[2.5, 14.0], [50.7, 15.3], [7.6, 66.1], [35.5, 66.1]];   // agujeros UNO R3: (desde el borde de A0-A5, desde el borde del USB)
TOF = [25, 10.7, 2];     // VL53L0X CJVL53L0XV2
TOF_AG = 20;             // separacion de sus agujeros (medir el suyo)
TOF_FRENTE_Y = 35;
TOF_LADO_X = 40;
OLED = 27;
OLED_XY = [28, 29];
BOTON_XY = [-30, 30];
SWITCH_XY = [36, -42];
PROTO = [35, 47, 9];     // mini protoboard 170 puntos, girada (X, Y, Z)
PROTO_XY = [0, -25];
RANURA_X = 25;           // ranuras del piso 3 sobre los headers del Arduino

// ---------- Utilidades ----------
module cuadrado_redondo(l, r, h) {
  linear_extrude(h) offset(r) square(l - 2 * r, center = true);
}

module agujero(d, h) { translate([0, 0, -0.5]) cylinder(d = d, h = h + 1); }

module mostrar(p) { if (PASO == 0 || PASO >= p) children(); }

// ---------- Piezas impresas ----------
module avellanado() { translate([0, 0, ESP - 1.6]) cylinder(d1 = M3_PASO, d2 = 6.6, h = 1.61); }

module piso1() {
  difference() {
    cuadrado_redondo(L, R_ESQ, ESP);
    for (s = [-1, 1])
      translate([s * (X_RUEDA_INT - 2 + 25), 0, ESP / 2]) cube([50, 2 * POZO_Y, ESP + 2], center = true);
    translate([0, COLOR_Y, ESP / 2]) cube([16, 16, ESP + 2], center = true);           // cables del sensor de color
    translate([0, 0, ESP / 2]) cube([24, 10, ESP + 2], center = true);                 // paso de cables
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    for (s = [-1, 1]) for (y = [-1, 1])
      translate([s * X_MOT, y * (MOT_A / 2 + 3), 0]) agujero(M3_PASO, ESP);            // cunas de motor
    for (x = [-1, 1]) for (y = [-1, 1])
      translate([x * L298_AG / 2, L298_Y + y * L298_AG / 2, 0]) agujero(M3_PASO, ESP); // L298N
    // patines y capucha: avellanados, quedan bajo la bateria
    for (y = [PATIN_Y, -PATIN_Y]) translate([0, y, 0]) { agujero(M3_PASO, ESP); avellanado(); }
    for (x = [-1, 1]) translate([x * 17, COLOR_Y, 0]) { agujero(M3_PASO, ESP); avellanado(); }
    for (x = [-1, 1]) translate([x * 22.5, BAT_Y, ESP / 2]) cube([3, 22, ESP + 2], center = true);   // cincho de bateria
  }
}

module piso2() {
  difference() {
    cuadrado_redondo(L, R_ESQ, ESP);
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    for (h = AG_UNO) translate([PLACA[0] / 2 - h[0], PLACA_Y - PLACA[1] / 2 + h[1], 0]) agujero(M3_PASO, ESP);
    translate([0, -53, ESP / 2]) cube([24, 8, ESP + 2], center = true);                // cables de abajo
    translate([0, TOF_FRENTE_Y - 7.5, 0]) agujero(M3_PASO, ESP);                        // escuadras VL53L0X
    for (s = [-1, 1]) translate([s * (TOF_LADO_X - 7.5), 0, 0]) agujero(M3_PASO, ESP);
  }
}

module piso3() {
  difference() {
    translate([0, P3_Y, 0]) linear_extrude(ESP) offset(R3) square([P3[0] - 2 * R3, P3[1] - 2 * R3], center = true);
    for (p = POSTES) translate([p[0], p[1], 0]) agujero(M3_PASO, ESP);
    translate([BOTON_XY[0], BOTON_XY[1], 0]) agujero(D_BOTON, ESP);
    translate([SWITCH_XY[0], SWITCH_XY[1], 0]) agujero(D_SWITCH, ESP);
    for (s = [-1, 1]) translate([s * RANURA_X, -12, ESP / 2]) cube([8, 52, ESP + 2], center = true);
  }
}

module cuna_motor() {
  // aprieta el motor contra el piso 1; abierta arriba, 0.3 mm mas baja que el motor para que apriete
  difference() {
    translate([-8, -MOT_A / 2 - 6, 0]) cube([16, MOT_A + 12, 2 + MOT_H - 0.3]);
    translate([-9, -MOT_A / 2 - HOLGURA, 2]) cube([18, MOT_A + 2 * HOLGURA, MOT_H + 1]);
    for (y = [-1, 1]) translate([0, y * (MOT_A / 2 + 3), 0]) agujero(M3_PASO, 20);
  }
}

module capucha_color() {
  // tubo que tapa la luz ambiente; el TCS34725 entra por abajo y se apoya en el borde interior
  h = Z1 - 2;                         // de 2 mm sobre el suelo hasta el piso 1
  hueco = COLOR_MOD + 2 * HOLGURA;
  borde = COLOR_Z + 1.6;              // altura donde se apoya la espalda del modulo
  difference() {
    union() {
      translate([-hueco / 2 - 2, -hueco / 2 - 2, 0]) cube([hueco + 4, hueco + 4, h]);
      translate([-22, -5, h - 3]) cube([44, 10, 3]);                       // orejas
      for (x = [-1, 1]) translate([x * (hueco / 2 - 0.75), 0, borde - 2 + 1])   // topes donde se apoya el modulo
        cube([1.5, 8, 2], center = true);
    }
    translate([-hueco / 2, -hueco / 2, -1]) cube([hueco, hueco, borde - 2 + 1]);
    translate([-hueco / 2, -hueco / 2, 0]) cube([hueco, hueco, h + 1]);
    for (x = [-1, 1]) translate([x * 17, 0, h - 4]) agujero(M3_PASO, 5);
  }
}

module patin() {
  // apoyo deslizante; deja 0.5 mm al suelo. Se atornilla con M3 desde arriba del piso 1
  h = Z1 - 0.5;
  difference() {
    translate([0, 0, 0.5]) {
      translate([0, 0, 5]) cylinder(d = 10, h = h - 5);
      translate([0, 0, 5]) sphere(d = 10);
    }
    translate([0, 0, Z1 - 10]) cylinder(d = M3_ROSCA, h = 11);
  }
}

module escuadra_tof() {
  // el VL53L0X se atornilla en la cara +Y (mira hacia +Y)
  difference() {
    union() {
      translate([-15, 0, 0]) cube([30, 3, 18]);
      translate([-15, -9, 0]) cube([30, 12, 3]);
    }
    for (x = [-1, 1]) translate([x * TOF_AG / 2, -1, 12]) rotate([-90, 0, 0]) cylinder(d = M2_ROSCA, h = 5);
    translate([0, -4.5, 0]) agujero(M3_PASO, 3);
  }
}

module espaciador(h = 5) {
  // separa el Arduino y el L298N de su piso (5 mm)
  difference() { cylinder(d = 7, h = h); agujero(M3_PASO, h); }
}

module prueba() {
  // pieza de prueba: agujeros M3 y M2, boton, interruptor y ranura del motor
  difference() {
    cube([70, 26, 3]);
    for (i = [0 : 2]) translate([6 + i * 7, 7, 0]) agujero(3.2 + i * 0.2, 3);    // 3.2 / 3.4 / 3.6
    for (i = [0 : 1]) translate([6 + i * 7, 18, 0]) agujero(M3_ROSCA + i * 0.2, 3);
    translate([30, 18, 0]) agujero(M2_ROSCA, 3);
    translate([40, 8, 0]) agujero(D_BOTON, 3);
    translate([40, 19, 0]) agujero(D_SWITCH, 3);
  }
  translate([48, 0, 0]) difference() {
    cube([22, 26, 9]);
    translate([5, 13 - MOT_A / 2 - HOLGURA, 2]) cube([20, MOT_A + 2 * HOLGURA, 10]);
  }
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
    color("orange") for (y = [PATIN_Y, -PATIN_Y]) translate([0, y, 0]) patin();
    color("orange") translate([0, COLOR_Y, 2]) capucha_color();
    color("purple") translate([0, COLOR_Y, COLOR_Z + 0.8]) cube([COLOR_MOD, COLOR_MOD, 1.6], center = true);
  }
  mostrar(3) {
    color("royalblue") translate([0, BAT_Y, Z1 + ESP + BAT[2] / 2]) cube(BAT, center = true);
    color("dimgray") translate([0, BAT_Y, Z1 + ESP + BAT[2] + 0.5]) cube([46, 20, 1], center = true);
    color("red") translate([0, L298_Y, Z1 + ESP + 5 + L298[2] / 2]) cube(L298, center = true);
    postes(Z1 + ESP, SEP);
  }
  mostrar(4) {
    color("lightsteelblue", 0.9) translate([0, 0, Z2]) piso2();
    color("darkcyan") translate([0, PLACA_Y, Z2 + ESP + 5 + 7]) cube([PLACA[0], PLACA[1], 14], center = true);
    color("orange") translate([0, TOF_FRENTE_Y - 3, Z2 + ESP]) escuadra_tof();
    color("green") translate([0, TOF_FRENTE_Y + 0.5, Z2 + ESP + 12]) cube([TOF[0], 1.6, TOF[1]], center = true);
    for (s = [-1, 1]) {
      color("orange") translate([s * (TOF_LADO_X - 3), 0, Z2 + ESP]) rotate([0, 0, -s * 90]) escuadra_tof();
      color("green") translate([s * (TOF_LADO_X + 0.5), 0, Z2 + ESP + 12]) cube([1.6, TOF[0], TOF[1]], center = true);
    }
  }
  mostrar(5) {
    postes(Z2 + ESP, SEP3);
    color("lightsteelblue", 0.9) translate([0, 0, Z3]) piso3();
    color("crimson") translate([PROTO_XY[0], PROTO_XY[1], Z3 + ESP + PROTO[2] / 2]) cube(PROTO, center = true);
    color("white") translate([OLED_XY[0], OLED_XY[1], Z3 + ESP + 3]) cube([OLED, OLED, 4], center = true);
    color("black") translate([BOTON_XY[0], BOTON_XY[1], Z3 + ESP]) cylinder(d = 10, h = 6);
    color("dimgray") translate([SWITCH_XY[0], SWITCH_XY[1], Z3 + ESP]) cylinder(d = 3, h = 10);
  }
}

if (PIEZA == "ensamble") ensamble();
else if (PIEZA == "piso1") piso1();
else if (PIEZA == "piso2") piso2();
else if (PIEZA == "piso3") piso3();
else if (PIEZA == "cuna_motor") cuna_motor();
else if (PIEZA == "capucha_color") translate([0, 0, Z1 - 2]) rotate([180, 0, 0]) capucha_color();
else if (PIEZA == "patin") translate([0, 0, Z1]) rotate([180, 0, 0]) patin();
else if (PIEZA == "escuadra_tof") escuadra_tof();
else if (PIEZA == "espaciador") espaciador();
else if (PIEZA == "prueba") prueba();
