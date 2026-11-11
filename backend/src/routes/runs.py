from fastapi import APIRouter,Depends,Response
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.schemas.run import DiversityInput
from src.services import runs
from src.utils.serialize import row
router=APIRouter()
@router.get('/runs')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return runs.list_runs(db)
@router.get('/runs/{id}')
def detail(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return row(runs.get_run(db,id))
@router.post('/runs',status_code=201)
def create(data:DiversityInput,response:Response,db:Session=Depends(get_db),user=Depends(writers)):
 payload,deduped=runs.create_run(db,data,user)
 if deduped:
  response.status_code=200;response.headers['Idempotency-Key']=payload['input_fingerprint'];response.headers['X-Deduplicated']='true'
 return payload
@router.post('/runs/{id}/retry')
def retry(id:int,response:Response,db:Session=Depends(get_db),user=Depends(writers)):
 payload,queued=runs.retry_run(db,id,user)
 if not queued:response.headers['X-No-Op']='true'
 return payload
