from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Date
from datetime import date
from src.config.database import Base
class Survey(Base):
 __tablename__='surveys'
 id:Mapped[int]=mapped_column(primary_key=True)
 name:Mapped[str]=mapped_column(String(100),unique=True)
 survey_date:Mapped[date]=mapped_column(Date)
 filename:Mapped[str]=mapped_column(String(160))
 description:Mapped[str]=mapped_column(String(500),default='')
