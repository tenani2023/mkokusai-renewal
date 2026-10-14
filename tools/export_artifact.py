# ビルド済み dist/index.html を Artifact 用（<title>+<style>+本文）に変換する
import re, os, shutil, sys
dist='dist'; out='/private/tmp/claude-501/-Users-asanohinata/e65b4f07-6ceb-48a5-888f-346b861452f2/scratchpad/artifact'
shutil.rmtree(out, ignore_errors=True); os.makedirs(out+'/img')
html=open(f'{dist}/index.html',encoding='utf-8').read()
# CSS をインライン化
css=''
for m in re.finditer(r'<link rel="stylesheet" href="(/_astro/[^"]+\.css)">',html):
    css+=open(dist+m.group(1),encoding='utf-8').read()+'\n'
head=re.search(r'<head>(.*?)</head>',html,re.S).group(1)
body=re.search(r'<body>(.*?)</body>',html,re.S).group(1)
fonts=''.join(re.findall(r'<link rel="stylesheet" href="https://fonts[^"]+">',head))
scripts=''.join(re.findall(r'<script>.*?</script>',head,re.S))
# 画像パスを相対に
body=body.replace('/_astro/','img/')
# 内部リンクはプレビューでは無効のため、その旨を知らせる
body=re.sub(r'href="(/[^"#]*)"', r'href="#" data-href="\1"', body)
banner='<div class="pv-banner">デザイン確認用プレビュー（トップページ）：下層ページは次工程で制作するため、ページ内リンクは動作しません。</div>'
page=f'''<title>守山市国際交流協会 トップページ案</title>
{fonts}
<style>
{css}
.pv-banner{{position:sticky;top:0;z-index:200;background:#0d3f6e;color:#fff;font:700 12px/1.6 "Noto Sans JP",sans-serif;text-align:center;padding:8px 16px;letter-spacing:.04em}}
</style>
{scripts}
{banner}
{body}
<script>document.querySelectorAll('a[data-href]').forEach(a=>a.addEventListener('click',e=>e.preventDefault()));</script>
'''
open(out+'/index.html','w',encoding='utf-8').write(page)
# 参照している画像のみコピー
used=set(re.findall(r'img/([^"\s,]+\.(?:avif|webp|jpg|png))',page))
for f in used: shutil.copy(f'{dist}/_astro/{f}',f'{out}/img/{f}')
print(len(page),'bytes;',len(used),'images')
for f in sorted(used): print(f)
