from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,ForeignKey,UniqueConstraint
from src.config.database import Base
class Transect(Base):
 __tablename__='transects'
 __table_args__=(UniqueConstraint('survey_id','reference'),)
 id:Mapped[int]=mapped_column(primary_key=True)
 survey_id:Mapped[int]=mapped_column(ForeignKey('surveys.id'))
 reference:Mapped[str]=mapped_column(String(50))
 name:Mapped[str]=mapped_column(String(100))
 habitat:Mapped[str]=mapped_column(String(80))
