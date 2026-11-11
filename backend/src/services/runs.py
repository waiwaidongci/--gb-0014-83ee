from sqlalchemy import select
from fastapi import HTTPException
from src.models import DiversityRun,Survey,Transect
from src.utils.serialize import row
from src.constants.enums import RunStatus
from .audit import record
def list_runs(db):return [row(r) for r in db.scalars(select(DiversityRun).order_by(DiversityRun.id.desc()))]
def get_run(db,id):
 obj=db.get(DiversityRun,id)
 if not obj:raise HTTPException(404,'研究不存在')
 return obj
def create_run(db,data,user):
 if not db.get(Survey,data.survey_id):raise HTTPException(404,'调查期不存在')
 valid=set(db.scalars(select(Transect.id).where(Transect.survey_id==data.survey_id)))
 if not set(data.transect_ids)<=valid:raise HTTPException(422,'所选样线必须来自同一调查期')
 obj=DiversityRun(survey_id=data.survey_id,name=data.name,config=data.model_dump(exclude={'name','survey_id'}),creator_id=user.id);db.add(obj);db.commit()
 from src.worker import analyze_run
 try:analyze_run.delay(obj.id)
 except Exception:obj.status=RunStatus.FAILED;obj.error='队列不可用';db.commit();raise HTTPException(503,obj.error)
 record(db,user.email,'diversity.queued',{'run_id':obj.id});return row(obj)
