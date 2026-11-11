from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers,admins
from src.controllers.export import export_note
from src.schemas.note import NoteInput,ApprovalInput
from src.services import notes
router=APIRouter()
@router.get('/notes')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return notes.list_notes(db)
@router.post('/notes',status_code=201)
def create(data:NoteInput,db:Session=Depends(get_db),user=Depends(writers)):return notes.create_note(db,data,user)
@router.patch('/notes/{id}/approval')
def approve(id:int,data:ApprovalInput,db:Session=Depends(get_db),user=Depends(admins)):return notes.approve_note(db,id,data,user)
@router.get('/notes/{id}/export')
def export(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return export_note(db,id)
