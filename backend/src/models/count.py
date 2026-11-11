from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,ForeignKey,UniqueConstraint,CheckConstraint
from src.config.database import Base
class SpeciesCount(Base):
 __tablename__='species_counts'
 __table_args__=(UniqueConstraint('transect_id','species'),CheckConstraint('count >= 0',name='nonnegative_count'))
 id:Mapped[int]=mapped_column(primary_key=True)
 transect_id:Mapped[int]=mapped_column(ForeignKey('transects.id'))
 species:Mapped[str]=mapped_column(String(10))
 count:Mapped[int]=mapped_column()
