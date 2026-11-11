import os
DATABASE_URL=os.getenv('DATABASE_URL','postgresql+psycopg://ecology:ecology_demo@db:5432/ecology')
REDIS_URL=os.getenv('REDIS_URL','redis://redis:6379/0')
JWT_SECRET=os.environ['JWT_SECRET']
SEED_DEMO=os.getenv('SEED_DEMO','true').lower()=='true'
ARTIFACT_DIR=os.getenv('ARTIFACT_DIR','/artifacts')
