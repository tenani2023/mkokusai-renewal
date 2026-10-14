#!/usr/bin/env python3
"""
既存サイト（ホームページ・ビルダー製）の本文を、新サイト用のクリーンな HTML に変換する。
文章は変更せず、構造（見出し・段落・写真ギャラリー・表）だけを整える。

使い方: python3 tools/convert_page.py <mirrorDir> <page> [<page> ...]
出力:   src/content/pages/<page>.html, public/images/legacy/*, public/files/*
"""
import sys, os, re, html, shutil, json
from html.parser import HTMLParser

MIRROR = sys.argv[1]
PAGES = sys.argv[2:]
OUT_DIR = 'src/content/pages'
IMG_DIR = 'public/images/legacy'
PDF_DIR = 'public/files'
os.makedirs(OUT_DIR, exist_ok=True); os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(PDF_DIR, exist_ok=True)

ROUTES = {
    'index.html': '/', 'concept.html': '/concept/', 'eventnews.html': '/eventnews/', 'japanese.html': '/japanese/',
    'portugues.html': '/interpreter/', 'sistercity.html': '/sistercity/', 'speech.html': '/speech/',
    'wanted.html': '/wanted/', 'contact.html': '/contact/', 'link.html': '/link/', 'festival.html': '/festival/',
}
RED = {'#ff0000', '#990000', '#cc0000'}
BLUE = {'#0e7bbf', '#3894ce', '#0000ff', '#0000cc', '#000099'}
GREEN = {'#009900', '#009999'}

# ---------- 簡易 DOM ----------
class Node:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag; self.attrs = dict(attrs or {}); self.children = []; self.parent = parent
    def text(self):
        return ''.join(c if isinstance(c, str) else c.text() for c in self.children)

VOID = {'br', 'img', 'hr', 'input', 'meta', 'link'}

class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root'); self.cur = self.root; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1; return
        if self.skip: return
        # 閉じタグ省略（li / p / tr / td）への対応
        implicit = {'li': ('li',), 'p': ('p',), 'tr': ('tr', 'td', 'th'), 'td': ('td', 'th'), 'th': ('td', 'th'),
                    'table': ('p',), 'ul': ('p',), 'ol': ('p',), 'div': ('p',), 'h3': ('p',), 'h4': ('p',), 'h5': ('p',)}
        if tag in implicit:
            n = self.cur
            while n is not None and n.tag not in ('root', 'table', 'ul', 'ol', 'td', 'th', 'div') :
                if n.tag in implicit[tag]:
                    self.cur = n.parent; break
                n = n.parent
        n = Node(tag, attrs, self.cur); self.cur.children.append(n)
        if tag not in VOID: self.cur = n
    def handle_startendtag(self, tag, attrs):
        if self.skip: return
        self.cur.children.append(Node(tag, attrs, self.cur))
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1); return
        if self.skip: return
        n = self.cur
        while n is not None and n.tag != tag: n = n.parent
        if n is not None and n.parent is not None: self.cur = n.parent
    def handle_data(self, d):
        if self.skip: return
        self.cur.children.append(d)
    def handle_comment(self, d): pass

def extract_main(src):
    i = src.find('<div id="hpb-main">')
    j = src.find('<!-- main end -->')
    if i < 0: raise SystemExit('hpb-main not found')
    return src[i:j if j > 0 else None]

# ---------- インライン整形 ----------
def color_class(attrs):
    c = (attrs.get('color') or '').lower().strip()
    if c in RED: return 'c-red'
    if c in BLUE: return 'c-blue'
    if c in GREEN: return 'c-green'
    if c in ('#000000', '#000', 'black'): return 'c-black'
    return None

def norm_space(s):
    s = s.replace('　', ' ')
    return re.sub(r'[ \t\r\n]+', ' ', s)

