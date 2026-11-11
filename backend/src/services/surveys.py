from sqlalchemy import select,func
from fastapi import HTTPException
from src.models import Survey,Transect
from src.utils.serialize import row
from .audit import record
def list_surveys(db):return [dict(row(s),transect_count=db.scalar(select(func.count()).select_from(Transect).where(Transect.survey_id==s.id))) for s in db.scalars(select(Survey).order_by(Survey.id))]
def create_survey(db,data,user):
 if db.scalar(select(Survey).where(Survey.name==data.name)):raise HTTPException(409,'调查期名称已存在')
 obj=Survey(**data.model_dump());db.add(obj);db.commit();record(db,user.email,'survey.create',{'survey_id':obj.id});return row(obj)
