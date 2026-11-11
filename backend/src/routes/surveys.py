from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.schemas.survey import SurveyInput
from src.services import surveys
from src.constants.species import SPECIES
router=APIRouter()
@router.get('/surveys')
def index(db:Session=Depends(get_db),user=Depends(current_user)):return surveys.list_surveys(db)
@router.post('/surveys',status_code=201)
def create(data:SurveyInput,db:Session=Depends(get_db),user=Depends(writers)):return surveys.create_survey(db,data,user)
@router.get('/species')
def species(user=Depends(current_user)):return SPECIES
