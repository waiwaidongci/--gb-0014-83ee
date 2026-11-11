from pydantic import BaseModel,Field,model_validator
class DiversityInput(BaseModel):
 name:str=Field(min_length=1,max_length=100)
 survey_id:int=Field(gt=0)
 transect_ids:list[int]=Field(min_length=1,max_length=30)
 m:int=Field(ge=0,le=100000,strict=True)
 bootstrap:int=Field(ge=50,le=1000,strict=True)
 seed:int=Field(ge=0,le=2147483647,strict=True)
 @model_validator(mode='after')
 def unique_transects(self):
  if len(set(self.transect_ids))!=len(self.transect_ids):raise ValueError('样线不得重复')
  return self
