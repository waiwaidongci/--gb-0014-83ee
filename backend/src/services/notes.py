from sqlalchemy import select
from fastapi import HTTPException
from src.models import ConservationNote,DiversityRun
from src.constants.enums import NoteStatus,RunStatus
from src.utils.serialize import row
from .audit import record
def list_notes(db):return [row(x) for x in db.scalars(select(ConservationNote).order_by(ConservationNote.id.desc()))]
def create_note(db,data,user):
 run=db.get(DiversityRun,data.run_id)
 if not run or run.status!=RunStatus.SUCCEEDED:raise HTTPException(422,'请选择成功研究')
 valid={x['id'] for x in run.result['transects'] if x['status']=='eligible'}
 if len(set(data.transect_ids))!=len(data.transect_ids) or not set(data.transect_ids)<=valid:raise HTTPException(422,'建议样线须来自本研究有效群落且不重复')
 obj=ConservationNote(**data.model_dump(),creator_id=user.id);db.add(obj);db.commit();record(db,user.email,'observation.created',{'note_id':obj.id});return row(obj)
def approve_note(db,id,data,user):
 obj=db.get(ConservationNote,id)
 if not obj:raise HTTPException(404,'观察建议不存在')
 if obj.status!=NoteStatus.DRAFT:raise HTTPException(409,'仅草案可审核')
 obj.status=data.status;obj.review_note=data.review_note;db.commit();record(db,user.email,'observation.reviewed',{'note_id':id,'status':obj.status});return row(obj)
