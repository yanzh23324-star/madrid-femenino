from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]
def main():
 template=(ROOT/'src/template.html').read_text(encoding='utf-8')
 feed=json.loads((ROOT/'site/data/feed.json').read_text(encoding='utf-8'))
 # JSON embedded in a script must not be able to close the element.
 seed=json.dumps(feed,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
 (ROOT/'site/index.html').write_text(template.replace('__FEED_JSON__',seed),encoding='utf-8')
 (ROOT/'site/.nojekyll').touch()
if __name__=='__main__':main()
