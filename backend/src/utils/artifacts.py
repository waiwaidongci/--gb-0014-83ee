import json,os,tempfile
from pathlib import Path
class ArtifactWriteError(RuntimeError):pass
def artifact_path(artifact_dir,run_id):return str(Path(artifact_dir,f'diversity-{run_id}.json'))
def write_run_artifact(artifact_dir,run_id,payload):
 '''原子写结果文件：同目录临时文件 → flush/fsync → 回读校验 → os.replace。
 任一步失败都清理临时文件并抛出，绝不留下“看似成功”的结果文件。'''
 directory=Path(artifact_dir);directory.mkdir(parents=True,exist_ok=True)
 final=Path(artifact_path(directory,run_id))
 fd,tmp_name=tempfile.mkstemp(prefix=f'.diversity-{run_id}.',suffix='.tmp',dir=directory)
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:
   json.dump(payload,f,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
  with open(tmp_name,encoding='utf-8') as f:
   on_disk=json.load(f)
  if on_disk!=payload:raise ArtifactWriteError('结果文件回读校验不一致')
  os.replace(tmp_name,final)
 except Exception:
  try:os.unlink(tmp_name)
  except FileNotFoundError:pass
  raise
 return str(final)
def read_run_artifact(artifact_dir,run_id):
 with open(artifact_path(artifact_dir,run_id),encoding='utf-8') as f:return json.load(f)
