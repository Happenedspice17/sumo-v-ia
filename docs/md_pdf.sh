#!/bin/sh
# Genera docs/pdf/manual_uso.pdf, manual_tecnico.pdf e historial_cambios.pdf desde los .md
cd "$(dirname "$0")"
gen() {
  pandoc "$1.md" -s --embed-resources -c md_pdf.css $3 --section-divs -f markdown+task_lists -o "/tmp/$1.html" --metadata lang=es
  node md_pdf.js "/tmp/$1.html" "pdf/$1.pdf" "$2"
}
gen manual_uso "Robot de laberinto · Manual de uso" "-c md_pdf_uso.css"
gen manual_tecnico "Robot de laberinto · Manual técnico"
gen historial_cambios "Robot de laberinto · Bitácora de diseño"
