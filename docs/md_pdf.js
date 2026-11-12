// Uso: node docs/md_pdf.js entrada.html salida.pdf "Titulo pie"
// Renderiza los bloques ```mermaid``` en el mismo Chromium antes de imprimir.
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [inp, out, pie] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.resolve(inp));
  // tablas cortas: no se parten entre páginas; las largas sí (sin cortar filas)
  await p.evaluate(() => document.querySelectorAll('table').forEach(t => { if (t.rows.length <= 12) t.classList.add('corta'); }));
  if (await p.$('pre.mermaid')) {
    await p.addScriptTag({ path: path.join(__dirname, 'node_modules/mermaid/dist/mermaid.min.js') });
    const err = await p.evaluate(async () => {
      document.querySelectorAll('pre.mermaid').forEach(pre => {
        const d = document.createElement('div');
        d.className = 'mermaid';
        d.textContent = pre.textContent;
        pre.replaceWith(d);
      });
      const v = getComputedStyle(document.documentElement);
      const c = n => v.getPropertyValue(n).trim();
      mermaid.initialize({ startOnLoad: false, theme: 'base', fontFamily: 'Inter, sans-serif',
        flowchart: { htmlLabels: false, curve: 'basis' }, state: { htmlLabels: false },
        themeVariables: { fontSize: '13px', primaryColor: c('--acento2'), primaryBorderColor: c('--acento'),
          primaryTextColor: '#1b1f24', lineColor: '#5b6472', secondaryColor: '#f3f4f6',
          tertiaryColor: '#ffffff', clusterBkg: '#f7f8fa', clusterBorder: '#c9ced6' } });
      try { await mermaid.run({ querySelector: 'div.mermaid' }); return null; } catch (e) { return String(e); }
    });
    if (err) { console.error('Mermaid:', err); process.exit(1); }
  }
  await p.pdf({ path: out, format: 'Letter', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: `<div style="font-family:Inter,sans-serif;font-size:8px;width:100%;padding:0 18mm;color:#8a919c;display:flex;justify-content:space-between"><span>${pie}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>` });
  await b.close();
})();
