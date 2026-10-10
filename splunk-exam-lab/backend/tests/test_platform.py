import copy,json,time
from collections import Counter
from app.db import SessionLocal
from app.models import Exam,ExamItem
from app.engine import allocation,score_selection
from app.challenges import CHALLENGES,validate_challenge
from sqlalchemy import select

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
 assert len(qs)==300 and len({q['text'] for q in qs})==300
 assert Counter(q['domain_id'] for q in qs)=={1:15,2:30,3:45,4:30,5:30,6:30,7:30,8:30,9:30,10:30}
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
 save(client,e,0,a[0]);save(client,e,1,a[1]);save(client,e,2,['D'])
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
 assert len(client.get('/api/questions').json())==300
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
 e=start(client,count=300);indices=[n for n,i in enumerate(e['items']) if i['question']['type']=='multiple'];a=keys(e)
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
 q=client.get('/api/questions').json()[0];q['review_status']='needs_review';client.put('/api/questions/'+q['id'],json=q)
 assert client.post('/api/exams',json={'mode':'quick','count':300}).status_code==409

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
