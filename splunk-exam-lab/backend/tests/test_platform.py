import copy,json,time
from collections import Counter
from pathlib import Path
from app.db import SessionLocal
from app.models import Exam,ExamItem
from app.engine import allocation,score_selection
from app.challenges import CHALLENGES,validate_challenge
from sqlalchemy import select

BUNDLED=json.loads((Path(__file__).resolve().parents[2]/'question_bank/questions.json').read_text())

def start(c,**kwargs):
 r=c.post('/api/exams',json={'count':4,**kwargs});assert r.status_code==201,r.text;return r.json()
def keys(e):
 with SessionLocal() as db:return [i.snapshot['correct'] for i in db.scalars(select(ExamItem).where(ExamItem.exam_id==e['id']).order_by(ExamItem.position))]
def save(c,e,n,a):return c.put(f"/api/exams/{e['id']}/answers/{n}",json={'selected':a,'current_index':n})
def submit(c,e):return c.post('/api/exams/'+e['id']+'/submit').json()
def test_blueprint_bank(client):
 b=client.get('/api/blueprint').json();qs=client.get('/api/questions').json()
 assert [d['weight'] for d in b]==[5,10,15,10,10,10,10,10,10,10]
 objs={o['id'] for d in b for o in d['objectives']}
 assert len(objs)==32 and {q['objective_id'] for q in qs}==objs
 assert len(qs)==len(BUNDLED) and len({q['text'] for q in qs})==len(BUNDLED)
 assert Counter(q['domain_id'] for q in qs)==Counter(q['domain_id'] for q in BUNDLED)
def test_weighted_mock_and_concealment(client):
 w={1:5,2:10,3:15,**{i:10 for i in range(4,11)}}
 assert allocation(65,w)=={1:3,2:7,3:10,4:7,5:7,6:7,7:6,8:6,9:6,10:6}
 for n in range(1,301):assert sum(allocation(n,w).values())==n
 for _ in range(3):
  e=start(client,mode='mock',feedback='immediate');assert len(e['items'])==65 and e['feedback']=='end'
  assert Counter(i['question']['domain_id'] for i in e['items'])==allocation(65,w)
  assert len({i['question']['id'] for i in e['items']})==65
  assert e['deadline']-e['started_at']==3420
  for i in e['items']:
   assert 'correct' not in i['question'] and 'explanation' not in i['question']
   assert all('explanation' not in o for o in i['question']['options'])
  assert client.post(f"/api/exams/{e['id']}/check/0").status_code==409

def test_autosave_resume_timer(client):
 e=start(client,timed=True,duration=5);key=keys(e)[0]
 assert client.put(f"/api/exams/{e['id']}/answers/0",json={'selected':key,'flagged':True,'current_index':2}).status_code==200
 got=client.get('/api/exams/'+e['id']).json()
 assert got['items'][0]['selected']==key and got['items'][0]['flagged']
 assert got['current_index']==2 and got['deadline']==e['deadline']
 assert client.get('/api/exams').json()[0]['status']=='active'
def test_exact_multiple_scoring():
 assert score_selection({'correct':['A','B']},['B','A'])
 assert not score_selection({'correct':['A','B']},['A'])
 assert not score_selection({'correct':['A','B']},['A','B','C'])
 assert not score_selection({'correct':['A']},[])
def test_submission_analytics_history(client):
 e=start(client);a=keys(e)
 save(client,e,0,a[0]);save(client,e,1,a[1]);save(client,e,2,[next(o['id'] for o in e['items'][2]['question']['options'] if o['id'] not in a[2])])
 result=submit(client,e);assert result['score']==50 and result['status']=='submitted'
 assert all('correct' in i['question'] for i in result['items'])
 s=client.get('/api/analytics').json()
 assert s['attempted']==3 and s['exams_completed']==1 and s['accuracy']==66.7
 assert s['average']==50 and s['highest']==50 and s['unique_attempted']==3
 assert s['wrong_count']==2 and s['streak']==1 and len(s['trend'])==1
 assert sum(d['attempts'] for d in s['domains'])==3
 assert submit(client,e)['score']==50 and save(client,e,0,[]).status_code==409
 assert client.get('/api/exams').json()[0]['score']==50
 assert len(client.post('/api/exams/'+e['id']+'/retake').json()['items'])==2

