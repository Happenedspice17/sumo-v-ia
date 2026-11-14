// Graba la animacion de una corrida cuadro por cuadro. Uso: node graba_video.js pagina.html carpeta_cuadros [velocidad] [fps]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [pag, dir, vel = 4, fps = 30] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.resolve(pag) + '?captura=1');
  const fin = await p.evaluate(() => window.FIN);
  const pre = 1.5 * fps, post = 3.5 * fps, n = Math.ceil(fin / vel * fps);
  const lienzo = p.locator('canvas');
  for (let k = 0; k < pre + n + post; k++) {
    const t = Math.min(Math.max((k - pre) / fps * vel, 0), fin);
    await p.evaluate((t) => window.dibuja(t), t);
    await lienzo.screenshot({ path: path.join(dir, String(k).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 93 });
  }
  await b.close();
  console.log('cuadros:', pre + n + post);
})();
