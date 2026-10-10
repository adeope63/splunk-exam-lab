from __future__ import annotations
import math, random, time, uuid
from collections import Counter
from fastapi import HTTPException
from sqlalchemy import select, text
from .models import Domain, Question, Exam, ExamItem, Setting
DEFAULTS={'duration':57,'count':20,'target':80,'theme':'dark','randomize':True,'feedback':'immediate'}
def settings(db):
    return {**DEFAULTS,**{s.key:s.value for s in db.scalars(select(Setting))}}
def allocation(n, weights):
    raw={i:n*w/sum(weights.values()) for i,w in weights.items()}
    out={i:math.floor(v) for i,v in raw.items()}
    for i in sorted(raw,key=lambda i:(-(raw[i]-out[i]),i))[:n-sum(out.values())]: out[i]+=1
    return out
def score_selection(question, selected):
    return set(selected)==set(question['correct'])
def submit(db, exam):
    connection=db.connection().connection.driver_connection
    if not connection.in_transaction: db.execute(text('BEGIN IMMEDIATE'))
    db.refresh(exam)
    if exam.status=='submitted':
        db.commit()
        return
    items=list(db.scalars(select(ExamItem).where(ExamItem.exam_id==exam.id)))
    for item in items: item.correct=score_selection(item.snapshot,item.selected)
    exam.score=round(100*sum(i.correct for i in items)/len(items),2)
    exam.status='submitted'
    exam.submitted_at=min(time.time(),exam.deadline) if exam.deadline else time.time()
    db.commit()
def expire(db, exam):
    if exam.status=='active' and exam.deadline and time.time()>=exam.deadline: submit(db,exam)
def create_exam(db, request):
    cfg=settings(db)
    questions=list(db.scalars(select(Question).where(Question.active==True)))
    questions=[q for q in questions if q.content['review_status']=='verified' and q.content.get('objective_alignment')!='supplemental']
    prior=list(db.scalars(select(ExamItem).join(Exam).where(Exam.status=='submitted')))
    if request.mode=='wrong':
        wrong={i.question_id for i in prior if not i.correct}
        questions=[q for q in questions if q.id in wrong]
    if request.mode!='mock':
        questions=[q for q in questions if (not request.domains or q.content['domain_id'] in request.domains) and (not request.objectives or q.objective_id in request.objectives) and (request.difficulty=='all' or q.content['difficulty']==request.difficulty)]
        if request.unanswered:
            seen={i.question_id for i in prior if i.selected}
            questions=[q for q in questions if q.id not in seen]
    rng=random.SystemRandom()
    if cfg['randomize']: rng.shuffle(questions)
    if request.weak and request.mode!='mock':
        totals=Counter(i.snapshot['domain_id'] for i in prior)
        correct=Counter(i.snapshot['domain_id'] for i in prior if i.correct)
        questions.sort(key=lambda q:correct[q.content['domain_id']]/totals[q.content['domain_id']] if totals[q.content['domain_id']] else -1)
    if request.mode=='mock':
        weights={d.id:d.weight for d in db.scalars(select(Domain))}
        counts=allocation(65,weights)
        chosen=[]
        for domain,count in counts.items():
            pool=[q for q in questions if q.content['domain_id']==domain]
            if len(pool)<count: raise HTTPException(409,f'Domain {domain} needs {count} verified questions; has {len(pool)}')
            chosen+=pool[:count]
    else:
        if len(questions)<request.count: raise HTTPException(409,f'Only {len(questions)} matching verified questions are available. Choose a smaller count.')
        chosen=questions[:request.count]
    if cfg['randomize']: rng.shuffle(chosen)
    now=time.time()
    minutes=cfg['duration'] if request.mode=='mock' else (request.duration or cfg['duration'])
    exam=Exam(id=str(uuid.uuid4()),mode=request.mode,started_at=now,deadline=now+minutes*60 if request.mode=='mock' or request.timed else None,feedback='end' if request.mode=='mock' else request.feedback)
    db.add(exam); db.flush()
    for pos,q in enumerate(chosen):
        snapshot={**q.content,'options':[dict(o) for o in q.content['options']]}
        if cfg['randomize']: rng.shuffle(snapshot['options'])
        db.add(ExamItem(exam_id=exam.id,position=pos,question_id=q.id,snapshot=snapshot,selected=[]))
    db.commit()
    return exam
def serialize_exam(db, exam):
    expire(db,exam)
    items=list(db.scalars(select(ExamItem).where(ExamItem.exam_id==exam.id).order_by(ExamItem.position)))
    output=[]
    for item in items:
        reveal=exam.status=='submitted' or (exam.feedback=='immediate' and item.checked)
        q=dict(item.snapshot)
        if not reveal:
            q.pop('correct'); q.pop('explanation'); q.pop('reference')
            q['options']=[{'id':o['id'],'text':o['text']} for o in q['options']]
        output.append({'position':item.position,'question':q,'selected':item.selected,'flagged':item.flagged,'checked':item.checked,'correct':item.correct if reveal else None})
    return {'id':exam.id,'mode':exam.mode,'started_at':exam.started_at,'deadline':exam.deadline,'submitted_at':exam.submitted_at,'status':exam.status,'feedback':exam.feedback,'score':exam.score,'current_index':exam.current_index,'items':output,'server_time':time.time()}