def test_auto_expiry(client):
 e=start(client,timed=True)
 with SessionLocal() as db:
  obj=db.get(Exam,e['id']);obj.deadline=time.time()-1;db.commit()
 got=client.get('/api/exams/'+e['id']).json()
 assert got['status']=='submitted' and got['score']==0
 assert got['submitted_at']==got['deadline'] and save(client,e,0,['A']).status_code==409

def test_immediate_check_lock(client):
 e=start(client,feedback='immediate');a=keys(e)[0]
 assert client.post(f"/api/exams/{e['id']}/check/0").status_code==422
 save(client,e,0,a);got=client.post(f"/api/exams/{e['id']}/check/0").json()
 assert got['items'][0]['checked'] and got['items'][0]['correct']
 assert 'correct' not in got['items'][1]['question']
 assert save(client,e,0,[]).status_code==409 and save(client,e,0,a).status_code==200

def test_topic_unanswered_difficulty(client):
 e=start(client,mode='topic',objectives=['3.3'],domains=[3],difficulty='medium')
 assert all(i['question']['objective_id']=='3.3' for i in e['items'])
 for n,a in enumerate(keys(e)):save(client,e,n,a)
 submit(client,e);got=start(client,mode='topic',unanswered=True,count=2,objectives=['3.3'])
 assert not ({i['question']['id'] for i in got['items']}&{i['question']['id'] for i in e['items']})
 assert client.post('/api/exams',json={'mode':'topic','count':300,'objectives':['1.1']}).status_code==409
 assert client.post('/api/exams',json={'count':0}).status_code==422

def test_invalid_selection(client):
 e=start(client)
 assert save(client,e,0,['Z']).status_code==422
 assert save(client,e,0,['A','A']).status_code==422
 assert client.put(f"/api/exams/{e['id']}/answers/0",json={'selected':[],'current_index':999}).status_code==422
 assert client.get('/api/exams/'+e['id']).json()['items'][0]['selected']==[]

def test_historical_snapshot(client):
 e=start(client,count=1);q=client.get('/api/questions?search='+e['items'][0]['question']['id']).json()[0]
 original=q['text'];q['text']='An edited original question requiring a new evaluation of a visualization.'
 assert client.put('/api/questions/'+q['id'],json=q).status_code==200
 assert client.delete('/api/questions/'+q['id']).status_code==200
 assert submit(client,e)['items'][0]['question']['text']==original
 assert client.get('/api/questions?search='+q['id']).json()==[]
 assert len(client.post('/api/exams/'+e['id']+'/retake').json()['items'])==1

def test_question_and_import_validation(client):
 exported=client.get('/api/export').json();q=copy.deepcopy(exported[0]);q['id']='CUSTOM';q['text']='A fresh original example requiring a choice of visualization command.'
 assert client.post('/api/import',files={'file':('q.json',json.dumps([q,exported[0]]))}).status_code==409
 assert len(client.get('/api/questions').json())==len(BUNDLED)
 assert client.post('/api/import',files={'file':('q.json',json.dumps([q]))}).json()=={'imported':1}
 assert client.post('/api/questions',json=q).status_code==409
 q['id']='INVALID';q['text']='Another fresh original question with an invalid official objective.';q['objective_id']='1.99'
 assert client.post('/api/questions',json=q).status_code==422
 assert client.post('/api/import',files={'file':('q.json',json.dumps([q]))}).status_code==422
 q['objective_id']='2.1';assert client.post('/api/questions',json=q).status_code==422
 q['objective_id']='1.1';q['correct']=['Z'];assert client.post('/api/questions',json=q).status_code==422
 assert client.post('/api/import',files={'file':('q.json','{}')}).status_code==422
 csv=client.get('/api/export?format=csv');assert 'objective_id' in csv.text
 assert client.post('/api/import',files={'file':('q.csv',csv.content)}).status_code==409

