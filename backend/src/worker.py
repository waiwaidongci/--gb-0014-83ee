from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import DiversityRun
from src.services.analysis import analyze
from src.services.archive import get_archive,load_archive_inputs
from src.services.audit import record
from src.utils.artifacts import write_run_artifact,read_run_artifact,artifact_path
app=Celery('ecology_rarefy',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)
def _fail(db,run_id,message):
 db.rollback()
 run=db.get(DiversityRun,run_id)
 if run is not None:
  run.status='failed';run.error=message[:1000]
  archive=get_archive(db,run_id)
  if archive is not None:archive.artifact_path=None
  db.commit();record(db,'worker','diversity.failed',{'run_id':run_id,'error':run.error})
 # 失败不留结果文件：结果文件只允许与 succeeded 状态对应
 try:Path(artifact_path(ARTIFACT_DIR,run_id)).unlink()
 except FileNotFoundError:pass
@app.task(name='ecology.analyze',soft_time_limit=180,time_limit=210)
def analyze_run(id):
 with SessionLocal() as db:
  run=db.get(DiversityRun,id)
  if not run or run.status=='succeeded':return
  archive=get_archive(db,run.id)
  if not archive:
   _fail(db,id,'缺少受理归档，拒绝复算：输入快照不存在，无法保证可复现');return
  run.status='running';run.error=None;db.commit()
  try:
   survey,transects,config=load_archive_inputs(archive)
   result=analyze(survey,transects,config)
   if result.get('fingerprint')!=archive.input_fingerprint:
    raise ValueError('结果指纹与归档输入指纹不一致，拒绝发布')
   path=write_run_artifact(ARTIFACT_DIR,id,result)
   run.result=result;run.status='succeeded';run.error=None
   archive.artifact_path=path
   db.commit()
  except Exception as e:
   _fail(db,id,str(e));return
  # 提交后复核：结果文件必须与 succeeded 状态对应，否则回退为 failed，不留成功假象
  try:
   on_disk=read_run_artifact(ARTIFACT_DIR,id)
   if on_disk.get('fingerprint')!=archive.input_fingerprint:
    raise ValueError('结果文件指纹与归档不一致')
  except Exception as e:
   _fail(db,id,f'结果文件复核失败：{e}');return
  record(db,'worker','diversity.succeeded',{'run_id':id,'m':result['m'],'eligible':result['eligible'],'empty':result['excluded_empty'],'artifact':artifact_path(ARTIFACT_DIR,id)})
