from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,ForeignKey,DateTime,UniqueConstraint,Text
from src.config.database import Base
class RunArchive(Base):
 '''研究受理时不可变的输入快照：调查期、所选样线及完整计数与配置。
 源数据后续补正不影响归档；worker 与复算只能读取本快照。'''
 __tablename__='run_archives'
 __table_args__=(UniqueConstraint('input_fingerprint',name='uq_run_archive_fingerprint'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('diversity_runs.id'),unique=True)
 input_fingerprint:Mapped[str]=mapped_column(String(64))
 survey_snapshot:Mapped[dict]=mapped_column(JSON)
 transect_snapshot:Mapped[list]=mapped_column(JSON)
 config_snapshot:Mapped[dict]=mapped_column(JSON)
 artifact_path:Mapped[str|None]=mapped_column(String(255),nullable=True)
 algorithm_version:Mapped[str]=mapped_column(String(80),default='individual-rarefaction-multinomial-v1')
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
