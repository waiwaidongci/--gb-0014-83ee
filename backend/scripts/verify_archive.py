'''受理归档/幂等/原子写验证脚本（SQLite 临时库，无需 Docker/Redis）。
运行：JWT_SECRET=verify PYTHONPATH=. python scripts/verify_archive.py
覆盖：补正隔离、重复投递去重、失败重试同归档、原子写失败、历史研究拒绝复算、队列失败、API 层。'''
import os,tempfile,json
os.environ.setdefault('JWT_SECRET','verify-secret')
_DB_FD,_DB_PATH=tempfile.mkstemp(suffix='.db');os.close(_DB_FD)
_ART=tempfile.mkdtemp()
os.environ['DATABASE_URL']='sqlite+pysqlite:///'+_DB_PATH
os.environ['ARTIFACT_DIR']=_ART
from datetime import date
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from src.config.database import Base,engine,SessionLocal
from src.models import *
from src.services import runs as runs_service
from src.services.archive import get_archive,load_archive_inputs
from src.services.transects import get_counts
from src.services.analysis import analyze as analyze_fn
from src.utils.security import hash_password,issue_token
from src.utils.artifacts import artifact_path,write_run_artifact,read_run_artifact
from src.schemas.run import DiversityInput
from src import worker as wmod
from src.main import app
from src.config.database import get_db

# 无 Redis 环境：用内存假任务替换服务层的 Celery 投递；真实任务体保留为 _execute
_execute=wmod.analyze_run
class _FakeTask:
 def delay(self,run_id):return None
wmod.analyze_run=_FakeTask()
def execute(run_id):_execute(run_id)

PASS=[];FAIL=[]
def check(name,cond,detail=''):
 (PASS if cond else FAIL).append(name)
 print(('  ✓ ' if cond else '  ✗ ')+name+(' — '+detail if detail and not cond else ''))

Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
SPECIES=[f'S{i:02d}' for i in range(1,25)]

