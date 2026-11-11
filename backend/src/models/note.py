from datetime import datetime,timezone
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,JSON,ForeignKey,DateTime
from src.config.database import Base
class ConservationNote(Base):
 __tablename__='conservation_notes'
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('diversity_runs.id'))
 name:Mapped[str]=mapped_column(String(100))
 transect_ids:Mapped[list]=mapped_column(JSON)
 observation:Mapped[str]=mapped_column(String(600))
 suggested_action:Mapped[str]=mapped_column(String(500))
 status:Mapped[str]=mapped_column(String(20),default='draft')
 review_note:Mapped[str]=mapped_column(String(500),default='')
 creator_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
