#!/usr/bin/env python3
"""Free, dependency-free updater. Only reads public Real Madrid women's pages."""
import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

HOME = 'https://www.realmadrid.com/es-ES/futbol/primer-equipo-femenino'
CALENDAR = 'https://www.realmadrid.com/es-ES/calendario?filter-football=primer-equipo-femenino'
WOMEN_ID = 'vaikl8nl7hdr4y9jj4jyb9ey'
ROOT = Path(__file__).resolve().parents[1]
TEAM_NAMES = {'Real Madrid':'皇马','Bayern de Múnich':'拜仁慕尼黑','Manchester City':'曼城','Barcelona':'巴塞罗那','Espanyol':'西班牙人','Tenerife':'特内里费','Sevilla':'塞维利亚','Athletic Club':'毕尔巴鄂竞技','Paris FC':'巴黎 FC','Internazionale':'国际米兰','Badalona':'巴达洛纳','Granada':'格拉纳达','Madrid CFF':'Madrid CFF','Alavés':'阿拉维斯','Roma':'罗马','Valencia':'瓦伦西亚','Atlético Madrid':'马德里竞技','Logroño United':'洛格罗尼奥联','Real Sociedad':'皇家社会','Paris Saint-Germain':'巴黎圣日耳曼','Ajax':'阿贾克斯'}
COMPETITIONS = {'womens-champions-league':'欧冠','primera-division-femenina':'Liga F','supercopa-femenina':'超级杯','copa-de-la-reina':'王后杯'}

class StateParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.active=False; self.chunks=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='ng-state': self.active=True
    def handle_endtag(self,tag):
        if tag=='script': self.active=False
    def handle_data(self,data):
        if self.active: self.chunks.append(data)

def parse_state(html):
    p=StateParser(); p.feed(html)
    if not p.chunks: raise ValueError('官网数据结构不可识别；保留旧数据')
    state=json.loads(''.join(p.chunks))
    if not isinstance(state,dict): raise ValueError('官网状态数据无效')
    return state

def dictionaries(value):
    if isinstance(value,dict):
        yield value
        for v in value.values(): yield from dictionaries(v)
    elif isinstance(value,list):
        for v in value: yield from dictionaries(v)

def parse_time(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('来源时间缺少时区')
    return d

def parse_news(state):
    items={}
    for obj in dictionaries(state):
        tags=obj.get('tag') or []
        if not isinstance(tags,list): continue
        tag=next((t for t in tags if isinstance(t,str) and t.startswith('realmadrid-com:noticias/futbol/primer-equipo-femenino/')),None)
        if not tag or not obj.get('title') or not obj.get('date') or not obj.get('slug'): continue
        if not re.fullmatch(r'[a-z0-9-]+',obj['slug']): continue
        date=parse_time(obj['date']).astimezone(ZoneInfo('Europe/Madrid')).date().isoformat()
        url='https://www.realmadrid.com/es-ES/'+tag.split(':',1)[1]+'/'+obj['slug']
        category='比赛战报' if '/cronicas' in tag else '官方动态'
        items[url]={'title':str(obj['title'])[:300], 'summary':'西班牙语原文 · 阅读官方报道 ↗', 'publishedDate':date,'publishedAt':obj['date'],'source':'皇家马德里官网','category':category,'url':url}
    if not items: raise ValueError('未解析到女足官方新闻；保留旧数据')
    return sorted(items.values(),key=lambda x:x['publishedAt'],reverse=True)

def parse_fixtures(state,source_url=HOME):
    items={}
    for obj in dictionaries(state):
        home=obj.get('homeTeam'); away=obj.get('awayTeam')
        if not isinstance(home,dict) or not isinstance(away,dict) or not obj.get('dateTime'): continue
        if WOMEN_ID not in [home.get('optaId'),away.get('optaId')]: continue
        match_id=obj.get('optaId') or obj.get('id')
        if not match_id: continue
        raw_status=obj.get('status')
        statuses={'pre_match':'scheduled','finished':'finished','postponed':'postponed','cancelled':'cancelled','canceled':'cancelled','fixture':'scheduled'}
        if raw_status in ['playing','in_play','half_time','live']: continue  # Not a live-score service.
        if raw_status not in statuses: raise ValueError('官网出现未知比赛状态：'+str(raw_status))
        status=statuses[raw_status]; date=parse_time(obj['dateTime'])
        kickoff=date.astimezone(timezone.utc).isoformat().replace('+00:00','Z') if obj.get('isScheduled') is True else None
        score=None
        if status=='finished':
            a=obj.get('homeTeamScoreTotal'); b=obj.get('awayTeamScoreTotal')
            if not re.fullmatch(r'\d{1,2}',str(a)) or not re.fullmatch(r'\d{1,2}',str(b)): raise ValueError('已结束赛事缺少可验证比分')
            a,b=int(a),int(b)
            score=f'{a}–{b}'
        competition=obj.get('competition') or {}
        comp=COMPETITIONS.get(competition.get('slug'))
        if not comp:
            name=competition.get('name','')
            comp='Liga F' if 'Primera División Femenina' in name else '其他'
        h=home.get('name'); a=away.get('name')
        if not h or not a: raise ValueError('比赛队名缺失')
        item={'id':str(match_id),'date':date.astimezone(ZoneInfo('Europe/Madrid')).date().isoformat(),'kickoff':kickoff,'home':TEAM_NAMES.get(h,h),'away':TEAM_NAMES.get(a,a),'competition':comp,'status':status,'score':score,'venue':(obj.get('venue') or {}).get('name') or '场地待定','url':source_url,'source':'皇家马德里官网'}
        # Full match objects win over sparse copies from competition brackets.
        old=items.get(item['id'])
        if not old or (item['kickoff'] and not old['kickoff']): items[item['id']]=item
    if not items: raise ValueError('未解析到皇马女足赛事；保留旧数据')
    return list(items.values())

def merge_news(old,new):
    merged={n['url']:n for n in old}
    for n in new:
        previous=merged.get(n['url'],{})
        # Human-written Chinese summaries, if present, remain available.
        if previous.get('titleZh'): n={**n,'titleZh':previous['titleZh'],'summaryZh':previous.get('summaryZh','')}
        merged[n['url']]=n
    return sorted(merged.values(),key=lambda n:n.get('publishedAt',n['publishedDate']),reverse=True)[:30]

def merge_fixtures(old,new,now):
    merged={x['id']:x for x in old}
    merged.update({x['id']:x for x in new})
    lower=(now-timedelta(days=45)).date().isoformat(); upper=(now+timedelta(days=120)).date().isoformat()
    return sorted([x for x in merged.values() if lower<=x['date']<=upper],key=lambda x:(x['date'],x.get('kickoff') or '',x['id']))[:150]

def fetch(url):
    if url not in [HOME,CALENDAR]: raise ValueError('不支持的数据源')
    for attempt in range(3):
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'PureWhiteStand/1.0 (noncommercial football fan website)','Accept':'text/html'})
            with urllib.request.urlopen(request,timeout=35) as response:
                if response.status!=200: raise ValueError('官网返回非成功状态')
                if not response.url.startswith('https://www.realmadrid.com/'): raise ValueError('官网重定向到未知域名')
                raw=response.read(8_000_001)
                if len(raw)>8_000_000: raise ValueError('来源页面过大')
                return raw.decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code not in [429,500,502,503,504] or attempt==2: raise RuntimeError(f'官网 HTTP {e.code}，保留旧数据') from None
        except (urllib.error.URLError,TimeoutError):
            if attempt==2: raise RuntimeError('来源网络连接失败，保留旧数据') from None
        time.sleep(2**attempt)