def seed_fixtures():
 with SessionLocal() as db:
  u=User(email='analyst@test',name='分析师',role='analyst',password_hash=hash_password('pw'))
  db.add(u);db.flush()
  sv=Survey(name='秋季调查',survey_date=date(2026,10,14),filename='sj.csv')
  db.add(sv);db.flush()
  tids=[]
  for i in range(3):
   t=Transect(survey_id=sv.id,reference=f'SJ-{i+1:02d}',name=f'样线{i+1}',habitat='林缘')
   db.add(t);db.flush();tids.append(t.id)
   for j,s in enumerate(SPECIES):
    count=0 if i==2 else (200//(j+2) if j<6 else (1 if j<10 else 0))
    db.add(SpeciesCount(transect_id=t.id,species=s,count=count))
  db.commit();return sv.id,tids,u.id

SURVEY_ID,TIDS,UID=seed_fixtures()
def payload(**over):
 p=dict(name='研究A',survey_id=SURVEY_ID,transect_ids=TIDS[:2],m=50,bootstrap=50,seed=42)
 p.update(over);return DiversityInput(**p)
def user():
 with SessionLocal() as db:return db.get(User,UID)
def run_by_id(rid):
 with SessionLocal() as db:return db.get(DiversityRun,rid)
def arch(rid):
 with SessionLocal() as db:return get_archive(db,rid)
def artifact_file(rid):return Path(artifact_path(_ART,rid))
def run_count():
 with SessionLocal() as db:return db.scalar(select(func.count()).select_from(DiversityRun))

print('\n== 场景1：受理归档冻结输入，源数据补正不改变归档输入与结果指纹 ==')
# 1a 补正前：顺序变化与重复投递都命中同一指纹（幂等）
with SessionLocal() as db:
 first,dedup0=runs_service.create_run(db,payload(),user())
check('首次受理为新建（非去重）',not dedup0)
rid=first['id']
with SessionLocal() as db:
 shuffled,dup_sh=runs_service.create_run(db,payload(transect_ids=list(reversed(TIDS[:2]))),user())
check('样线选择顺序变化不改指纹、命中去重',dup_sh and shuffled['id']==rid)
with SessionLocal() as db:
 again,dup1=runs_service.create_run(db,payload(name='研究A-重复投递'),user())
check('重复投递返回既有研究且不新建',dup1 and again['id']==rid)
check('研究总数未增加（不重复发布结果）',run_count()==1)
# 1b worker 消费，成功并落盘
execute(rid)
r=run_by_id(rid);a=arch(rid);fp_before=a.input_fingerprint
check('研究成功',r.status=='succeeded',r.error or '')
check('结果指纹等于归档输入指纹',r.result['fingerprint']==fp_before)
check('结果文件落盘且内容与库一致',artifact_file(rid).exists() and json.loads(artifact_file(rid).read_text())==r.result)
snapshot_before=json.loads(json.dumps(a.transect_snapshot));res_before=json.loads(json.dumps(r.result))
# 1c 补正源数据：SJ-01 的 S01 计数 +37
with SessionLocal() as db:
 c=db.scalar(select(SpeciesCount).where(SpeciesCount.transect_id==TIDS[0],SpeciesCount.species=='S01'))
 old_s01=c.count;c.count+=37;db.commit()
 live=get_counts(db,TIDS[0])
check('源数据确实已补正',live['S01']==old_s01+37)
a2=arch(rid);r2=run_by_id(rid)
check('归档完整计数快照未被补正改变',a2.transect_snapshot==snapshot_before)
check('归档调查期与所选样线集合冻结',a2.survey_snapshot['id']==SURVEY_ID and [t['reference'] for t in a2.transect_snapshot]==['SJ-01','SJ-02'])
check('库结果与结果指纹保持原值',r2.result==res_before and r2.result['fingerprint']==fp_before)
survey_s,tran_s,cfg_s=load_archive_inputs(a2)
check('按归档重算指纹不变',analyze_fn(survey_s,tran_s,cfg_s)['fingerprint']==fp_before)
live_trans=[dict(t,counts={s:live.get(s,0) for s in SPECIES}) if t['id']==TIDS[0] else t for t in tran_s]
check('按补正后源数据重算得到不同指纹',analyze_fn(survey_s,live_trans,cfg_s)['fingerprint']!=fp_before)
# 1d 补正后同载荷是新输入：产生新研究；再次投递仍对新指纹幂等
with SessionLocal() as db:
 post_fix,dup2=runs_service.create_run(db,payload(name='补正后研究'),user())
check('补正后同载荷识别为新输入（新研究）',not dup2 and post_fix['id']!=rid)
with SessionLocal() as db:
 post_fix2,dup3=runs_service.create_run(db,payload(name='补正后研究-重复'),user())
check('补正后重复投递仍按新指纹去重',dup3 and post_fix2['id']==post_fix['id'])
check('研究总数为2（原研究与补正后研究各一）',run_count()==2)

print('\n== 场景2：中途失败后重试仍按同一份归档计算 ==')
# 2a 非法 m：先归档后计算失败
with SessionLocal() as db:
 rb,_=runs_service.create_run(db,payload(name='超限研究',m=99999),user());bid=rb['id']
execute(bid);rb=run_by_id(bid)
check('非法m研究失败且无结果文件',rb.status=='failed' and not artifact_file(bid).exists())
check('失败研究仍保留受理归档与指纹',arch(bid) is not None and bool(arch(bid).input_fingerprint))
# 2b 合法研究模拟 worker 中途崩溃（running 中断、无文件）
with SessionLocal() as db:
 rq,_=runs_service.create_run(db,payload(name='中断研究',seed=7),user());qid=rq['id']
qa_fp=arch(qid).input_fingerprint
with SessionLocal() as db:
 db.get(DiversityRun,qid).status='running';db.commit()
check('中断研究处于running且尚无结果文件',run_by_id(qid).status=='running' and not artifact_file(qid).exists())
with SessionLocal() as db:
 ret,queued=runs_service.retry_run(db,qid,user())
check('重试受理并重新排队',queued and ret['status']=='queued')
execute(qid);rq2=run_by_id(qid)
check('重试后成功',rq2.status=='succeeded',rq2.error or '')
check('重试仍按同一份归档（指纹一致）',arch(qid).input_fingerprint==qa_fp and rq2.result['fingerprint']==qa_fp)
check('成功后结果文件与状态对应',artifact_file(qid).exists())
mtime=artifact_file(qid).stat().st_mtime_ns
execute(qid)
check('成功研究重复执行直接跳过、不重复发布',run_by_id(qid).status=='succeeded' and artifact_file(qid).stat().st_mtime_ns==mtime)
with SessionLocal() as db:
 _,queued2=runs_service.retry_run(db,qid,user())
check('成功研究重试为no-op',not queued2)

print('\n== 场景3：写入失败不留成功假象，恢复后重试成功且文件/状态对应 ==')
with SessionLocal() as db:
 rw,_=runs_service.create_run(db,payload(name='写失败研究',seed=9),user());wid=rw['id']
wa_fp=arch(wid).input_fingerprint
real_replace=os.replace
def boom(src,dst):raise OSError('模拟磁盘替换失败')
os.replace=boom
try:execute(wid)
finally:os.replace=real_replace
rw1=run_by_id(wid)
check('写入失败时研究标记failed',rw1.status=='failed' and '模拟磁盘替换失败' in (rw1.error or ''))
check('写入失败无结果文件、无临时残留',not artifact_file(wid).exists() and not list(Path(_ART).glob(f'.diversity-{wid}.*.tmp')))
check('写入失败未清空归档（可重试）',arch(wid).input_fingerprint==wa_fp)
with SessionLocal() as db:runs_service.retry_run(db,wid,user())
execute(wid);rw2=run_by_id(wid)
check('恢复后重试成功',rw2.status=='succeeded')
check('结果文件与succeeded对应且指纹一致',json.loads(artifact_file(wid).read_text())['fingerprint']==wa_fp)
# 3b 提交后复核失败（复核读取抛错）→ 回退 failed
artifact_file(wid).unlink()
with SessionLocal() as db:db.get(DiversityRun,wid).status='queued';db.commit()
wmod.read_run_artifact=lambda *a,**k:(_ for _ in ()).throw(OSError('模拟复核读失败'))
execute(wid);wmod.read_run_artifact=read_run_artifact
rw3=run_by_id(wid)
check('复核失败回退failed且无结果文件',rw3.status=='failed' and not artifact_file(wid).exists())
with SessionLocal() as db:runs_service.retry_run(db,wid,user())
execute(wid)
check('再次重试恢复成功且文件归位',run_by_id(wid).status=='succeeded' and artifact_file(wid).exists())
# 3c 原子写工具对不可写目录明确抛错
try:
 write_run_artifact('/nonexistent-root-xyz/'+os.urandom(4).hex(),1,{'x':1});check('不可写目录应抛错',False)
except OSError:check('不可写目录明确抛错、无假成功',True)

print('\n== 场景4：历史研究没有归档，明确拒绝复算 ==')
with SessionLocal() as db:
 legacy=DiversityRun(survey_id=SURVEY_ID,name='历史研究',config=payload().model_dump(exclude={'name','survey_id'}),result={},status='failed',creator_id=UID)
 db.add(legacy);db.commit();lid=legacy.id
try:
 with SessionLocal() as db:runs_service.retry_run(db,lid,user())
 check('无归档历史研究重试被拒绝',False)
except Exception as e:
 check('无归档历史研究重试被拒绝(409)',getattr(e,'status_code',None)==409 and '归档' in str(e.detail))
execute(lid)
check('worker对无归档研究置failed并说明原因',run_by_id(lid).status=='failed' and '归档' in (run_by_id(lid).error or ''))
check('无归档研究不产生结果文件',not artifact_file(lid).exists())

print('\n== 场景5：队列不可用不留下排队假象 ==')
def broken_delay(*a,**k):raise ConnectionError('redis down')
orig=wmod.analyze_run.delay;wmod.analyze_run.delay=broken_delay
try:
 with SessionLocal() as db:
  try:
   runs_service.create_run(db,payload(name='队列失败研究',seed=11),user());check('队列不可用应503',False)
  except Exception as e:
   check('队列不可用返回503',getattr(e,'status_code',None)==503)
  qfail=db.scalar(select(DiversityRun).where(DiversityRun.name=='队列失败研究'))
  check('入队失败研究落为failed而非queued',qfail is not None and qfail.status=='failed' and qfail.error=='队列不可用')
finally:
 wmod.analyze_run.delay=orig

print('\n== 场景6：API 层端到端（TestClient + SQLite） ==')
def override_db():
 with SessionLocal() as db:yield db
app.dependency_overrides[get_db]=override_db
client=TestClient(app)
H={'Authorization':'Bearer '+issue_token(user())}
r1=client.post('/runs',json=payload(name='API研究',seed=13).model_dump(),headers=H)
r2=client.post('/runs',json=payload(name='API研究-重复',seed=13).model_dump(),headers=H)
check('首次API受理201',r1.status_code==201)
check('重复投递200且去重头存在',r2.status_code==200 and r2.headers.get('x-deduplicated')=='true' and r2.json()['id']==r1.json()['id'])
api_id=r1.json()['id'];execute(api_id)
check('API受理研究可被worker计算成功',client.get(f'/runs/{api_id}',headers=H).json()['status']=='succeeded')
rn=client.post(f'/runs/{api_id}/retry',headers=H)
check('成功研究retry为no-op',rn.status_code==200 and rn.headers.get('x-no-op')=='true')
rl=client.post(f'/runs/{lid}/retry',headers=H)
check('历史无归档研究API重试409',rl.status_code==409 and '归档' in rl.json()['detail'])
with SessionLocal() as db:
 v=User(email='v@test',name='记录员',role='viewer',password_hash=hash_password('pw'));db.add(v);db.commit();vid=v.id
with SessionLocal() as db:vtoken=issue_token(db.get(User,vid))
rv=client.post('/runs',json=payload(seed=15).model_dump(),headers={'Authorization':'Bearer '+vtoken})
check('viewer提交研究403',rv.status_code==403)
# 失败研究（非法m的 bid）经 API 重试：修正不了输入则仍失败，但路径可用；这里对写失败恢复后的 wid 已成功，改用 running 中断研究验证
rr_bad=client.post(f'/runs/{bid}/retry',headers=H)
check('失败研究API重试可重新入队（按同归档再算）',rr_bad.status_code==200 and rr_bad.json()['status']=='queued')
execute(bid)
check('同归档非法m重试仍失败、仍无结果文件',client.get(f'/runs/{bid}',headers=H).json()['status']=='failed' and not artifact_file(bid).exists())

print(f'\n结果：{len(PASS)} 通过 / {len(FAIL)} 失败')
if FAIL:
 print('失败项：');[print(' -',x) for x in FAIL];raise SystemExit(1)
print('全部通过')
