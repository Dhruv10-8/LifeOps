# IMPORTS

from fastapi import FastAPI, Depends, HTTPException

from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlalchemy.orm import Session

from jose import jwt, JWTError

from datetime import datetime, timedelta

from typing import List

from pydantic import BaseModel

from database import engine, Base, SessionLocal

from models import UserDB, TaskDB, BillDB, ReminderDB, DocumentDB

from auth import hash_password, verify_password

# APP SETUP
app = FastAPI(title="LifeOps API", version="0.1")

Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AUTH CONSTANTS
SECRET_KEY = "change-this-later"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class UserProfileUpdate(BaseModel):
    name: str
    bio: str = ""
    avatar_url: str = ""
    timezone: str = "UTC"


# PYDANTIC
class UserRegister(BaseModel):
    name: str
    email: str
    password: str


class TaskCreate(BaseModel):
    title: str
    priority: int = 1
    due_date: str | None = None


class Task(BaseModel):
    id: int
    title: str
    completed: bool
    priority: int

    created_at: str | None = None

    due_date: str | None = None

    class Config:
        from_attributes = True


class BillCreate(BaseModel):
    name: str
    amount: int
    due_date: str


class Bill(BaseModel):
    id: int
    name: str
    amount: int
    due_date: str
    paid: bool

    class Config:
        from_attributes = True


class ReminderCreate(BaseModel):
    title: str
    due_date: str


class Reminder(BaseModel):
    id: int
    title: str
    due_date: str
    completed: bool

    class Config:
        from_attributes = True


class DocumentCreate(BaseModel):
    name: str
    category: str
    expiry_date: str | None = None
    notes: str = ""


class Document(BaseModel):
    id: int
    name: str
    category: str
    expiry_date: str | None = None
    notes: str

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# DB DEPENDENCY
def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# JWT HELPERS
def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# CURRENT USER
def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):

    credentials_exception = HTTPException(status_code=401, detail="Invalid token")

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(UserDB).filter(UserDB.id == int(user_id)).first()

    if user is None:
        raise credentials_exception

    return user


# UTILITY FUNCTION
def compute_score(task):

    score = task.priority * 10

    if not task.completed:
        score += 20

    if task.due_date:

        try:

            due = datetime.fromisoformat(task.due_date)

            days = (due - datetime.utcnow()).days

            if days <= 0:
                score += 40

            elif days <= 1:
                score += 30

            elif days <= 3:
                score += 20

            elif days <= 7:
                score += 10

        except:
            pass

    return score


# ROUTES
@app.get("/")
def root():
    return {"message": "LifeOps Backend Running"}


@app.get("/db-test")
def db_test():
    return {"status": "database connected"}


# USER ROUTES


@app.post("/auth/register")
def register_user(user: UserRegister, db: Session = Depends(get_db)):

    existing_user = db.query(UserDB).filter(UserDB.email == user.email).first()

    if existing_user:

        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = UserDB(
        name=user.name, email=user.email, password_hash=hash_password(user.password)
    )

    db.add(new_user)

    db.commit()

    db.refresh(new_user)

    return {"message": "User created", "user_id": new_user.id}


@app.post("/auth/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):

    db_user = db.query(UserDB).filter(UserDB.email == form_data.username).first()

    if not db_user:

        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(form_data.password, db_user.password_hash):

        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(db_user.id)})

    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def get_me(current_user: UserDB = Depends(get_current_user)):

    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
    }


# TASK ROUTES


