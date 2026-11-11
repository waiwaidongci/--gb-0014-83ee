import numpy as np
from scipy.special import gammaln

def valid_counts(counts):
 a=np.asarray(counts)
 if a.ndim!=1 or not len(a) or not np.issubdtype(a.dtype,np.number) or not np.isfinite(a).all() or (a<0).any() or not np.equal(a,np.floor(a)).all():raise ValueError('物种计数必须为有限非负整数向量')
 if a.sum()>2400000:raise ValueError('样线个体总量超研究配额')
 return a.astype(np.int64)
def expected_species(counts,m):
 a=valid_counts(counts);N=int(a.sum())
 if not isinstance(m,(int,np.integer)) or not 0<=m<=N:raise ValueError('稀释量m必须是0..N的整数')
 if m==0:return 0.
 if m==1:return 1.
 positive=a[a>0]
 if m==N:return float(len(positive))
 if N==0:raise ValueError('空群落无法稀释')
 remain=N-positive;possible=remain>=m;contribution=np.ones(len(positive),dtype=float)
 # log C(N-n_i,m) - log C(N,m); -expm1 avoids cancellation for rare species.
 log_denom=gammaln(N+1)-gammaln(m+1)-gammaln(N-m+1)
 z=remain[possible];log_numer=gammaln(z+1)-gammaln(m+1)-gammaln(z-m+1)
 contribution[possible]=-np.expm1(np.minimum(log_numer-log_denom,0.))
 return float(np.clip(contribution.sum(),0,len(positive)))