def inline_html(node, ctx):
    """インライン要素を HTML 文字列へ。ブロック境界（br / img）は特別トークンで返す"""
    parts = []
    for c in node.children:
        if isinstance(c, str):
            parts.append(html.escape(norm_space(c), quote=False)); continue
        t = c.tag
        if t == 'br': parts.append('\x00BR\x00'); continue
        if t == 'img':
            parts.append(img_token(c, ctx)); continue
        if t == 'a':
            href = c.attrs.get('href', '') or ''
            inner = inline_html(c, ctx)
            # 画像だけを包むリンク（拡大画像・PDF）
            if '\x00IMG' in inner and not re.sub(r'\x00IMG[^\x00]*\x00|\x00BR\x00| ', '', inner):
                parts.append(inner.replace('\x00IMG||', f'\x00IMG|{map_href(href, ctx)}|'))
                continue
            if not inner.strip() or href.startswith('#'):
                parts.append('' if href.startswith('#') else inner); continue
            if href.startswith('mailto:mkokusai@usennet'):  # 旧アドレスは廃止
                parts.append(inner); continue
            parts.append(link_html(href, inner, ctx)); continue
        if t in ('font', 'span'):
            cls = color_class(c.attrs) if t == 'font' else None
            inner = inline_html(c, ctx)
            parts.append(f'\x00C:{cls}\x00{inner}\x00/C\x00' if cls else inner); continue
        if t in ('b', 'strong'):
            parts.append('\x00C:strong\x00' + inline_html(c, ctx) + '\x00/C\x00'); continue
        if t in ('i', 'em'):
            parts.append('<em>' + inline_html(c, ctx) + '</em>'); continue
        parts.append(inline_html(c, ctx))
    return ''.join(parts)

def map_href(href, ctx):
    href = href.strip()
    if not href or href == 'None': return ''
    if href.startswith(('http://', 'https://')):
        if 'mkokusai.org/' in href:
            href = href.split('mkokusai.org/')[1]
        else:
            return href
    if href.startswith('mailto:'): return href
    base = os.path.basename(href.split('#')[0])
    if base in ROUTES: return ROUTES[base]
    if base.lower().endswith('.pdf'):
        src = os.path.join(MIRROR, base)
        if os.path.exists(src): shutil.copy(src, os.path.join(PDF_DIR, base)); ctx['pdfs'].add(base)
        return f'/files/{base}'
    if re.search(r'\.(jpe?g|png|gif)$', base, re.I):
        return copy_img(base, ctx)
    return href

def copy_img(base, ctx):
    src = os.path.join(MIRROR, base)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(IMG_DIR, base)); ctx['imgs'].add(base)
        return f'/images/legacy/{base}'
    ctx['missing'].add(base); return ''

def link_html(href, inner, ctx):
    h = map_href(href, ctx)
    if not h: return inner
    ext = h.startswith('http')
    attrs = f' href="{h}"'
    if ext: attrs += ' target="_blank" rel="noopener"'
    if h.endswith('.pdf'): attrs += ' target="_blank" rel="noopener"'; inner = inner if 'PDF' in inner else inner
    return f'<a{attrs}>{inner}</a>'

def img_token(c, ctx):
    src = os.path.basename(c.attrs.get('src', ''))
    alt = (c.attrs.get('alt') or '').strip()
    if src == 'map.png': alt = '守山市民交流センター周辺の地図'
    path = copy_img(src, ctx)
    if not path: return ''
    w = c.attrs.get('width', ''); h = c.attrs.get('height', '')
    style = c.attrs.get('style', '') or ''
    kind = 'poster' if 'float' in style and not alt else ('button' if src.lower().endswith('.gif') else 'photo')
    return f'\x00IMG||{path}|{alt}|{w}|{h}|{kind}\x00'

# ---------- ブロック構築 ----------
def fix_link_breaks(s):
    s = re.sub(r'(<a [^>]*>)((?:\s|\x00BR\x00)+)', r'\2\1', s)
    s = re.sub(r'((?:\s|\x00BR\x00)+)(</a>)', r'\2\1', s)
    s = s.replace('このページの先頭へ', '').replace('このページの先頭', '')
    return s