def test_bookmark_notes_mistakes(client):
 e=start(client,count=1);submit(client,e);id=e['items'][0]['question']['id']
 assert len(client.get('/api/questions?revision=wrong').json())==1
 client.put('/api/revision/'+id,json={'bookmarked':True,'note':'Review correlation constraints'})
 assert client.get('/api/questions?revision=bookmarks').json()[0]['note']=='Review correlation constraints'
 assert client.get('/api/revision/'+id).json()['bookmarked']
 client.put('/api/revision/'+id,json={'bookmarked':False});assert client.get('/api/questions?revision=bookmarks').json()==[]
 wrong=start(client,mode='wrong',count=1);submit(client,wrong)
 assert client.get('/api/questions?revision=wrong').json()[0]['mistakes']==2

def test_backup_restore_reset(client):
 e=start(client,count=1);save(client,e,0,keys(e)[0]);submit(client,e)
 backup=client.get('/api/backup');assert backup.content.startswith(b'SQLite format 3')
 assert client.post('/api/reset',json={'confirmation':'NO'}).status_code==422
 client.post('/api/reset',json={'confirmation':'RESET'});assert client.get('/api/analytics').json()['attempted']==0
 r=client.post('/api/restore',files={'file':('backup.sqlite3',backup.content)});assert r.status_code==200,r.text
 assert client.get('/api/analytics').json()['attempted']==1
 assert client.get('/api/exams/'+e['id']).json()['score']==100
 assert client.post('/api/restore',files={'file':('bad.db',b'not SQLite')}).status_code==422
 assert client.get('/api/analytics').json()['attempted']==1

def test_preferences_challenges(client):
 cfg=client.get('/api/settings').json();cfg.update(duration=60,target=85,randomize=False)
 assert client.put('/api/settings',json=cfg).status_code==200
 e=start(client,mode='mock');assert e['deadline']-e['started_at']==3600
 assert len(client.get('/api/challenges').json())==12
 assert all('answers' not in c for c in client.get('/api/challenges').json())
 assert client.post('/api/challenges/stats-choice',json={'answer':'stats count by EventCode'}).json()['correct']
 assert not client.post('/api/challenges/stats-choice',json={'answer':'transaction EventCode'}).json()['correct']
 assert client.get('/api/challenges').json()[6]['attempts']==2
 assert validate_challenge(CHALLENGES[2],' where elapsed > budget ')
def test_origin_guard(client):
 assert client.post('/api/reset',headers={'origin':'https://evil.example'},json={'confirmation':'RESET'}).status_code==403
 assert client.get('/api/health',headers={'origin':'http://127.0.0.1:5173'}).status_code==200
def test_api_multiple_response_no_partial_credit(client):
 # Imported multi-answer questions remain supported even though the reviewed
 # bundled bank follows the requested four-option single-answer style.
 for n in range(3):
  q=copy.deepcopy(BUNDLED[0]);q.update(id=f'TEST-MULTI-{n}',text=f'Imported multiple-response scoring example number {n}. Select TWO answers.',type='multiple',correct=['A','B'])
  assert client.post('/api/questions',json=q).status_code==201
 with SessionLocal() as db:
  from app.models import Question
  for q in db.scalars(select(Question)):
   if not q.id.startswith('TEST-MULTI-'):q.active=False
  db.commit()
 e=start(client,count=3);indices=list(range(3));a=keys(e)
 save(client,e,indices[0],a[indices[0]])
 save(client,e,indices[1],a[indices[1]][:1])
 save(client,e,indices[2],a[indices[2]]+['C'])
 result=submit(client,e)
 assert result['items'][indices[0]]['correct']
 assert not result['items'][indices[1]]['correct'] and not result['items'][indices[2]]['correct']
 assert sum(i['correct'] for i in result['items'])==1

