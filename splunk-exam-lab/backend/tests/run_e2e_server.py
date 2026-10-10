import os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory(prefix='splunk-lab-e2e-') as temp:
    os.environ['SPLUNK_LAB_DB']=str(Path(temp)/'e2e.sqlite3')
    os.environ['SPLUNK_LAB_TEST_ORIGIN']='http://127.0.0.1:5174'
    import uvicorn
    uvicorn.run('app.main:app',host='127.0.0.1',port=8001)
