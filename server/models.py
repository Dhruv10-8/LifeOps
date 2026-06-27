from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Text
)

from sqlalchemy.orm import relationship

from database import Base


class UserDB(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(String)

    email = Column(
        String,
        unique=True,
        nullable=False
    )

    password_hash = Column(
        String,
        nullable=False
    )

    provider = Column(
        String,
        default="local"
    )

    tasks = relationship(
        "TaskDB",
        back_populates="user"
    )

    bills = relationship(
        "BillDB",
        back_populates="user"
    )

    reminders = relationship(
        "ReminderDB",
        back_populates="user"
    )

    documents = relationship(
        "DocumentDB",
        back_populates="user"
    )
    bio = Column(Text, default="")
    avatar_url = Column(String, default="")
    timezone = Column(String, default="UTC")


class BillDB(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    amount = Column(Integer)

    due_date = Column(String)

    paid = Column(Boolean, default=False)

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    user = relationship(
        "UserDB",
        back_populates="bills"
    )


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    completed = Column(Boolean, default=False)

    priority = Column(Integer, default=1)

    created_at = Column(String)

    due_date = Column(String)

    tags = Column(Text, default="")

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    user = relationship(
        "UserDB",
        back_populates="tasks"
    )


class ReminderDB(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String)

    due_date = Column(String)

    completed = Column(Boolean, default=False)
    
    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    user = relationship(
        "UserDB",
        back_populates="reminders"
    )


class DocumentDB(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)

    category = Column(String)

    expiry_date = Column(String)

    notes = Column(Text)

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    user = relationship(
        "UserDB",
        back_populates="documents"
    )