from sqlalchemy import select
from fastapi import HTTPException
from src.models import DiversityRun
from src.utils.serialize import row
from src.constants.enums import RunStatus
from .audit import record
from .archive import accept_run,get_archive
def list_runs(db):return [row(r) for r in db.scalars(select(DiversityRun).order_by(DiversityRun.id.desc()))]
def get_run(db,id):
 obj=db.get(DiversityRun,id)
 if not obj:raise HTTPException(404,'研究不存在')
 return obj
def create_run(db,data,user):
 obj,deduped=accept_run(db,data,user)
 if deduped:
  record(db,user.email,'diversity.deduped',{'run_id':obj.id,'input_fingerprint':obj.input_fingerprint})
  return row(obj),True
 from src.worker import analyze_run
 try:analyze_run.delay(obj.id)
 except Exception:
  obj.status=RunStatus.FAILED;obj.error='队列不可用';db.commit()
  raise HTTPException(503,obj.error)
 record(db,user.email,'diversity.queued',{'run_id':obj.id,'input_fingerprint':obj.input_fingerprint})
 return row(obj),False
def retry_run(db,id,user):
 run=get_run(db,id)
 archive=get_archive(db,run.id)
 if not archive:raise HTTPException(409,'历史研究缺少受理归档，明确拒绝复算：输入快照不存在，无法保证可复现')
 if run.status==RunStatus.SUCCEEDED:return row(run),False
 from src.worker import analyze_run
 try:analyze_run.delay(run.id)
 except Exception:
  run.status=RunStatus.FAILED;run.error='队列不可用';db.commit()
  raise HTTPException(503,run.error)
 run.status=RunStatus.QUEUED;run.error=None;db.commit()
 record(db,user.email,'diversity.retried',{'run_id':run.id,'input_fingerprint':archive.input_fingerprint})
 return row(run),True
