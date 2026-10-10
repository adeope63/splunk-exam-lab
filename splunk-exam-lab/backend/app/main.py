from __future__ import annotations
import csv, io, json, os, sqlite3, tempfile, time, uuid, asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select, delete, text
from sqlalchemy.orm import Session
from .db import get_db, engine, DB_PATH, SessionLocal
from .models import Domain, Objective, Question, Exam, ExamItem, Revision, Setting, ChallengeAttempt
from .schemas import QuestionInput, StartExam, AnswerInput, RevisionInput, SettingsInput, fingerprint
from .engine import create_exam, serialize_exam, submit, expire, settings, score_selection
from .seed import initialize
@asynccontextmanager
async def lifespan(app):
    initialize()
    def expire_sessions():
        with SessionLocal() as db:
            for exam in db.scalars(select(Exam).where(Exam.status=='active', Exam.deadline!=None, Exam.deadline<=time.time())):
                expire(db,exam)
    async def sweep():
        while True:
            await asyncio.sleep(1)
            await asyncio.to_thread(expire_sessions)
    task=asyncio.create_task(sweep())
    try: yield
    finally:
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
app=FastAPI(title='Splunk Exam Lab',version='1.0.0',lifespan=lifespan)
LOCAL_ORIGINS=['http://127.0.0.1:5173','http://localhost:5173']
if os.environ.get('SPLUNK_LAB_TEST_ORIGIN'): LOCAL_ORIGINS.append(os.environ['SPLUNK_LAB_TEST_ORIGIN'])
app.add_middleware(CORSMiddleware,allow_origins=LOCAL_ORIGINS,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Content-Type'])
@app.middleware('http')
async def local_origin_guard(request: Request, call_next):
    origin=request.headers.get('origin')
    if origin and origin not in set(LOCAL_ORIGINS+['http://127.0.0.1:8000','http://localhost:8000']):
        return Response('Untrusted origin',status_code=403)
    return await call_next(request)
@app.get('/api/health')
def health(): return {'status':'ok','storage':'local SQLite'}
def get_exam(db, id):
    exam=db.get(Exam,id)
    if not exam: raise HTTPException(404,'Exam not found')
    return exam
def validate_question(db,data):
    objective=db.get(Objective,data.objective_id)
    if not objective or objective.domain_id!=data.domain_id: raise HTTPException(422,'Unknown official domain/objective mapping')
    return data.model_dump()
@app.get('/api/blueprint')
def blueprint(db: Session=Depends(get_db)):
    return [{'id':d.id,'name':d.name,'weight':d.weight,'objectives':[{'id':o.id,'name':o.name} for o in db.scalars(select(Objective).where(Objective.domain_id==d.id))]} for d in db.scalars(select(Domain).order_by(Domain.id))]
@app.get('/api/questions')
def questions(search: str='',domain: int=0,objective: str='',difficulty: str='all',revision: str='',db: Session=Depends(get_db)):
    rows=list(db.scalars(select(Question).where(Question.active==True)))
    rev={r.question_id:r for r in db.scalars(select(Revision))}
    history=list(db.scalars(select(ExamItem).join(Exam).where(Exam.status=='submitted')))
    mistakes=Counter(i.question_id for i in history if not i.correct)
    out=[]
    for q in rows:
        data=q.content
        if search.lower() not in (data['text']+' '+q.id+' '+data['explanation']).lower(): continue
        if domain and data['domain_id']!=domain: continue
        if objective and q.objective_id!=objective: continue
        if difficulty!='all' and data['difficulty']!=difficulty: continue
        r=rev.get(q.id)
        if revision=='bookmarks' and not (r and r.bookmarked): continue
        if revision=='wrong' and not mistakes[q.id]: continue
        out.append({**data,'bookmarked':r.bookmarked if r else False,'note':r.note if r else '', 'mistakes':mistakes[q.id]})
    return out
@app.post('/api/questions',status_code=201)
def add_question(data: QuestionInput,db: Session=Depends(get_db)):
    value=validate_question(db,data); fp=fingerprint(data.text)
    if db.get(Question,data.id) or db.scalar(select(Question).where(Question.fingerprint==fp)): raise HTTPException(409,'Duplicate ID or question content')
    db.add(Question(id=data.id,objective_id=data.objective_id,content=value,fingerprint=fp)); db.commit()
    return value
@app.put('/api/questions/{id}')
def edit_question(id: str,data: QuestionInput,db: Session=Depends(get_db)):
    q=db.get(Question,id)
    if not q or not q.active: raise HTTPException(404,'Question not found')
    if id!=data.id: raise HTTPException(422,'Question ID cannot change')
    value=validate_question(db,data); fp=fingerprint(data.text)
    if db.scalar(select(Question).where(Question.fingerprint==fp,Question.id!=id)): raise HTTPException(409,'Duplicate question content')
    q.objective_id=data.objective_id; q.content=value; q.fingerprint=fp; db.commit()
    return value
@app.delete('/api/questions/{id}')
def remove_question(id: str,db: Session=Depends(get_db)):
    q=db.get(Question,id)
    if not q: raise HTTPException(404,'Question not found')
    q.active=False; db.commit(); return {'deleted':True,'historical_snapshots_preserved':True}
@app.get('/api/export')
def export_questions(format: str='json',db: Session=Depends(get_db)):
    rows=[q.content for q in db.scalars(select(Question).where(Question.active==True))]
    if format=='json': return Response(json.dumps(rows,indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename=questions.json'})
    if format!='csv': raise HTTPException(422,'Choose json or csv')
    stream=io.StringIO(); writer=csv.DictWriter(stream,fieldnames=list(QuestionInput.model_fields)); writer.writeheader()
    for row in rows: writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=questions.csv'})
@app.post('/api/import')
async def import_questions(file: UploadFile=File(...),db: Session=Depends(get_db)):
    raw=await file.read(5*1024*1024+1)
    if len(raw)>5*1024*1024: raise HTTPException(413,'Import exceeds 5 MB')
    try:
        text=raw.decode('utf-8-sig')
        if (file.filename or '').lower().endswith('.csv'):
            rows=list(csv.DictReader(io.StringIO(text)))
            for row in rows:
                for key in ['options','correct','commands']: row[key]=json.loads(row[key])
        else: rows=json.loads(text)
        if not isinstance(rows,list) or len(rows)>2000: raise ValueError('Import must be an array of at most 2000 questions')
        checked=[QuestionInput.model_validate(row) for row in rows]
    except Exception as e: raise HTTPException(422,f'Invalid import: {e}')
    ids=set(); fps=set(); values=[]
    for q in checked:
        v=validate_question(db,q); fp=fingerprint(q.text)
        if q.id in ids or fp in fps or db.get(Question,q.id) or db.scalar(select(Question).where(Question.fingerprint==fp)):
            raise HTTPException(409,f'Duplicate ID or content: {q.id}. Import is atomic; nothing was added.')
        ids.add(q.id); fps.add(fp); values.append((q,v,fp))
    for q,v,fp in values: db.add(Question(id=q.id,objective_id=q.objective_id,content=v,fingerprint=fp))
    db.commit(); return {'imported':len(values)}
@app.post('/api/exams',status_code=201)
def start(data: StartExam,db: Session=Depends(get_db)): return serialize_exam(db,create_exam(db,data))
@app.get('/api/exams')
def exam_list(db: Session=Depends(get_db)):
    exams=list(db.scalars(select(Exam).order_by(Exam.started_at.desc())))
    for e in exams: expire(db,e)
    return [{'id':e.id,'mode':e.mode,'started_at':e.started_at,'status':e.status,'score':e.score,'deadline':e.deadline,'count':len(list(db.scalars(select(ExamItem.id).where(ExamItem.exam_id==e.id))))} for e in exams]
@app.get('/api/exams/{id}')
def exam_detail(id: str,db: Session=Depends(get_db)): return serialize_exam(db,get_exam(db,id))
@app.put('/api/exams/{id}/answers/{position}')
def save_answer(id: str,position: int,data: AnswerInput,db: Session=Depends(get_db)):
    db.execute(text('BEGIN IMMEDIATE'))
    exam=get_exam(db,id); expire(db,exam)
    if exam.status!='active': raise HTTPException(409,'Exam already submitted')
    item=db.scalar(select(ExamItem).where(ExamItem.exam_id==id,ExamItem.position==position))
    if not item: raise HTTPException(404,'Question not found')
    allowed={o['id'] for o in item.snapshot['options']}
    if len(data.selected)!=len(set(data.selected)) or not set(data.selected)<=allowed or (item.snapshot['type']=='single' and len(data.selected)>1): raise HTTPException(422,'Invalid answer selection')
    if item.checked and data.selected!=item.selected: raise HTTPException(409,'Checked practice answers are locked')
    item.selected=data.selected
    if data.flagged is not None: item.flagged=data.flagged
    if data.current_index is not None:
        count=db.query(ExamItem).filter_by(exam_id=id).count()
        if not 0<=data.current_index<count: raise HTTPException(422,'Invalid navigation position')
        exam.current_index=data.current_index
    db.commit(); return {'saved':True}
@app.post('/api/exams/{id}/check/{position}')
def check_answer(id: str,position: int,db: Session=Depends(get_db)):
    db.execute(text('BEGIN IMMEDIATE'))
    exam=get_exam(db,id); expire(db,exam)
    if exam.status!='active' or exam.mode=='mock' or exam.feedback!='immediate': raise HTTPException(409,'Feedback available after submission')
    item=db.scalar(select(ExamItem).where(ExamItem.exam_id==id,ExamItem.position==position))
    if not item: raise HTTPException(404,'Question not found')
    if not item.selected: raise HTTPException(422,'Select an answer first')
    item.checked=True; item.correct=score_selection(item.snapshot,item.selected); db.commit()
    return serialize_exam(db,exam)
@app.post('/api/exams/{id}/submit')
def submit_exam(id: str,db: Session=Depends(get_db)):
    exam=get_exam(db,id); submit(db,exam); return serialize_exam(db,exam)
@app.post('/api/exams/{id}/retake',status_code=201)
def retake(id: str,db: Session=Depends(get_db)):
    old=get_exam(db,id)
    if old.status!='submitted': raise HTTPException(409,'Submit the exam first')
    items=[i for i in db.scalars(select(ExamItem).where(ExamItem.exam_id==id)) if not i.correct]
    if not items: raise HTTPException(409,'No incorrect answers to retake')
    e=Exam(id=str(uuid.uuid4()),mode='wrong',started_at=time.time(),feedback='immediate')
    db.add(e);db.flush()
    for pos,i in enumerate(items): db.add(ExamItem(exam_id=e.id,position=pos,question_id=i.question_id,snapshot=i.snapshot,selected=[]))
    db.commit(); return serialize_exam(db,e)
@app.put('/api/revision/{id}')
def revision(id: str,data: RevisionInput,db: Session=Depends(get_db)):
    if not db.get(Question,id) and not db.scalar(select(ExamItem).where(ExamItem.question_id==id)): raise HTTPException(404,'Question not found')
    r=db.get(Revision,id)
    if not r: r=Revision(question_id=id,bookmarked=False,note='');db.add(r)
    if data.bookmarked is not None: r.bookmarked=data.bookmarked
    if data.note is not None: r.note=data.note
    db.commit();return {'bookmarked':r.bookmarked,'note':r.note}
@app.get('/api/revision/{id}')
def get_revision(id: str,db: Session=Depends(get_db)):
    r=db.get(Revision,id);return {'bookmarked':r.bookmarked if r else False,'note':r.note if r else ''}
@app.get('/api/settings')
def get_settings(db: Session=Depends(get_db)): return settings(db)
@app.put('/api/settings')
def set_settings(data: SettingsInput,db: Session=Depends(get_db)):
    for k,v in data.model_dump().items():
        s=db.get(Setting,k)
        if s: s.value=v
        else: db.add(Setting(key=k,value=v))
    db.commit();return settings(db)
@app.get('/api/analytics')
def analytics(db: Session=Depends(get_db)):
    exams=list(db.scalars(select(Exam)))
    for e in exams: expire(db,e)
    completed=[e for e in exams if e.status=='submitted']
    items=list(db.scalars(select(ExamItem).join(Exam).where(Exam.status=='submitted')))
    attempted=[i for i in items if i.selected]
    correct=sum(bool(i.correct) for i in attempted)
    questions=list(db.scalars(select(Question).where(Question.active==True)))
    seen={i.question_id for i in attempted}
    days={datetime.fromtimestamp(e.submitted_at,timezone.utc).date() for e in completed}
    days.update(datetime.fromtimestamp(c.created_at,timezone.utc).date() for c in db.scalars(select(ChallengeAttempt)))
    today=datetime.now(timezone.utc).date(); streak=0; day=today if today in days else today-timedelta(days=1)
    while day in days: streak+=1;day-=timedelta(days=1)
    def group_stats(key,value):
        subset=[i for i in items if i.snapshot[key]==value]
        answered=[i for i in subset if i.selected]
        bank=[q for q in questions if q.content[key]==value]
        covered=len({i.question_id for i in answered}&{q.id for q in bank})
        return {'attempts':len(answered),'correct':sum(bool(i.correct) for i in answered),'accuracy':round(100*sum(bool(i.correct) for i in answered)/len(answered),1) if answered else None,'covered':covered,'total':len(bank)}
    domains=[{'id':d.id,'name':d.name,'weight':d.weight,**group_stats('domain_id',d.id),'objectives':[{'id':o.id,'name':o.name,**group_stats('objective_id',o.id)} for o in db.scalars(select(Objective).where(Objective.domain_id==d.id))]} for d in db.scalars(select(Domain).order_by(Domain.id))]
    scores=[e.score for e in completed]
    coverage=round(100*len(seen & {q.id for q in questions})/len(questions),1) if questions else 0
    accuracy=round(100*correct/len(attempted),1) if attempted else 0
    recent=sorted(completed,key=lambda e:e.submitted_at)[-10:]
    ready=round(sum((d['accuracy'] or 0)*d['weight']/100 for d in domains),1)
    return {'attempted':len(attempted),'unique_attempted':len(seen),'exams_completed':len(completed),'average':round(sum(scores)/len(scores),1) if scores else 0,'highest':max(scores,default=0),'accuracy':accuracy,'streak':streak,'readiness':ready,'coverage':coverage,'bank_count':len(questions),'domains':domains,'trend':[{'name':f'Session {n+1}','score':e.score,'id':e.id,'date':e.submitted_at,'mode':e.mode} for n,e in enumerate(recent)],'recent':[{'id':e.id,'score':e.score,'mode':e.mode,'date':e.submitted_at} for e in reversed(recent[-5:])],'wrong_count':len({i.question_id for i in items if not i.correct})}
@app.get('/api/backup')
def backup():
    with sqlite3.connect(DB_PATH) as src, sqlite3.connect(':memory:') as dest:
        src.backup(dest)
        # serialize() is not available on Python 3.9; use a temporary on-disk destination.
        with tempfile.NamedTemporaryFile(suffix='.sqlite3',delete=False) as f: name=f.name
        try:
            with sqlite3.connect(name) as out: dest.backup(out)
            raw=Path(name).read_bytes()
        finally: os.unlink(name)
    return Response(raw,media_type='application/octet-stream',headers={'Content-Disposition':'attachment; filename=splunk-exam-lab.sqlite3'})
@app.post('/api/restore')
async def restore(file: UploadFile=File(...)):
    raw=await file.read(50*1024*1024+1)
    if len(raw)>50*1024*1024 or not raw.startswith(b'SQLite format 3\x00'): raise HTTPException(422,'Expected a SQLite backup under 50 MB')
    with tempfile.NamedTemporaryFile(suffix='.sqlite3',delete=False) as f: f.write(raw); name=f.name
    try:
        with sqlite3.connect(name) as src:
            if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Integrity check failed')
            required={'domains','objectives','questions','exams','exam_items','revision','settings','challenge_attempts','alembic_version'}
            tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not required<=tables: raise ValueError('Not an Exam Lab backup')
            if src.execute('SELECT version_num FROM alembic_version').fetchone()!=('0001',): raise ValueError('Unsupported schema version')
            if src.execute('SELECT count(*) FROM objectives').fetchone()[0]!=32: raise ValueError('Invalid blueprint')
            if src.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Invalid relationships')
            blueprint=json.loads((Path(__file__).resolve().parents[2]/'references'/'blueprint.json').read_text())
            expected_domains={(d['id'],d['name'],d['weight']) for d in blueprint}
            expected_objectives={(o['id'],d['id'],o['name']) for d in blueprint for o in d['objectives']}
            if set(src.execute('SELECT id,name,weight FROM domains'))!=expected_domains or set(src.execute('SELECT id,domain_id,name FROM objectives'))!=expected_objectives: raise ValueError('Backup does not match the official blueprint')
            if src.execute("SELECT name FROM sqlite_master WHERE type IN ('trigger','view')").fetchall(): raise ValueError('Unexpected schema objects')
            with sqlite3.connect(DB_PATH) as current:
                for table in sorted(required):
                    if src.execute(f'PRAGMA table_info({table})').fetchall()!=current.execute(f'PRAGMA table_info({table})').fetchall(): raise ValueError(f'Invalid table schema: {table}')
            for id,objective,content,fp in src.execute('SELECT id,objective_id,content,fingerprint FROM questions'):
                q=QuestionInput.model_validate(json.loads(content))
                if q.id!=id or q.objective_id!=objective or fingerprint(q.text)!=fp: raise ValueError('Invalid question mapping or fingerprint')
            for snapshot,selected in src.execute('SELECT snapshot,selected FROM exam_items'):
                q=QuestionInput.model_validate(json.loads(snapshot));selected=json.loads(selected)
                if q.objective_id not in {o[0] for o in expected_objectives} or not set(selected)<={o.id for o in q.options}: raise ValueError('Invalid historical snapshot')
            engine.dispose()
            with sqlite3.connect(DB_PATH) as dest: src.backup(dest)
        engine.dispose()
    except Exception as e: raise HTTPException(422,f'Invalid backup: {e}')
    finally: os.unlink(name)
    return {'restored':True}
@app.post('/api/reset')
def reset(data: dict,db: Session=Depends(get_db)):
    if data.get('confirmation')!='RESET': raise HTTPException(422,'Type RESET to confirm')
    for model in [ExamItem,Exam,ChallengeAttempt,Revision]: db.execute(delete(model))
    db.commit();return {'reset':True}
from .challenges import CHALLENGES, validate_challenge
@app.get('/api/challenges')
def challenges(db: Session=Depends(get_db)):
    attempts=list(db.scalars(select(ChallengeAttempt)))
    return [{k:v for k,v in c.items() if k not in ['answers','explanation']} | {'attempts':sum(a.challenge_id==c['id'] for a in attempts),'solved':any(a.challenge_id==c['id'] and a.correct for a in attempts)} for c in CHALLENGES]
@app.post('/api/challenges/{id}')
def challenge(id: str,data: dict,db: Session=Depends(get_db)):
    c=next((c for c in CHALLENGES if c['id']==id),None)
    if not c: raise HTTPException(404,'Challenge not found')
    answer=str(data.get('answer',''))[:10000]; correct=validate_challenge(c,answer)
    db.add(ChallengeAttempt(challenge_id=id,answer=answer,correct=correct,created_at=time.time()));db.commit()
    return {'correct':correct,'explanation':c['explanation'],'answers':c['answers']}