def atomic_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(value,ensure_ascii=False,indent=2)+'\n'
    with tempfile.NamedTemporaryFile('w',dir=path.parent,encoding='utf-8',delete=False) as f:
        temp=f.name; f.write(text)
    os.replace(temp,path)

def refresh(feed,mode,fetcher=fetch,now=None):
    now=now or datetime.now(timezone.utc); stamp=now.isoformat().replace('+00:00','Z')
    result=copy.deepcopy(feed); errors=[]; cache={}
    def state(url):
        if url not in cache: cache[url]=parse_state(fetcher(url))
        return cache[url]
    for kind in ['news','fixtures']:
        if mode not in ['both',kind]: continue
        previous=result.get(kind,{'items':[],'checkedAt':None,'error':None})
        try:
            if kind=='news': items=merge_news(previous['items'],parse_news(state(HOME)))
            else:
                incoming=parse_fixtures(state(HOME))+parse_fixtures(state(CALENDAR),CALENDAR)
                items=merge_fixtures(previous['items'],incoming,now)
                if not items: raise ValueError('赛事列表异常为空')
            revision=hashlib.sha256(json.dumps(items,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
            result[kind]={'items':items,'checkedAt':stamp,'attemptedAt':stamp,'revision':revision,'error':None}
        except Exception as e:
            message=str(e)[:200]; errors.append(kind+': '+message)
            result[kind]={**previous,'attemptedAt':stamp,'error':message}
    result['mode']='github'; result['schedule']={'news':'每小时第 17 分钟（GitHub 可能延迟）','fixtures':'每天北京时间 08:37（GitHub 可能延迟）'}
    return result,errors

def main():
    p=argparse.ArgumentParser(); p.add_argument('--mode',choices=['news','fixtures','both'],default='both');p.add_argument('--data',type=Path,default=ROOT/'site/data/feed.json');args=p.parse_args()
    feed=json.loads(args.data.read_text(encoding='utf-8'))
    result,errors=refresh(feed,args.mode);atomic_json(args.data,result)
    for k in ['news','fixtures']:
        r=result[k];print(f'{k}: {len(r["items"])} records; checkedAt={r.get("checkedAt")}; error={r.get("error")}')
    if errors:
        for e in errors:print(e,file=sys.stderr)
        return 1
    return 0
if __name__=='__main__': sys.exit(main())