def finish_colors(s):
    """色/太字トークンを、実効スタイル（最も内側の色・太字の有無）で HTML に変換する"""
    out = []; stack = []
    for tok in re.split(r'(\x00C:[a-z-]+\x00|\x00/C\x00)', s):
        if tok.startswith('\x00C:'):
            stack.append(tok[3:-1])
        elif tok == '\x00/C\x00':
            if stack: stack.pop()
        elif tok:
            colors = [n for n in stack if n != 'strong']
            color = colors[-1] if colors else None
            if color == 'c-black': color = None
            bold = 'strong' in stack
            seg = tok
            if color: seg = f'<span class="{color}">{seg}</span>'
            if bold: seg = f'<strong>{seg}</strong>'
            out.append(seg)
    s = ''.join(out)
    s = re.sub(r'</strong><strong>', '', s)
    s = re.sub(r'</span><span class="([a-z-]+)">', '', s)  # 同じ色が連続する場合は結合（直前と同じクラスのみ）
    s = re.sub(r'<span class="([a-z-]+)">(\s*)</span>', r'\2', s)
    s = re.sub(r'<strong>(\s*)</strong>', r'\1', s)
    return s

def plain(s):
    s = re.sub(r'\x00C:[a-z-]+\x00|\x00/C\x00', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(s).strip()

def normalize_lines(s):
    """BR で行に分けたとき、色スパンが行をまたがないように閉じて開き直す"""
    out = []; stack = []
    for tok in re.split(r'(\x00C:[a-z-]+\x00|\x00/C\x00|\x00BR\x00)', s):
        if tok.startswith('\x00C:'):
            stack.append(tok); out.append(tok)
        elif tok == '\x00/C\x00':
            if stack: stack.pop(); out.append(tok)
        elif tok == '\x00BR\x00':
            out.append('\x00/C\x00' * len(stack)); out.append(tok); out.extend(stack)
        else:
            out.append(tok)
    return ''.join(out)

def strip_colors(s):
    return re.sub(r'\x00C:[a-z-]+\x00|\x00/C\x00', '', s)

def is_colored_line(line):
    """行のテキストがすべて色付き（赤/青/緑）の範囲内にあるか（黒指定は無色扱い）"""
    txt = plain(line)
    if not txt: return False
    stack = []; outside = ''
    for tok in re.split(r'(\x00C:[a-z-]+\x00|\x00/C\x00)', line):
        if tok.startswith('\x00C:'):
            stack.append(tok[3:-1])
        elif tok == '\x00/C\x00':
            if stack: stack.pop()
        else:
            colors = [n for n in stack if n != 'strong']
            eff = colors[-1] if colors else None
            if (eff is None and 'strong' not in stack) or eff == 'c-black' and 'strong' not in stack:
                outside += tok
    return not plain(outside).strip()

LABEL_RE = re.compile(r'^(第[０-９0-9]+日目|＜.*＞|<.*>)')
def is_label(line):
    t = plain(line)
    return bool(t) and len(t) <= 40 and (LABEL_RE.match(t) is not None or is_colored_line(line)) and not re.search(r'[。]$', t)

def heading_level(line):
    txt = plain(line)
    if not txt or len(txt) > 70: return None
    if txt.startswith(('【', '※', '・', '〒', 'TEL', 'Mail', 'MAIL', '＜', '<')): return None
    if '→' in txt or '・・・' in txt: return None
    if re.search(r'[。、]$', txt) and not re.search(r'(開催しました|実施しました|作成しました|帰国されました|来市されました|開催します|参加しました|開催されました)[。！]?$', txt): return None
    if is_colored_line(line): return 3
    return None

def convert_blocks(root, ctx):
    out = []           # 出力ブロック（文字列）
    cur_heading = ''
    def flush_para(lines):
        nonlocal cur_heading
        lines = [l for l in (ln.strip() for ln in lines) if plain(l)]
        if not lines: return
        # 行ごとに見出し判定
        buf = []
        def emit_para():
            if not buf: return
            if all(is_colored_line(b) for b in buf):
                body = '<br>'.join(strip_colors(b) for b in buf)
            else:
                body = '<br>'.join(buf)
            out.append('<p>' + finish_colors(body) + '</p>'); buf.clear()
        skip = 0
        for i, ln in enumerate(lines):
            if skip: skip -= 1; continue
            if plain(ln) in ('お知らせ', '開催報告'):
                emit_para(); out.append(f'<h2>{plain(ln)}</h2>'); continue
            lv = heading_level(ln)
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            # 色付きの文章が折り返されているだけの場合は見出しにしない／結合する
            if lv and nxt and is_colored_line(nxt) and not re.search(r'[。！!」～】]$', plain(ln)):
                merged = ln + ' ' + nxt
                if len(plain(merged)) <= 90 and heading_level(nxt) is not None:
                    ln = merged; skip = 1; nxt = lines[i + 2] if i + 2 < len(lines) else ''
                else:
                    lv = None
            if lv:
                # 次行が「～…～」のサブタイトルなら、現在行を見出し・次行を副題に
                if nxt and heading_level(nxt) and plain(nxt).startswith(('～', '〜', '「')):
                    eyebrow = ''
                    if buf and len(plain(buf[-1])) <= 24 and not re.search(r'[。！]$|@|TEL|Mail|MAIL|【', plain(buf[-1])):
                        eyebrow = buf.pop()
                    emit_para(); cur_heading = plain(ln)
                    if eyebrow: out.append(f'<p class="eyebrow">{plain(eyebrow)}</p>')
                    out.append(f'<h3>{strip_colors(ln).strip()}</h3>')
                    out.append(f'<p class="subtitle">{strip_colors(nxt).strip()}</p>'); skip = 1; continue
                # 「もりやま”夢”プロジェクト」のような短い前段 → 見出しの上書き（eyebrow）
                if nxt and heading_level(nxt) and len(plain(ln)) <= 24 and not re.search(r'[！!。]$', plain(ln)):
                    emit_para(); out.append(f'<p class="eyebrow">{plain(ln)}</p>'); continue
                eyebrow = ''
                if buf and len(plain(buf[-1])) <= 24 and not re.search(r'[。！]$|@|TEL|Mail|MAIL|【', plain(buf[-1])):
                    eyebrow = buf.pop()
                emit_para()
                cur_heading = plain(ln)
                if eyebrow: out.append(f'<p class="eyebrow">{plain(eyebrow)}</p>')
                out.append(f'<h3>{strip_colors(ln).strip()}</h3>')
            else:
                buf.append(ln)
        emit_para()

    def handle_inline_run(s):
        """段落内の文字列を、テキスト行と画像列に分けて出力"""
        s = normalize_lines(fix_link_breaks(s))
        segs = re.split(r'(\x00IMG[^\x00]*\x00)', s)
        lines = []; gallery = []; nonlocal_photos = [False]
        def flush_gallery():
            if not gallery: return
            items = []
            for g in gallery:
                _, href, path, alt, w, h, kind = g.strip('\x00').split('|')
                if kind == 'button':
                    label = alt or 'ダウンロード'
                    items.append(('button', f'<a class="btn btn--ghost btn--sm" href="{href or path}" target="_blank" rel="noopener">{label}</a>'))
                    continue
                a = alt or (f'{cur_heading}の写真' if cur_heading else '活動の写真')
                img = f'<img src="{path}" alt="{html.escape(a)}" loading="lazy" decoding="async">'
                if href: img = f'<a href="{href}" target="_blank" rel="noopener">{img}</a>'
                items.append((kind, img))
            buttons = [i for k, i in items if k == 'button']
            posters = [i for k, i in items if k == 'poster']
            photos = [i for k, i in items if k == 'photo']
            nonlocal_photos[0] = bool(photos)
            if posters: out.append('<figure class="poster">' + ''.join(posters) + '</figure>')
            if photos:
                if len(photos) == 1: out.append('<figure class="photo">' + photos[0] + '</figure>')
                else: out.append('<ul class="gallery">' + ''.join(f'<li>{p}</li>' for p in photos) + '</ul>')
            if buttons: out.append('<p class="buttons">' + ''.join(buttons) + '</p>')
            gallery.clear()
        for seg in segs:
            if seg.startswith('\x00IMG'):
                # 画像の前にたまっていたテキストを段落に（末尾が「第１日目 …」等のラベルなら切り出す）
                label = ''
                while lines and not plain(lines[-1]): lines.pop()
                if lines and is_label(lines[-1]) and not heading_level(lines[-1]) and len(lines) >= 1:
                    label = lines.pop()
                if any(plain(l) for l in lines): flush_para(lines); lines = []
                if label: out.append(f'<p class="label">{strip_colors(label).strip()}</p>')
                gallery.append(seg)
            else:
                seg_lines = seg.split('\x00BR\x00')
                for k, ln in enumerate(seg_lines):
                    if plain(ln):
                        if gallery:
                            flush_gallery()
                            t = plain(ln)
                            nxt = next((x for x in seg_lines[k + 1:] if plain(x)), '')
                            # 直後に見出しが続く短い行は見出しの前段なので通常処理へ
                            if nxt and heading_level(nxt) and len(t) <= 24:
                                lines.append(ln); continue
                            if is_label(ln) and not heading_level(ln):
                                out.append(f'<p class="label">{strip_colors(ln).strip()}</p>'); continue
                            # ギャラリー直後の短い黒字行はキャプション
                            if nonlocal_photos[0] and len(t) <= 60 and not re.search(r'開催|年度|\d年|実施|募集|第\d+回', t):
                                out.append(f'<p class="caption">{strip_colors(ln).strip()}</p>'); continue
                        lines.append(ln)
                    else:
                        if lines: lines.append('')  # 空行＝段落区切り
        if gallery: flush_gallery()
        # 段落区切りで分割
        para = []
        for ln in lines:
            if ln == '':
                if para: flush_para(para); para = []
            else: para.append(ln)
        if para: flush_para(para)

    def walk(node):
        for c in node.children:
            if isinstance(c, str):
                if c.strip(): handle_inline_run(html.escape(norm_space(c), quote=False))
                continue
            t = c.tag
            if t in ('h2',): continue                      # ページ見出しは新サイト側で付与
            if t == 'a' and (c.attrs.get('href') or '').startswith('#'): continue  # 先頭へ
            if t in ('h3', 'h4', 'h5'):
                ih = inline_html(c, ctx); txt = plain(ih)
                # ホームページ・ビルダーは h3 を本文のコンテナとして使うことがある
                if len(txt) > 80 or '\x00IMG' in ih or any((not isinstance(x, str)) and x.tag in ('p', 'div', 'table', 'ul', 'ol') for x in c.children):
                    if any((not isinstance(x, str)) and x.tag in ('p', 'div', 'table', 'ul', 'ol') for x in c.children): walk(c)
                    else: handle_inline_run(ih)
                elif txt:
                    out.append(f'<{t}>{finish_colors(ih).replace(chr(0)+"BR"+chr(0), "<br>")}</{t}>')
                continue
            if t == 'table':
                out.append(table_html(c, ctx)); continue
            if t in ('ul', 'ol'):
                items = []
                for li in c.children:
                    if isinstance(li, str) or li.tag != 'li': continue
                    inner = finish_colors(inline_html(li, ctx)).replace('\x00BR\x00', '<br>')
                    inner = re.sub(r'\x00IMG[^\x00]*\x00', '', inner).strip()
                    if plain(inner): items.append(f'<li>{inner}</li>')
                if items: out.append(f'<{t}>' + ''.join(items) + f'</{t}>')
                continue
            if t in ('p', 'div', 'center', 'font', 'span', 'b', 'strong', 'em', 'i', 'a', 'img', 'br', 'blockquote', 'tbody'):
                if t in ('p', 'div', 'center', 'blockquote'):
                    # ブロック要素の子にブロックが含まれる場合は再帰、そうでなければインライン処理
                    if any((not isinstance(x, str)) and x.tag in ('p', 'div', 'table', 'ul', 'ol', 'h3', 'h4', 'h5', 'center', 'blockquote') for x in c.children):
                        walk(c)
                    else:
                        handle_inline_run(inline_html(c, ctx))
                else:
                    handle_inline_run(inline_html(Node('tmp', children_of=[c]) if False else wrap(c), ctx))
                continue
            walk(c)
    def wrap(c):
        n = Node('tmp'); n.children = [c]; return n
    walk(root)
    return out

def table_html(tnode, ctx):
    rows = []
    def cells(tr):
        cs = []
        for td in tr.children:
            if isinstance(td, str) or td.tag not in ('td', 'th'): continue
            inner = finish_colors(inline_html(td, ctx)).replace('\x00BR\x00', '<br>')
            inner = re.sub(r'\x00IMG[^\x00]*\x00', '', inner)
            inner = re.sub(r'^(\s|<br>)+|(\s|<br>)+$', '', inner)
            attrs = ''
            for k in ('colspan', 'rowspan'):
                if td.attrs.get(k): attrs += f' {k}="{td.attrs[k]}"'
            cs.append(f'<{td.tag}{attrs}>{inner}</{td.tag}>')
        return cs
    def find_rows(n):
        for c in n.children:
            if isinstance(c, str): continue
            if c.tag == 'tr':
                cs = cells(c)
                if any(plain(x) for x in cs): rows.append('<tr>' + ''.join(cs) + '</tr>')
            else: find_rows(c)
    find_rows(tnode)
    if not rows: return ''
    return '<div class="table-wrap"><table>' + ''.join(rows) + '</table></div>'

def tidy(blocks):
    s = '\n'.join(b for b in blocks if b)
    # 「もりやま”夢”プロジェクト」が見出しに含まれる場合は上書き（eyebrow）に分離
    s = re.sub(r'<h3>(もりやま[”"]夢[”"]プロジェクト)\s+(.*?)</h3>', r'<p class="eyebrow">\1</p>\n<h3>\2</h3>', s)
    s = s.replace('\x00BR\x00', '<br>')
    s = re.sub(r'\x00IMG[^\x00]*\x00', '', s)
    s = finish_colors(s)
    s = re.sub(r'(<br>\s*){2,}', '<br>', s)
    s = re.sub(r'<p>(\s|<br>)*</p>', '', s)
    s = re.sub(r'<p>\s*<br>', '<p>', s); s = re.sub(r'<br>\s*</p>', '</p>', s)
    s = re.sub(r' +', ' ', s)
    s = re.sub(r'<p>\s+', '<p>', s); s = re.sub(r'\s+</p>', '</p>', s)
    s = re.sub(r'<h3>\s+', '<h3>', s); s = re.sub(r'\s+</h3>', '</h3>', s)
    return s.strip() + '\n'

def dedupe(s):
    """姉妹都市ページのような、同一ブロックの重複掲載を除去する"""
    blocks = s.split('\n')
    seen = set(); out = []; dup_run = 0
    for b in blocks:
        key = re.sub(r'\s+', '', b)
        if len(key) > 40 and key in seen:
            dup_run += 1; continue
        seen.add(key); out.append(b)
    return '\n'.join(out) + '\n', dup_run

summary = {}
for page in PAGES:
    ctx = {'imgs': set(), 'pdfs': set(), 'missing': set()}
    src = open(os.path.join(MIRROR, page + '.html'), encoding='utf-8', errors='replace').read()
    tb = TreeBuilder(); tb.feed(extract_main(src))
    blocks = convert_blocks(tb.root, ctx)
    out = tidy(blocks)
    if '<h2>' not in out:
        h3s = re.findall(r'<h3>(.*?)</h3>', out)
        if any(re.search(r'\d{4}', h) for h in h3s):
            out = re.sub(r'<h3>([^<]*\d{4}.*?)</h3>', r'<h2>\1</h2>', out)
        else:
            out = out.replace('<h3>', '<h2>').replace('</h3>', '</h2>')
    dups = 0
    if page == 'sistercity':
        first = out.find('<h2>開催報告</h2>'); second = out.find('<h2>開催報告</h2>', first + 1)
        if second > 0: dups = out[second:].count('\n'); out = out[:second]
    open(os.path.join(OUT_DIR, page + '.html'), 'w', encoding='utf-8').write(out)
    heads = re.findall(r'<h3>(.*?)</h3>', out)
    summary[page] = {'bytes': len(out), 'images': len(ctx['imgs']), 'pdfs': sorted(ctx['pdfs']), 'missing': sorted(ctx['missing']), 'duplicates_removed': dups, 'h3': heads}
    print(f'{page}: {len(out)} bytes, {len(ctx["imgs"])} images, {len(heads)} headings, dup-removed {dups}, missing {sorted(ctx["missing"])}')
json.dump(summary, open(os.path.join(OUT_DIR, '_summary.json'), 'w'), ensure_ascii=False, indent=1)
