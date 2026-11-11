import json,hashlib
from src.constants.species import SPECIES

def fingerprint(survey,transects,config):
 canonical=[]
 for t in sorted(transects,key=lambda x:x['reference']):
  canonical.append({'id':t['id'],'survey_id':t['survey_id'],'reference':t['reference'],'name':t['name'],'habitat':t['habitat'],'counts':{s:int(t['counts'].get(s,0)) for s in sorted(SPECIES)}})
 cfg={**config,'transect_ids':sorted(config['transect_ids'])}
 data={'survey':{k:survey[k] for k in ('id','name','survey_date','filename')},'transects':canonical,'config':cfg,'algorithm':'individual-rarefaction-multinomial-v1'}
 return hashlib.sha256(json.dumps(data,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()
