import json
from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import DiversityRun,Survey
from src.services.transects import list_transects
from src.services.analysis import analyze
from src.services.audit import record
from src.utils.serialize import row
app=Celery('ecology_rarefy',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
@app.task(name='ecology.analyze',soft_time_limit=180,time_limit=210)
def analyze_run(id):
 with SessionLocal() as db:
  run=db.get(DiversityRun,id)
  if not run or run.status=='succeeded':return
  run.status='running';db.commit()
  try:
   selected=set(run.config['transect_ids']);data=[t for t in list_transects(db,run.survey_id) if t['id'] in selected];result=analyze(row(db.get(Survey,run.survey_id)),data,run.config)
   Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True);Path(ARTIFACT_DIR,f'diversity-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False));run.result=result;run.status='succeeded';run.error=None;db.commit();record(db,'worker','diversity.succeeded',{'run_id':id,'m':result['m'],'eligible':result['eligible'],'empty':result['excluded_empty']})
  except Exception as e:
   db.rollback();run=db.get(DiversityRun,id);run.status='failed';run.error=str(e)[:1000];db.commit();record(db,'worker','diversity.failed',{'run_id':id,'error':run.error})
