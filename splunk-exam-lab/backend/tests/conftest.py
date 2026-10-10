import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
TMP=tempfile.TemporaryDirectory(prefix='splunk-lab-tests-')
os.environ['SPLUNK_LAB_DB']=str(Path(TMP.name)/'test.sqlite3')
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import engine,DB_PATH
@pytest.fixture()
def client():
    engine.dispose()
    for p in [DB_PATH,Path(str(DB_PATH)+'-wal'),Path(str(DB_PATH)+'-shm')]:
        if p.exists():p.unlink()
    with TestClient(app) as c:yield c
    engine.dispose()
