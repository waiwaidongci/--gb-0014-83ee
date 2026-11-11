import hashlib
import numpy as np
from .diversity import indices
from .rarefaction import valid_counts,expected_species

def bootstrap_intervals(counts,m,repetitions,seed,key):
 a=valid_counts(counts);N=int(a.sum())
 if N==0:raise ValueError('空群落不可bootstrap')
 if not isinstance(repetitions,int) or not 50<=repetitions<=1000:raise ValueError('bootstrap次数需50..1000')
 if not isinstance(seed,int) or not 0<=seed<=2147483647:raise ValueError('seed范围不合法')
 expected_species(a,m)
 key_seed=int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'big')
 rng=np.random.default_rng(np.random.SeedSequence([seed,key_seed]));replicates=rng.multinomial(N,a/N,size=repetitions)
 H=[];D=[];R=[]
 for sample in replicates:
  result=indices(sample);H.append(result['shannon']);D.append(result['simpson']);R.append(expected_species(sample,m))
 def interval(x):return np.quantile(x,[.025,.975]).tolist()
 return {'shannon_ci':interval(H),'simpson_ci':interval(D),'rarefied_ci':interval(R),'repetitions':repetitions,'method':'percentile 95%; multinomial(N, observed p), conditional on observed composition; unseen species/spatial dependence/detection uncertainty excluded'}
