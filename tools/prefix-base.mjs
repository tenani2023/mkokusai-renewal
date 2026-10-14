// サブディレクトリ配信（GitHub Pages プレビュー）用に、ビルド済み HTML 内の
// ルート相対リンク（href="/..." / src="/..."）へ base パスを付与する。
// 使い方: node tools/prefix-base.mjs dist /mkokusai-renewal
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const [dir, base] = process.argv.slice(2);
if (!dir || !base) { console.error('usage: prefix-base.mjs <dist> <base>'); process.exit(1); }

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });
let n = 0;
for (const file of walk(dir)) {
  if (!/\.(html|xml|txt|webmanifest)$/.test(file)) continue;
  const src = readFileSync(file, 'utf8');
  const out = src.replace(/(href|src|content|srcset)="\/(?!\/)/g, (m, attr) => {
    return `${attr}="${base}/`;
  }).replace(new RegExp(`${base}${base}/`, 'g'), `${base}/`);
  if (out !== src) { writeFileSync(file, out); n++; }
}
console.log(`prefixed ${n} files with ${base}`);
