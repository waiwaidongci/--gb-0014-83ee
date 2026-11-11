import json,hashlib
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from src.models import DiversityRun,RunArchive,Survey,Transect,SpeciesCount
from src.constants.species import SPECIES
from src.utils.serialize import row
ALGORITHM_VERSION='individual-rarefaction-multinomial-v1'

def survey_snapshot(db,survey_id):
 survey=db.get(Survey,survey_id)
 if not survey:raise HTTPException(404,'调查期不存在')
 return {k:row(survey)[k] for k in ('id','name','survey_date','filename')}

def transect_snapshot(db,survey_id,transect_ids):
 '''受理时点的完整输入：样线元数据 + 全部24种计数（缺列规范为零）。'''
 ordered=sorted(set(transect_ids))
 rows=db.scalars(select(Transect).where(Transect.id.in_(ordered))).all()
 if len(rows)!=len(ordered):raise HTTPException(422,'所选样线不存在')
 if any(t.survey_id!=survey_id for t in rows):raise HTTPException(422,'所选样线必须来自同一调查期')
 snapshot=[]
 for tid in sorted(rows,key=lambda t:t.reference):
  counts={x.species:x.count for x in db.scalars(select(SpeciesCount).where(SpeciesCount.transect_id==tid.id))}
  snapshot.append({'id':tid.id,'survey_id':tid.survey_id,'reference':tid.reference,'name':tid.name,'habitat':tid.habitat,
                   'counts':{s:int(counts.get(s,0)) for s in sorted(SPECIES)}})
 return snapshot

def compute_fingerprint(survey,transects,config):
 canonical=[{k:t[k] for k in ('id','survey_id','reference','name','habitat','counts')} for t in sorted(transects,key=lambda x:x['reference'])]
 cfg={**config,'transect_ids':sorted(config['transect_ids'])}
 data={'survey':{k:survey[k] for k in ('id','name','survey_date','filename')},'transects':canonical,'config':cfg,'algorithm':ALGORITHM_VERSION}
 return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def accept_run(db,data,user):
 '''受理：校验输入 → 构建不可变快照 → 计算输入指纹 → 幂等去重 → 落库归档。
 返回 (run, deduped)；deduped=True 表示命中既有研究，不重复入队。'''
 survey=survey_snapshot(db,data.survey_id)
 config=data.model_dump(exclude={'name','survey_id'})
 transects=transect_snapshot(db,data.survey_id,config['transect_ids'])
 fingerprint=compute_fingerprint(survey,transects,config)
 existing=db.scalar(select(DiversityRun).where(DiversityRun.input_fingerprint==fingerprint))
 if existing:
  return existing,True
 run=DiversityRun(survey_id=data.survey_id,name=data.name,config=config,creator_id=user.id,input_fingerprint=fingerprint)
 db.add(run);db.flush()
 db.add(RunArchive(run_id=run.id,input_fingerprint=fingerprint,survey_snapshot=survey,
                   transect_snapshot=transects,config_snapshot=config,algorithm_version=ALGORITHM_VERSION))
 try:
  db.commit()
 except IntegrityError:
  # 并发重复投递：唯一约束兜底，回查既有研究，按幂等返回而不是500
  db.rollback()
  existing=db.scalar(select(DiversityRun).where(DiversityRun.input_fingerprint==fingerprint))
  if existing:return existing,True
  raise
 db.refresh(run)
 return run,False

def get_archive(db,run_id):
 return db.scalar(select(RunArchive).where(RunArchive.run_id==run_id))

def load_archive_inputs(archive):
 '''归档还原为 analyze 所需 (survey,transects,config)，与源表完全脱钩。'''
 return dict(archive.survey_snapshot),[dict(t) for t in archive.transect_snapshot],dict(archive.config_snapshot)
