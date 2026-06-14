from sqlalchemy import Column, Integer, String, Boolean, Text
from database import Base

class BillDB(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    amount = Column(Integer)

    due_date = Column(String)

    paid = Column(Boolean, default=False)


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    completed = Column(Boolean, default=False)

    priority = Column(Integer, default=1)

    created_at = Column(String)

    due_date = Column(String)