def test_weak_priority_and_review_exclusion(client):
 e=start(client,mode='topic',count=2,domains=[8]);submit(client,e)
 got=start(client,mode='topic',count=10,weak=True)
 # Unattempted domains are prioritized before attempted ones.
 assert all(i['question']['domain_id']!=8 for i in got['items'])
 rows=client.get('/api/questions?domain=1').json();eligible=[q for q in rows if q['review_status']=='verified' and q['objective_alignment']!='supplemental']
 q=eligible[0];q['review_status']='needs_review';client.put('/api/questions/'+q['id'],json=q)
 assert client.post('/api/exams',json={'mode':'topic','domains':[1],'count':len(eligible)}).status_code==409

def test_background_expiry_without_browser_reads(client):
 e=start(client,timed=True)
 with SessionLocal() as db:
  db.get(Exam,e['id']).deadline=time.time()+.05;db.commit()
 time.sleep(1.25)
 with SessionLocal() as db:assert db.get(Exam,e['id']).status=='submitted'

def test_valid_csv_import(client):
 import csv,io
 q=client.get('/api/export').json()[0];q['id']='CSV-ORIGINAL';q['text']='A distinct original visualization example imported through a quoted CSV cell.'
 stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(q));writer.writeheader();writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in q.items()})
 r=client.post('/api/import',files={'file':('q.csv',stream.getvalue())});assert r.status_code==200 and r.json()['imported']==1
 assert client.get('/api/questions?search=CSV-ORIGINAL').json()[0]['text']==q['text']

def test_tampered_blueprint_backup_rejected(client,tmp_path):
 import sqlite3
 backup=client.get('/api/backup').content;path=tmp_path/'tampered.sqlite3';path.write_bytes(backup)
 with sqlite3.connect(path) as db:
  db.execute('PRAGMA journal_mode=DELETE')
  db.execute("UPDATE objectives SET name='Invented objective' WHERE id='1.1'");db.commit()
 r=client.post('/api/restore',files={'file':('tampered.sqlite3',path.read_bytes())})
 assert r.status_code==422
 assert client.get('/api/blueprint').json()[0]['objectives'][0]['name']=='Use the chart command'

def test_playlist_seed_preserves_edits_deletions_and_progress(client):
 from app.seed import initialize
 from app.models import Question
 playlist=client.get('/api/questions?search=YT-SPLK-').json()
 assert len(playlist)==58
 assert sum(q['objective_alignment']=='supplemental' for q in playlist)==3
 assert all(len(q['options'])==4 and all(o['explanation'].startswith(('Correct.','Incorrect.')) for o in q['options']) for q in playlist)
 first=playlist[0];first['explanation']='Personal edited explanation that must survive initialization.'
 assert client.put('/api/questions/'+first['id'],json=first).status_code==200
 assert client.delete('/api/questions/YT-SPLK-002').status_code==200
 assert client.put('/api/revision/'+first['id'],json={'bookmarked':True,'note':'Keep my study note.'}).status_code==200
 exam=start(client,count=1)
 initialize();initialize()
 got=client.get('/api/questions?search='+first['id']).json()[0]
 assert got['explanation']==first['explanation'] and got['note']=='Keep my study note.' and got['bookmarked']
 with SessionLocal() as db:
  assert not db.get(Question,'YT-SPLK-002').active
  assert db.get(Exam,exam['id']) is not None
 assert len(client.get('/api/questions?search=YT-SPLK-').json())==57

def test_playlist_explanations_follow_answer_reveal_and_supplement_exclusion(client):
 from app.models import Question
 with SessionLocal() as db:
  for q in db.scalars(select(Question)):
   if not q.id.startswith('YT-SPLK-'):q.active=False
   elif q.content['objective_alignment']=='supplemental':q.content={**q.content,'review_status':'verified'}
  db.commit()
 e=start(client,count=55,feedback='immediate')
 assert all(i['question']['objective_alignment']!='supplemental' for i in e['items'])
 assert client.post('/api/exams',json={'count':56}).status_code==409
 assert all('explanation' not in o for i in e['items'] for o in i['question']['options'])
 a=keys(e);save(client,e,0,a[0]);revealed=client.post(f"/api/exams/{e['id']}/check/0").json()
 q=revealed['items'][0]['question']
 assert q['correct']==a[0] and all(o['explanation'] for o in q['options'])
 assert q['source_url'].startswith('https://www.youtube.com/watch?')
 result=submit(client,e)
 assert all(o['explanation'] for i in result['items'] for o in i['question']['options'])

