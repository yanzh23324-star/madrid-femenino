from pathlib import Path
import html
import json
ROOT = Path(__file__).resolve().parents[1]

def glossary_html(glossary):
    esc = html.escape
    rows = []
    for entry in glossary['entries']:
        source = glossary['sources'].get(entry.get('source'))
        basis = esc(entry['basis'])
        if source:
            basis = '<a target="_blank" rel="noopener" href="'+esc(source['url'], quote=True)+'">'+basis+' ↗</a>'
        rows.append('<tr><td>'+esc(entry['aliases'][0])+'</td><td>'+esc(entry['zh'])+'</td><td>'+esc(entry['kind'])+'</td><td>'+basis+'</td></tr>')
    return ('<details class="glossary" id="translation-glossary"><summary>常用译名表 · 球员、球队与赛事</summary><p>'
            +esc(glossary['note'])+'<br>最近核对：'+esc(glossary['reviewedAt'])
            +' · 表内译名用于自动粗译，既有人工整理保留原有表述。</p><div class="glossary-scroll"><table><thead><tr><th scope="col">原名 / 术语</th><th scope="col">本站采用译写</th><th scope="col">类别</th><th scope="col">参考依据</th></tr></thead><tbody>'
            +''.join(rows)+'</tbody></table></div></details>')

def main():
    template = (ROOT/'src/template.html').read_text(encoding='utf-8')
    feed = json.loads((ROOT/'site/data/feed.json').read_text(encoding='utf-8'))
    glossary = json.loads((ROOT/'data/translation-glossary.json').read_text(encoding='utf-8'))
    seed = json.dumps(feed,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    (ROOT/'site/index.html').write_text(template.replace('__FEED_JSON__',seed).replace('__GLOSSARY_HTML__',glossary_html(glossary)),encoding='utf-8')
    (ROOT/'site/.nojekyll').touch()
if __name__=='__main__': main()
