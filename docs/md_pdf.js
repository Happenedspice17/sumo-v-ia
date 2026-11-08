// Uso: node docs/md_pdf.js entrada.html salida.pdf "Titulo pie"
const { chromium } = require('playwright');
(async () => {
  const [inp, out, pie] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + require('path').resolve(inp));
  await p.pdf({ path: out, format: 'Letter', printBackground: true, preferCSSPageSize: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: `<div style="font-size:9px;width:100%;padding:0 18mm;color:#777;display:flex;justify-content:space-between"><span>${pie}</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>` });
  await b.close();
})();
