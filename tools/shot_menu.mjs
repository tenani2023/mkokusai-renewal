import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const [url, out] = process.argv.slice(2);
const CH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const port = 9335;
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, '--window-size=1600,1000', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets; for (let i = 0; i < 40; i++) { try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); break; } catch { await sleep(250); } }
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
await send('Page.navigate', { url }); await sleep(2500);
await send('Runtime.evaluate', { expression: "document.querySelector('.menu-btn').click()" }); await sleep(800);
const a = await send('Runtime.evaluate', { expression: "JSON.stringify({expanded: document.querySelector('.menu-btn').getAttribute('aria-expanded'), focus: document.activeElement.textContent.trim(), bodyClass: document.body.className})", returnByValue: true });
console.log(a.result.result.value);
const shot = await send('Page.captureScreenshot', { format: 'png' });
writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
// Escape で閉じる
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape', windowsVirtualKeyCode: 27 });
await sleep(400);
const b = await send('Runtime.evaluate', { expression: "document.body.className + ' / ' + document.querySelector('.menu-btn').getAttribute('aria-expanded')", returnByValue: true });
console.log('after Escape:', b.result.result.value);
ws.close(); chrome.kill();
