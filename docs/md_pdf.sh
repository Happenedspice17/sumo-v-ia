#!/bin/sh
# Genera docs/pdf/manual_uso.pdf, manual_tecnico.pdf e historial_cambios.pdf desde los .md
# Requiere pandoc, Playwright con Chromium y `npm install` en docs/ (Mermaid para los diagramas).
cd "$(dirname "$0")"
[ -d node_modules/mermaid ] || npm install --no-audit --no-fund
gen() {
  pandoc "$1.md" -s --template md_pdf.html -c md_pdf.css $3 --toc --toc-depth=2 --section-divs \
    -f markdown+task_lists -o "$1.tmp.html" --metadata lang=es
  node md_pdf.js "$1.tmp.html" "pdf/$1.pdf" "$2"
  rm -f "$1.tmp.html"
}
gen manual_uso "Robot de laberinto · Manual de uso" "-c md_pdf_uso.css"
gen manual_tecnico "Robot de laberinto · Manual técnico"
gen historial_cambios "Robot de laberinto · Bitácora de diseño"
gen manual_jueces "Robot de laberinto · Manual para jueces" "-c md_pdf_jueces.css"
