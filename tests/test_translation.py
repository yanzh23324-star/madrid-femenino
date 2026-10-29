import copy
import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import translate as t
import update as u
import build as b
GLOSSARY = json.loads((ROOT/'data/translation-glossary.json').read_text())
NOW = datetime(2026,10,29,tzinfo=timezone.utc)

def story(title='Schröder juega en 2026', **kw):
    return {'title':title,'url':'https://www.realmadrid.com/es-ES/test','publishedDate':'2026-10-29',**kw}
def feed(*items):return {'news':{'items':list(items),'checkedAt':'old'},'fixtures':{'items':[{'id':'unchanged'}]}}
class Model:
    def __init__(self, output=None, error=None):self.output=output;self.error=error;self.calls=0
    def batch(self,texts):
        self.calls+=1
        if self.error:raise self.error
        return self.output

class TranslationTests(unittest.TestCase):
    def test_official_names_longest_match_and_word_boundaries(self):
        masked, saved=t.protect('Linda Caicedo y Schröder contra Real Madrid; International',GLOSSARY)
        self.assertEqual([x[1] for x in saved],['L·凯塞多','施罗德','皇马'])
        self.assertIn('International',masked)
        self.assertEqual(t.restore(masked,saved),'L·凯塞多 y 施罗德 contra 皇马; International')
    def test_success_persists_exact_source_and_preserves_manual(self):
        old=feed(story(),story('Manual',titleZh='人工标题',summaryZh='人工摘要'))
        engine=Model(['ZXQA在2026年出场'])
        new,errors=t.translate_feed(old,GLOSSARY,engine,NOW)
        self.assertEqual(errors,[]);self.assertEqual(new['news']['items'][0]['titleZh'],'施罗德在2026年出场')
        self.assertEqual(new['news']['items'][1],old['news']['items'][1]);self.assertEqual(new['fixtures'],old['fixtures'])
        self.assertNotIn('titleZh',old['news']['items'][0])
        no_work=Model(error=AssertionError('model should not load'))
        again,errors=t.translate_feed(new,GLOSSARY,no_work,NOW)
        self.assertEqual(again,new);self.assertEqual(no_work.calls,0)
    def test_merge_invalidates_changed_machine_but_retains_editorial(self):
        old,_=t.translate_feed(feed(story()),GLOSSARY,Model(['ZXQA在2026年出场']),NOW)
        row=old['news']['items'][0]
        same=u.merge_news([row],[story()])[0]
        self.assertEqual(same['translation'],row['translation'])
        changed=u.merge_news([row],[story('Schröder juega en 2027')])[0]
        self.assertNotIn('titleZh',changed)
        manual=u.merge_news([story(titleZh='人工标题',summaryZh='摘要')],[story('New headline')])[0]
        self.assertEqual(manual['titleZh'],'人工标题');self.assertEqual(manual['summaryZh'],'摘要')
    def test_glossary_revision_retranslates_machine_only(self):
        old,_=t.translate_feed(feed(story()),GLOSSARY,Model(['ZXQA在2026年出场']),NOW)
        changed=copy.deepcopy(GLOSSARY);changed['entries'][11]['zh']='施罗德（新译写）'
        new,errors=t.translate_feed(old,changed,Model(['ZXQA在2026年出场']),NOW)
        self.assertEqual(errors,[]);self.assertIn('新译写',new['news']['items'][0]['titleZh'])
    def test_missing_marker_or_changed_numbers_never_publish(self):
        for output in ['某人在2026年出场','ZXQA在2027年出场','ZXQA ZXQA在2026年出场']:
            new,errors=t.translate_feed(feed(story()),GLOSSARY,Model([output]),NOW)
            self.assertTrue(errors);self.assertNotIn('titleZh',new['news']['items'][0])
            self.assertEqual(new['news']['checkedAt'],'old')
    def test_network_or_model_failure_keeps_news_available(self):
        old=feed(story(),story('Manual',titleZh='人工中文'))
        new,errors=t.translate_feed(old,GLOSSARY,Model(error=RuntimeError('network unavailable')),NOW)
        self.assertTrue(errors);self.assertEqual(new['news']['items'][0]['title'],old['news']['items'][0]['title'])
        self.assertEqual(new['news']['items'][1],old['news']['items'][1]);self.assertEqual(new['fixtures'],old['fixtures'])
    def test_partial_success_survives_another_title_failure(self):
        new,errors=t.translate_feed(feed(story(),story('Unprotected 2026')),GLOSSARY,Model(['ZXQA在2026年出场','2027年新闻']),NOW)
        self.assertEqual(len(errors),1);self.assertIn('titleZh',new['news']['items'][0]);self.assertNotIn('titleZh',new['news']['items'][1])
    def test_football_terms_do_not_change_match_or_award_facts(self):
        self.assertEqual(t.football_title('El Real Madrid empata en Múnich',GLOSSARY),'皇马在慕尼黑战平')
        self.assertEqual(t.football_title('Convocatoria del Real Madrid contra el Bayern de Múnich',GLOSSARY),'皇马对阵拜仁慕尼黑的比赛大名单')
        self.assertEqual(t.football_title('Schröder opta al premio a la mejor jugadora joven del Balón de Oro 2026',GLOSSARY),'施罗德角逐2026年金球奖最佳年轻女足球员奖')
        self.assertIsNone(t.football_title('Other headline',GLOSSARY))
    def test_rule_only_run_works_without_model_dependencies(self):
        engine=Model(error=AssertionError('no model needed'))
        result,errors=t.translate_feed(feed(story('El Real Madrid empata en Múnich')),GLOSSARY,engine,NOW)
        self.assertEqual(errors,[]);self.assertEqual(engine.calls,0)
        self.assertEqual(result['news']['items'][0]['titleZh'],'皇马在慕尼黑战平')
    def test_glossary_visible_sources_and_escaping(self):
        output=b.glossary_html(GLOSSARY)
        self.assertIn('shop.realmadrid.com/zh-cn/index.html',output)
        self.assertIn('施罗德',output);self.assertIn('本站统一用语',output)
        g=copy.deepcopy(GLOSSARY);g['entries'][0]['zh']='<script>'
        self.assertIn('&lt;script&gt;',b.glossary_html(g))
if __name__=='__main__':unittest.main()
