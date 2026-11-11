import numpy as np
from .rarefaction import valid_counts
def indices(counts):
 a=valid_counts(counts);N=int(a.sum())
 if N==0:raise ValueError('空群落的Shannon/Simpson无定义')
 p=a[a>0]/N
 return {'shannon':max(0.,float(-np.sum(p*np.log(p)))),'simpson':float(1-np.sum(p*p)),'observed_species':int(len(p))}
