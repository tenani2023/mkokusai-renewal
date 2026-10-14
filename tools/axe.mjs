// axe-core によるアクセシビリティ検証（WCAG 2.x A/AA）
import { spawn } from 'node:child_process';
const [base, ...paths] = process.argv.slice(2);
const CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = 9900 + Math.floor(Math.random() * 90);
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets; for (let i = 0; i < 40; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(250); } }
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Page.enable');
const axeSrc = await (await fetch('https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js')).text();
let totalV = 0;
for (const p of paths) {
  await send('Page.navigate', { url: base + p }); await sleep(2500);
  await send('Runtime.evaluate', { expression: axeSrc });
  const r = await send('Runtime.evaluate', { expression: `axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r=>JSON.stringify({v:r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,help:v.help,ex:v.nodes[0]?.target?.[0]})),passes:r.passes.length}))`, awaitPromise: true, returnByValue: true });
  const res = JSON.parse(r.result.result.value);
  totalV += res.v.length;
  console.log(`== ${p}  違反 ${res.v.length} / 合格ルール ${res.passes}`);
  for (const v of res.v) console.log(`   [${v.impact}] ${v.id} ×${v.n}: ${v.help}  e.g. ${v.ex}`);
}
console.log('TOTAL violations:', totalV);
ws.close(); chrome.kill();
