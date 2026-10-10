"""One-time, conservative upgrade of the bundled question content."""
import json
from sqlalchemy import select
from .models import Question,Setting
from .schemas import QuestionInput,fingerprint

MARKER='bank_style_review_2026_10_v1'

def apply_style_review(db,bank_path):
    if db.get(Setting,MARKER):
        return
    reviewed={q['id']:QuestionInput.model_validate(q) for q in json.loads((bank_path/'questions.json').read_text())}
    originals=[]
    for filename in ('original-bank-before-style-review.json','playlist-before-style-review.json'):
        originals.extend(json.loads((bank_path/'review'/filename).read_text()))
    report={'updated':0,'already_current':0,'preserved_personal_edits':[],'preserved_inactive':[],'conflicts':[]}
    for raw in originals:
        prior=QuestionInput.model_validate(raw)
        row=db.get(Question,prior.id)
        if row is None:
            continue
        if not row.active:
            report['preserved_inactive'].append(row.id)
            continue
        current=QuestionInput.model_validate(row.content)
        replacement=reviewed[row.id]
        if current.model_dump()==replacement.model_dump():
            report['already_current']+=1
            continue
        if current.model_dump()!=prior.model_dump():
            report['preserved_personal_edits'].append(row.id)
            continue
        fp=fingerprint(replacement.text)
        if db.scalar(select(Question).where(Question.fingerprint==fp,Question.id!=row.id)):
            report['conflicts'].append(row.id)
            continue
        row.content=replacement.model_dump()
        row.objective_id=replacement.objective_id
        row.fingerprint=fp
        report['updated']+=1
    # ExamItem.snapshot and Revision are deliberately outside this migration.
    db.add(Setting(key=MARKER,value=report))
