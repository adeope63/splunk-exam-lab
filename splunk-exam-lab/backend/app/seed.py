from __future__ import annotations
import json
from pathlib import Path
from alembic.config import Config
from alembic import command
from .db import ROOT,SessionLocal
from .models import Domain,Objective,Question,Setting
from .schemas import QuestionInput,fingerprint
from .engine import DEFAULTS
def initialize():
    cfg=Config(str(ROOT/'alembic.ini'))
    cfg.set_main_option('script_location',str(ROOT/'migrations'))
    command.upgrade(cfg,'head')
    with SessionLocal() as db:
        blueprint=json.loads((ROOT.parent/'references'/'blueprint.json').read_text())
        for d in blueprint:
            if not db.get(Domain,d['id']): db.add(Domain(id=d['id'],name=d['name'],weight=d['weight']))
        db.flush()
        for d in blueprint:
            for o in d['objectives']:
                if not db.get(Objective,o['id']): db.add(Objective(id=o['id'],domain_id=d['id'],name=o['name']))
        db.flush()
        # Seed once. A user's deletion or edits must survive restarts.
        if not db.get(Setting,'bank_seeded'):
            for raw in json.loads((ROOT.parent/'question_bank'/'questions.json').read_text()):
                q=QuestionInput.model_validate(raw)
                if not db.get(Objective,q.objective_id): raise ValueError(f'Unknown objective: {q.objective_id}')
                db.add(Question(id=q.id,objective_id=q.objective_id,content=q.model_dump(),fingerprint=fingerprint(q.text)))
            db.add(Setting(key='bank_seeded',value=True))
        for k,v in DEFAULTS.items():
            if not db.get(Setting,k): db.add(Setting(key=k,value=v))
        db.commit()
if __name__=='__main__': initialize()
