import copy
import importlib.util
import json
import unittest
from datetime import datetime,timezone
from pathlib import Path
spec=importlib.util.spec_from_file_location('update',Path(__file__).resolve().parents[1]/'scripts/update.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
NOW=datetime(2026,10,27,0,0,tzinfo=timezone.utc)
def match(**kwargs):
    data={'id':'a1','optaId':'match1','dateTime':'2026-10-28T17:45:00.000Z','status':'pre_match','isScheduled':True,'homeTeam':{'optaId':'bayern','name':'Bayern de Múnich'},'awayTeam':{'optaId':u.WOMEN_ID,'name':'Real Madrid'},'competition':{'slug':'womens-champions-league'},'venue':{'name':'Uhlsport Park'}}
    data.update(kwargs);return data
NEWS={'title':'Noticias del equipo','slug':'noticias-27-10-2026','date':'2026-10-27T00:00:00Z','tag':['realmadrid-com:noticias/futbol/primer-equipo-femenino/actualidad']}
def page(data):return '<html><script id="ng-state" type="application/json">'+json.dumps(data)+'</script></html>'
def seed():return {k:{'items':[],'checkedAt':None,'error':None,'revision':'seed'} for k in ['news','fixtures']}
class ParserTests(unittest.TestCase):
    def test_gender_and_duplicate_filter(self):
        men=match(optaId='men',awayTeam={'optaId':'menTeam','name':'Real Madrid'})
        rows=u.parse_fixtures({'matches':[match(),copy.deepcopy(match()),men]})
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['away'],'皇马')
    def test_unknown_kickoff_stays_unknown(self):
        self.assertIsNone(u.parse_fixtures([match(isScheduled=False)])[0]['kickoff'])
    def test_final_score_strings_zero_and_missing(self):
        self.assertEqual(u.parse_fixtures([match(status='finished',homeTeamScoreTotal='0',awayTeamScoreTotal='0')])[0]['score'],'0–0')
        with self.assertRaises(ValueError):u.parse_fixtures([match(status='finished')])
    def test_daylight_saving_does_not_guess(self):
        row=u.parse_fixtures([match()])[0]
        self.assertEqual(row['kickoff'],'2026-10-28T17:45:00Z')
        self.assertEqual(u.parse_time(row['kickoff']).astimezone(u.ZoneInfo('Asia/Shanghai')).strftime('%m/%d %H:%M'),'10/29 01:45')
    def test_news_date_not_guessed_from_url(self):
        n={**NEWS,'slug':'old-slug-01-01-2020'}
        self.assertEqual(u.parse_news([n])[0]['publishedDate'],'2026-10-27')
        with self.assertRaises(ValueError):u.parse_news([{**NEWS,'tag':['realmadrid-com:noticias/futbol/primer-equipo/actualidad']}])
    def test_live_scores_are_not_mislabeled_final(self):
        with self.assertRaises(ValueError):u.parse_fixtures([match(status='in_play')])
    def test_failure_keeps_success_time_and_content(self):
        old=seed();old['news']={'items':[{'url':'x','title':'原内容'}],'checkedAt':'2026-10-26T00:00:00Z','revision':'one','error':None}
        def unavailable(url):raise RuntimeError('HTTP 403')
        result,errors=u.refresh(old,'news',unavailable,NOW)
        self.assertTrue(errors);self.assertEqual(result['news']['items'],old['news']['items']);self.assertEqual(result['news']['checkedAt'],old['news']['checkedAt']);self.assertEqual(old['news']['error'],None)
    def test_partial_failure_isolated_and_recoverable(self):
        html=page({'news':NEWS,'match':match()})
        def source(url):
            if url==u.CALENDAR:raise RuntimeError('calendar unavailable')
            return html
        result,errors=u.refresh(seed(),'both',source,NOW)
        self.assertEqual(len(errors),1);self.assertEqual(len(result['news']['items']),1);self.assertIsNone(result['fixtures']['checkedAt'])
        recovered,errors=u.refresh(result,'fixtures',lambda url:html,NOW)
        self.assertEqual(errors,[]);self.assertIsNone(recovered['fixtures']['error']);self.assertEqual(len(recovered['fixtures']['items']),1)
    def test_no_change_still_records_successful_check(self):
        html=page({'news':NEWS,'match':match()});first,_=u.refresh(seed(),'both',lambda url:html,NOW)
        later=datetime(2026,10,27,1,0,tzinfo=timezone.utc);second,_=u.refresh(first,'news',lambda url:html,later)
        self.assertEqual(first['news']['revision'],second['news']['revision']);self.assertNotEqual(first['news']['checkedAt'],second['news']['checkedAt']);self.assertEqual(first['fixtures'],second['fixtures'])
    def test_old_results_survive_partial_source_lists(self):
        a=u.parse_fixtures([match(status='finished',homeTeamScoreTotal='3',awayTeamScoreTotal='2')])[0]
        b=u.parse_fixtures([match(optaId='newMatch')])[0]
        self.assertEqual(len(u.merge_fixtures([a],[b],NOW)),2)
    def test_structure_change_fails_explicitly(self):
        with self.assertRaises(ValueError):u.parse_state('<html>access denied</html>')
if __name__=='__main__':unittest.main()
