from pydantic import BaseModel,Field,model_validator
from src.constants.species import SPECIES
class CountInput(BaseModel):
 species:str
 count:int=Field(ge=0,le=100000,strict=True)
 @model_validator(mode='after')
 def known_species(self):
  if self.species not in SPECIES:raise ValueError('未知物种编码')
  return self
class TransectInput(BaseModel):
 survey_id:int=Field(gt=0)
 reference:str=Field(min_length=1,max_length=50)
 name:str=Field(min_length=1,max_length=100)
 habitat:str=Field(min_length=1,max_length=80)
 counts:list[CountInput]=Field(min_length=1,max_length=24)
 @model_validator(mode='after')
 def unique_species(self):
  if len({c.species for c in self.counts})!=len(self.counts):raise ValueError('同样线物种不可重复；请先汇总')
  return self
