import json
from datetime import date
import numpy as np
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import *
from src.utils.security import hash_password
from src.utils.serialize import row
from src.constants.species import SPECIES
from src.services.transects import list_transects
from src.services.analysis import analyze

def seed():
 Base.metadata.create_all(engine)
 with SessionLocal() as db:
  for role,name in [('admin','顾芩 · 生态研究负责人'),('analyst','林荞 · 样线研究员'),('viewer','季苔 · 观察记录员')]:
   email=role+'@songji.demo'
   if not db.scalar(select(User).where(User.email==email)):db.add(User(email=email,name=name,role=role,password_hash=hash_password('Songji2026!')))
  db.commit();rng=np.random.default_rng(149)
  for period,(name,day) in enumerate([('春季返青调查','2026-04-14'),('盛夏生境调查','2026-07-14'),('秋季样线调查','2026-10-14')]):
   survey=db.scalar(select(Survey).where(Survey.name==name))
   if not survey:survey=Survey(name=name,survey_date=date.fromisoformat(day),filename=f'sj-transects-2026-{period+1}.csv',description='匿名同长度样线，个体计数努力不同；固定seed149。');db.add(survey);db.flush()
   for i in range(18):
    alpha=np.asarray([3.5/(j+1)**1.1 for j in range(24)]);alpha[i%3]*=2
    probabilities=rng.dirichlet(alpha);N=int(rng.integers(120,800));counts=rng.multinomial(N,probabilities)
    if period==2 and i==17:counts=np.zeros(24,dtype=int)
    reference=f'SJ-{i+1:02d}'
    if not db.scalar(select(Transect).where(Transect.survey_id==survey.id,Transect.reference==reference)):
     t=Transect(survey_id=survey.id,reference=reference,name=['林缘','溪边','草地'][i%3]+f'样线{i+1:02d}',habitat=['阔叶林缘','溪边灌丛','草地边界'][i%3]);db.add(t);db.flush();db.add_all([SpeciesCount(transect_id=t.id,species=s,count=int(c)) for s,c in zip(SPECIES,counts)])
   db.commit()
  if not db.scalar(select(DiversityRun).where(DiversityRun.name=='秋季共同努力量研究')):
   survey=db.scalar(select(Survey).where(Survey.name=='秋季样线调查'));data=list_transects(db,survey.id);admin=db.scalar(select(User).where(User.role=='admin'));config={'transect_ids':[t['id'] for t in data],'m':100,'bootstrap':200,'seed':20261114};result=analyze(row(survey),data,config);run=DiversityRun(survey_id=survey.id,name='秋季共同努力量研究',config=config,result=result,status='succeeded',creator_id=admin.id);db.add(run);db.flush();db.add(ConservationNote(run_id=run.id,name='林缘稀有种复查草案',transect_ids=[t['id'] for t in result['transects'] if t['status']=='eligible'][:2],observation='相同m=100下比较期望物种数；原N的Shannon/Simpson仅描述，不按原始物种数排优。',suggested_action='复查低计数物种和漏检可能，下一调查期保持样线协议。',creator_id=admin.id));db.add(AuditLog(actor='seed',action='demo.created',detail={'seed':149,'count_rows':1296}));db.commit()
  counts={t.__tablename__:db.scalar(select(func.count()).select_from(t)) for t in [User,Survey,Transect,SpeciesCount,DiversityRun,ConservationNote]};print(json.dumps(counts));return counts
if __name__=='__main__':seed()