def test_playlist_csv_metadata_round_trip(client):
 import csv,io
 from app.schemas import QuestionInput
 q=client.get('/api/questions?search=YT-SPLK-057').json()[0]
 q['id']='CSV-PLAYLIST';q['text']='CSV round-trip adaptation: '+q['text']
 fields=list(QuestionInput.model_fields)
 stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
 writer.writerow({k:json.dumps(q[k]) if isinstance(q.get(k),list) else q.get(k) for k in fields})
 assert client.post('/api/import',files={'file':('playlist.csv',stream.getvalue())}).json()=={'imported':1}
 got=client.get('/api/questions?search=CSV-PLAYLIST').json()[0]
 assert got['source_url']==q['source_url'] and got['source_question_number']==57
 assert got['options']==q['options']

def test_style_upgrade_preserves_personal_content_and_history(client):
 from app.models import Question,Setting
 from app.schemas import QuestionInput,fingerprint
 from app.bank_review import MARKER
 from app.seed import initialize
 root=Path(__file__).resolve().parents[2]/'question_bank'
 legacy=json.loads((root/'review/original-bank-before-style-review.json').read_text())+json.loads((root/'review/playlist-before-style-review.json').read_text())
 exam=start(client,count=2)
 with SessionLocal() as db:
  snapshots=[copy.deepcopy(i.snapshot) for i in db.scalars(select(ExamItem).where(ExamItem.exam_id==exam['id']).order_by(ExamItem.position))]
  db.delete(db.get(Setting,MARKER))
  for raw in legacy:
   q=QuestionInput.model_validate(raw);row=db.get(Question,q.id)
   row.content=q.model_dump();row.fingerprint=fingerprint(q.text)
  personal=db.get(Question,'SPLK-002-A');personal.content={**personal.content,'text':'My personally edited original question must remain available.'};personal.fingerprint=fingerprint(personal.content['text'])
  db.get(Question,'SPLK-003-A').active=False
  db.commit()
 assert client.put('/api/revision/SPLK-001-B',json={'bookmarked':True,'note':'Keep this note across the style upgrade.'}).status_code==200
 initialize()
 with SessionLocal() as db:
  report=db.get(Setting,MARKER).value
  assert report['updated']==320 and report['already_current']==36
  assert report['preserved_personal_edits']==['SPLK-002-A']
  assert report['preserved_inactive']==['SPLK-003-A'] and not report['conflicts']
  assert db.get(Question,'SPLK-002-A').content['text'].startswith('My personally')
  assert not db.get(Question,'SPLK-003-A').active
  assert [i.snapshot for i in db.scalars(select(ExamItem).where(ExamItem.exam_id==exam['id']).order_by(ExamItem.position))]==snapshots
  edited=db.get(Question,'SPLK-001-B');edited.content={**edited.content,'explanation':'A later personal explanation must also survive restart.'};db.commit()
 initialize()
 got=client.get('/api/questions?search=SPLK-001-B').json()[0]
 assert got['bookmarked'] and got['note']=='Keep this note across the style upgrade.'
 assert got['explanation']=='A later personal explanation must also survive restart.'

def test_reviewed_bank_keys_and_regeneration_contract():
 base=[q for q in BUNDLED if q['id'].startswith('SPLK-')]
 assert Counter(q['correct'][0] for q in base)=={'A':75,'B':75,'C':75,'D':75}
 for q in BUNDLED:
  assert q['type']=='single' and len(q['options'])==4
  assert len({o['text'] for o in q['options']})==4
  assert 'A colleague recommends:' not in q['text']
  assert 'Select TWO statements' not in q['text']
  assert all(o['explanation'].startswith('Correct. ' if o['id'] in q['correct'] else 'Incorrect. ') for o in q['options'])