@app.get("/tasks/", response_model=List[Task])
def get_tasks(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    return db.query(TaskDB).filter(TaskDB.user_id == current_user.id).all()


@app.post("/tasks/", response_model=Task)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    new_task = TaskDB(
        title=task.title,
        completed=False,
        priority=task.priority,
        created_at=datetime.utcnow().isoformat(),
        due_date=task.due_date,
        user_id=current_user.id,
    )

    db.add(new_task)

    db.commit()

    db.refresh(new_task)

    return new_task


@app.put("/tasks/{task_id}", response_model=Task)
def toggle_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    task = (
        db.query(TaskDB)
        .filter(TaskDB.id == task_id, TaskDB.user_id == current_user.id)
        .first()
    )

    if not task:

        raise HTTPException(status_code=404, detail="Task not found")

    task.completed = not task.completed

    db.commit()

    db.refresh(task)

    return task


@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    task = (
        db.query(TaskDB)
        .filter(TaskDB.id == task_id, TaskDB.user_id == current_user.id)
        .first()
    )

    if not task:

        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)

    db.commit()

    return {"message": "Task deleted"}


@app.get("/focus/")
def get_focus(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    tasks = db.query(TaskDB).filter(TaskDB.user_id == current_user.id).all()

    if not tasks:

        return {"focus_task": None, "reason": "No tasks available"}

    active_tasks = [task for task in tasks if not task.completed]

    if not active_tasks:

        return {"focus_task": None, "reason": "All tasks completed"}

    focus_task = max(active_tasks, key=compute_score)

    return {"focus_task": focus_task.title, "score": compute_score(focus_task)}


# BILL ROUTES
@app.post("/bills/", response_model=Bill)
def create_bill(
    bill: BillCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    new_bill = BillDB(
        name=bill.name,
        amount=bill.amount,
        due_date=bill.due_date,
        paid=False,
        user_id=current_user.id,
    )

    db.add(new_bill)

    db.commit()

    db.refresh(new_bill)

    return new_bill


@app.get("/bills/", response_model=List[Bill])
def get_bills(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    return db.query(BillDB).filter(BillDB.user_id == current_user.id).all()


@app.put("/bills/{bill_id}/pay")
def pay_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    bill = (
        db.query(BillDB)
        .filter(BillDB.id == bill_id, BillDB.user_id == current_user.id)
        .first()
    )

    if not bill:

        raise HTTPException(status_code=404, detail="Bill not found")

    bill.paid = True

    db.commit()

    db.refresh(bill)

    return bill


@app.delete("/bills/{bill_id}")
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    bill = (
        db.query(BillDB)
        .filter(BillDB.id == bill_id, BillDB.user_id == current_user.id)
        .first()
    )

    if not bill:

        raise HTTPException(status_code=404, detail="Bill not found")

    db.delete(bill)

    db.commit()

    return {"message": "Bill deleted"}


# REMINDER ROUTES


@app.post("/reminders/", response_model=Reminder)
def create_reminder(
    reminder: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    new_reminder = ReminderDB(
        title=reminder.title,
        due_date=reminder.due_date,
        completed=False,
        user_id=current_user.id,
    )

    db.add(new_reminder)

    db.commit()

    db.refresh(new_reminder)

    return new_reminder


@app.get("/reminders/", response_model=List[Reminder])
def get_reminders(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    return db.query(ReminderDB).filter(ReminderDB.user_id == current_user.id).all()


@app.put("/reminders/{reminder_id}")
def complete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    reminder = (
        db.query(ReminderDB)
        .filter(ReminderDB.id == reminder_id, ReminderDB.user_id == current_user.id)
        .first()
    )

    if not reminder:

        raise HTTPException(status_code=404, detail="Reminder not found")

    reminder.completed = not reminder.completed

    db.commit()

    db.refresh(reminder)

    return reminder


@app.delete("/reminders/{reminder_id}")
def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    reminder = (
        db.query(ReminderDB)
        .filter(ReminderDB.id == reminder_id, ReminderDB.user_id == current_user.id)
        .first()
    )

    if not reminder:

        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(reminder)

    db.commit()

    return {"message": "Reminder deleted"}


@app.get("/upcoming-reminders/")
def get_upcoming_reminders(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    reminders = db.query(ReminderDB).filter(ReminderDB.user_id == current_user.id).all()

    upcoming = []

    for reminder in reminders:

        if reminder.completed:
            continue

        try:

            due = datetime.fromisoformat(reminder.due_date)

            days_left = (due - datetime.utcnow()).days

            if days_left <= 7:

                upcoming.append(
                    {
                        "id": reminder.id,
                        "title": reminder.title,
                        "due_date": reminder.due_date,
                        "days_remaining": days_left,
                    }
                )

        except:
            pass

    return {"count": len(upcoming), "reminders": upcoming}


# DOCUMENT APIs
@app.post("/documents/", response_model=Document)
def create_document(
    document: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    new_document = DocumentDB(
        name=document.name,
        category=document.category,
        expiry_date=document.expiry_date,
        notes=document.notes,
        user_id=current_user.id,
    )

    db.add(new_document)

    db.commit()

    db.refresh(new_document)

    return new_document


@app.get("/documents/", response_model=List[Document])
def get_documents(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    return db.query(DocumentDB).filter(DocumentDB.user_id == current_user.id).all()


@app.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    document = (
        db.query(DocumentDB)
        .filter(DocumentDB.id == document_id, DocumentDB.user_id == current_user.id)
        .first()
    )

    if not document:

        raise HTTPException(status_code=404, detail="Document not found")

    db.delete(document)

    db.commit()

    return {"message": "Document deleted"}


@app.get("/expiring-documents/")
def get_expiring_documents(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    documents = db.query(DocumentDB).filter(DocumentDB.user_id == current_user.id).all()

    expiring = []

    for doc in documents:

        if not doc.expiry_date:
            continue

        try:

            expiry = datetime.fromisoformat(doc.expiry_date)

            days_left = (expiry - datetime.utcnow()).days

            if days_left <= 90:

                expiring.append(
                    {
                        "id": doc.id,
                        "name": doc.name,
                        "category": doc.category,
                        "expiry_date": doc.expiry_date,
                        "days_remaining": days_left,
                    }
                )

        except:
            pass

    return {"count": len(expiring), "documents": expiring}


# Dashboard API
@app.get("/dashboard/")
def get_dashboard(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    tasks = db.query(TaskDB).filter(TaskDB.user_id == current_user.id).all()

    bills = db.query(BillDB).filter(BillDB.user_id == current_user.id).all()

    reminders = db.query(ReminderDB).filter(ReminderDB.user_id == current_user.id).all()

    documents = db.query(DocumentDB).filter(DocumentDB.user_id == current_user.id).all()

    active_tasks = [t for t in tasks if not t.completed]

    focus_task = None

    if active_tasks:

        focus_task = max(active_tasks, key=compute_score)

    return {
        "user": current_user.name,
        "focus_task": (focus_task.title if focus_task else None),
        "tasks": {
            "total": len(tasks),
            "completed": len([t for t in tasks if t.completed]),
            "pending": len([t for t in tasks if not t.completed]),
        },
        "bills": {
            "total": len(bills),
            "paid": len([b for b in bills if b.paid]),
            "unpaid": len([b for b in bills if not b.paid]),
        },
        "documents": {"total": len(documents)},
        "reminders": {"total": len(reminders)},
    }


@app.get("/users/me")
def get_profile(current_user: UserDB = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "bio": current_user.bio,
        "avatar_url": current_user.avatar_url,
        "timezone": current_user.timezone,
        "provider": current_user.provider,
    }


@app.put("/users/me")
def update_profile(
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    current_user.name = data.name
    current_user.bio = data.bio
    current_user.avatar_url = data.avatar_url
    current_user.timezone = data.timezone

    db.commit()
    db.refresh(current_user)

    return current_user


@app.put("/users/change-password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):

    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Wrong password")

    current_user.password_hash = hash_password(data.new_password)

    db.commit()

    return {"message": "Password updated"}


@app.delete("/users/me")
def delete_account(
    db: Session = Depends(get_db), current_user: UserDB = Depends(get_current_user)
):

    db.delete(current_user)
    db.commit()

    return {"message": "Account deleted"}
