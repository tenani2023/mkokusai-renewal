#!/usr/bin/env python3
"""
ビルド済み dist/ を、確認用プレビュー（Artifact）向けの単一フォルダ構成に変換する。
- 各ページを <name>.html のフラットなファイルに変換（/concept/ → concept.html）
- トップページは index.html（Artifact 本体）と top.html（下層からの戻り先）の2つ
- 160px の旧写真は data URI で埋め込み、ファイル数を抑える
- 最適化画像は img/、PDF は files/ に配置
使い方: python3 tools/export_artifact_site.py <outDir>
"""
import os, re, sys, shutil, base64, json, mimetypes

DIST = 'dist'
OUT = sys.argv[1]
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(f'{OUT}/img'); os.makedirs(f'{OUT}/files')

def page_name(rel):
    # dist/concept/index.html → concept.html,  dist/news/2026-10-13-1/index.html → news-2026-10-13-1.html
    parts = rel.split('/')[:-1]
    return 'top.html' if not parts else '-'.join(parts) + '.html'

def route_to_file(route):
    r = route.strip()
    if r in ('/', ''): return 'top.html'
    return '-'.join(p for p in r.strip('/').split('/') if p) + '.html'

pages = []
for root, _, files in os.walk(DIST):
    for f in files:
        if f.endswith('.html'):
            rel = os.path.relpath(os.path.join(root, f), DIST)
            if rel.startswith('admin/'): continue
            pages.append(rel)

used_img = set(); used_pdf = set()
BANNER = '<div class="pv-banner">確認用プレビュー：守山市国際交流協会 新ホームページ案（文章・写真は現行サイトの掲載内容）</div>'
BANNER_CSS = '<style>.pv-banner{position:sticky;top:0;z-index:200;background:#0d3f6e;color:#fff;font:700 12px/1.6 "Noto Sans JP",sans-serif;text-align:center;padding:8px 16px;letter-spacing:.04em}</style>'

def inline_legacy(m):
    src = m.group(1)
    p = os.path.join(DIST, src.lstrip('/'))
    if not os.path.exists(p): return m.group(0)
    mt = mimetypes.guess_type(p)[0] or 'image/jpeg'
    data = base64.b64encode(open(p, 'rb').read()).decode()
    return f'src="data:{mt};base64,{data}"'

def convert(html):
    # 外部 CSS をインライン化
    def repl_css(m):
        p = os.path.join(DIST, m.group(1).lstrip('/'))
        return '<style>' + open(p, encoding='utf-8').read() + '</style>' if os.path.exists(p) else ''
    html = re.sub(r'<link rel="stylesheet" href="(/_astro/[^"]+\.css)">', repl_css, html)
    # ページ内リンク
    def repl_href(m):
        attr, val = m.group(1), m.group(2)
        if val.startswith('/files/'):
            used_pdf.add(val.split('/')[-1]); return f'{attr}="files/{val.split("/")[-1]}"'
        if val.startswith('/_astro/'):
            used_img.add(val.split('/')[-1]); return f'{attr}="img/{val.split("/")[-1]}"'
        if val.startswith('/images/legacy/'):
            return m.group(0)
        if val.startswith('/') and not val.startswith('//'):
            path, _, frag = val.partition('#')
            return f'{attr}="{route_to_file(path)}{"#" + frag if frag else ""}"'
        return m.group(0)
    html = re.sub(r'\b(href|src)="([^"]*)"', repl_href, html)
    # srcset
    def repl_srcset(m):
        items = []
        for it in m.group(1).split(','):
            it = it.strip()
            if it.startswith('/_astro/'):
                name = it.split(' ')[0].split('/')[-1]; used_img.add(name)
                it = 'img/' + it[len('/_astro/'):]
            items.append(it)
        return f'srcset="{", ".join(items)}"'
    html = re.sub(r'srcset="([^"]*)"', repl_srcset, html)
    # 旧写真を data URI に
    html = re.sub(r'src="(/images/legacy/[^"]+)"', inline_legacy, html)
    html = re.sub(r'href="(/images/legacy/[^"]+)"', lambda m: 'href="#"', html)  # 拡大画像リンクは無効化
    html = html.replace('href="img/favicon.svg"', 'href="#"')
    html = re.sub(r'<link rel="icon"[^>]*>', '', html)
    html = re.sub(r'<link rel="canonical"[^>]*>', '', html)
    html = re.sub(r'<meta property="og:[^"]*"[^>]*>', '', html)
    return html

manifest = []
for rel in pages:
    html = open(os.path.join(DIST, rel), encoding='utf-8').read()
    html = convert(html)
    name = page_name(rel)
    html = html.replace('<body>', '<body>' + BANNER, 1).replace('</head>', BANNER_CSS + '</head>', 1)
    open(os.path.join(OUT, name), 'w', encoding='utf-8').write(html)
    manifest.append(name)
    if name == 'top.html':
        # Artifact 本体（スケルトンに包まれるため doctype/html/head/body を外す）
        head = re.search(r'<head>(.*?)</head>', html, re.S).group(1)
        body = re.search(r'<body>(.*?)</body>', html, re.S).group(1)
        keep = ''.join(re.findall(r'<title>.*?</title>|<link rel="stylesheet" href="https://fonts[^"]+">|<style>.*?</style>|<script>.*?</script>', head, re.S))
        open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(keep + body)

for name in used_img:
    src = os.path.join(DIST, '_astro', name)
    if os.path.exists(src): shutil.copy(src, os.path.join(OUT, 'img', name))
for name in used_pdf:
    src = os.path.join(DIST, 'files', name)
    if os.path.exists(src): shutil.copy(src, os.path.join(OUT, 'files', name))

files = sorted(manifest) + sorted(f'img/{n}' for n in os.listdir(f'{OUT}/img')) + sorted(f'files/{n}' for n in os.listdir(f'{OUT}/files'))
files = [f for f in files if f != 'index.html']
json.dump(files, open(os.path.join(OUT, '_files.json'), 'w'), ensure_ascii=False)
total = sum(os.path.getsize(os.path.join(OUT, f)) for f in files)
print(f'{len(files)} files, {total/1e6:.1f} MB; pages={len(manifest)}')
