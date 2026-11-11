from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import Transect
from src.schemas.transect import TransectInput
from src.services import transects
router=APIRouter()
@router.get('/transects')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return transects.list_transects(db)
@router.get('/surveys/{id}/transects')
def for_survey(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return transects.list_transects(db,id)
@router.get('/transects/{id}/counts')
def counts(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 if not db.get(Transect,id):raise HTTPException(404,'样线不存在')
 return transects.get_counts(db,id)
@router.post('/transects',status_code=201)
def create(data:TransectInput,db:Session=Depends(get_db),user=Depends(writers)):return transects.create_transect(db,data,user)
