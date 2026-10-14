import re, html, json, sys, os, unicodedata
src = open(sys.argv[1], encoding='utf-8').read()
block = src.split('id="toppage-news"')[1].split('</ul>')[0]
items = re.findall(r'<li>(.*?)(?=<li>|$)', block, re.S)
pagemap = {'speech.html':'/speech/','eventnews.html':'/eventnews/','sistercity.html':'/sistercity/',
           'festival.html':'/festival/','http://mkokusai.org/festival.html':'/festival/','wanted.html':'/wanted/'}
out=[]
for raw in items:
    t = re.sub(r'<font[^>]*>|</font>','',raw)
    href = re.search(r'href="([^"]+)"', t)
    href = href.group(1) if href else None
    text = re.sub(r'<[^>]+>','',t)
    text = html.unescape(text).replace('　',' ')
    text = re.sub(r'\s+',' ',text).strip()
    m = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(.*)', text)
    if not m: print('SKIP', text); continue
    y,mo,d,title = m.groups()
    title = title.strip()
    date = f'{y}-{int(mo):02d}-{int(d):02d}'
    if href and 'sistercity' in href: cat='姉妹都市'
    elif '募集' in title: cat='参加者募集'
    elif re.search(r'開催しました|開催報告|受入|受 入|帰国', title): cat='開催報告'
    else: cat='お知らせ'
    out.append(dict(date=date,title=title,category=cat,link=pagemap.get(href) if href else None, old_href=href))
# slugs: date + index
counts={}
for o in out:
    counts[o['date']]=counts.get(o['date'],0)+1
seen={}
for o in out:
    n=seen.get(o['date'],0)+1; seen[o['date']]=n
    o['slug']=o['date'] if counts[o['date']]==1 else f"{o['date']}-{n}"
json.dump(out, open('src/data/news_seed.json','w'), ensure_ascii=False, indent=1)
for o in out:
    fm = ['---', f'title: "{o["title"]}"', f'date: {o["date"]}', f'category: "{o["category"]}"']
    if o['link']: fm.append(f'link: "{o["link"]}"')
    fm += ['draft: false','---','']
    body = ''
    if o['link']:
        body = f'詳しくは[関連ページ]({o["link"]})をご覧ください。\n'
    open(f'src/content/news/{o["slug"]}.md','w').write('\n'.join(fm)+body)
print(len(out),'entries')
for o in out: print(o['date'], o['category'], o['title'], o['old_href'])
