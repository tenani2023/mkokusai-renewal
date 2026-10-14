// 使い方: node tools/shot.mjs <url> <width> <out.png> [mobile=1] [maxHeight]
import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const [url, w, out, mobile = '0', maxH = '6000'] = process.argv.slice(2);
const CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = 9400 + Math.floor(Math.random() * 400);
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, '--window-size=1600,1000', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 40; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(250); } }
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: +w, height: 900, deviceScaleFactor: 1, mobile: mobile === '1' });
await send('Page.navigate', { url });
await sleep(3000);
// すべての reveal を表示状態にしてから全体を撮影
await send('Runtime.evaluate', { expression: "document.querySelectorAll('.reveal').forEach(e=>e.classList.add('is-visible')); window.scrollTo(0,0);" });
const m = await send('Runtime.evaluate', { expression: 'JSON.stringify({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth, vw: document.documentElement.clientWidth})', returnByValue: true });
const { h, w: sw, vw } = JSON.parse(m.result.result.value);
const H = Math.min(h, +maxH);
await send('Emulation.setDeviceMetricsOverride', { width: +w, height: H, deviceScaleFactor: 1, mobile: mobile === '1' });
await sleep(800);
const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: +w, height: H, scale: 1 } });
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
console.log(`saved ${out} ${w}x${H} (scrollWidth=${sw}, clientWidth=${vw})`);
ws.close(); chrome.kill();
