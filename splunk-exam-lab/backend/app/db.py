from __future__ import annotations
import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get('SPLUNK_LAB_DB', str(ROOT / 'data' / 'exam-lab.sqlite3'))).resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False, 'timeout': 30})
@event.listens_for(engine, 'connect')
def configure(dbapi, _):
    dbapi.execute('PRAGMA foreign_keys=ON')
    dbapi.execute('PRAGMA journal_mode=WAL')
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
class Base(DeclarativeBase):
    pass
def get_db():
    with SessionLocal() as db:
        yield db
