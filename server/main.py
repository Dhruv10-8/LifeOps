from fastapi import Depends
from sqlalchemy.orm import Session
from database import engine, Base, SessionLocal
from models import TaskDB, BillDB
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI(
    title="LifeOps API",
    version="0.1"
)

Base.metadata.create_all(bind=engine)

# Updated Codespaces CORS block
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Safe for local proxy development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class TaskCreate(BaseModel):
    title: str
    priority: int = 1
    due_date: str | None = None

class Task(BaseModel):
    id: int
    title: str
    completed: bool = False

    priority: int = 1

    created_at: str | None = None
    last_updated: str | None = None

    due_date: str | None = None

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

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

def compute_score(task: TaskDB):
    score = 0

    # Priority
    score += task.priority * 10

    # Completion bonus/penalty
    if not task.completed:
        score += 20
    else:
        score -= 10

    # Age factor
    if task.created_at:
        try:
            created = datetime.fromisoformat(task.created_at)
            days_old = (datetime.utcnow() - created).days

            score += min(days_old * 2, 20)
        except:
            pass

    # Due date urgency
    if task.due_date:
        try:
            due = datetime.fromisoformat(task.due_date)

            days_until_due = (due - datetime.utcnow()).days

            if days_until_due <= 0:
                score += 40
            elif days_until_due <= 1:
                score += 30
            elif days_until_due <= 3:
                score += 20
            elif days_until_due <= 7:
                score += 10

        except:
            pass

    return score


@app.get("/")
def root():
    return {"message": "LifeOps Backend Running"}

@app.get("/db-test/")
def db_test(db: Session = Depends(get_db)):
    return {"status": "database connected"}


@app.get("/tasks/", response_model=List[Task])
def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(TaskDB).all()
    return tasks


@app.post("/tasks/", response_model=Task)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = TaskDB(
        title=task.title,
        completed=False,
        priority=task.priority,
        created_at=datetime.utcnow().isoformat(),
        due_date=task.due_date
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task


@app.put("/tasks/{task_id}/", response_model=Task)
def toggle_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskDB).filter(
        TaskDB.id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    task.completed = not task.completed

    db.commit()
    db.refresh(task)

    return task


@app.delete("/tasks/{task_id}/")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskDB).filter(
        TaskDB.id == task_id
    ).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    db.delete(task)
    db.commit()

    return {
        "message": "Task deleted"
    }

@app.get("/focus/")
def get_focus(db: Session = Depends(get_db)):
    tasks = db.query(TaskDB).all()
    if not tasks:
        return {
            "focus_task": None,
            "reason": "No tasks available"
        }

    scored_tasks = [
        (task, compute_score(task))
        for task in tasks
        if not task.completed
    ]

    if not scored_tasks:
        return {
            "focus_task": None,
            "reason": "All tasks completed"
        }

    best_task, best_score = max(scored_tasks, key=lambda x: x[1])
    return {
        "focus_task": best_task,
        "score": best_score,
        "reason": "Highest priority + urgency + age weighting"
    }

@app.post("/bills/", response_model=Bill)
def create_bill(
    bill: BillCreate,
    db: Session = Depends(get_db)
):
    new_bill = BillDB(
        name=bill.name,
        amount=bill.amount,
        due_date=bill.due_date,
        paid=False
    )

    db.add(new_bill)
    db.commit()
    db.refresh(new_bill)

    return new_bill

@app.get("/bills/", response_model=List[Bill])
def get_bills(
    db: Session = Depends(get_db)
):
    return db.query(BillDB).all()

@app.put("/bills/{bill_id}/pay")
def pay_bill(
    bill_id: int,
    db: Session = Depends(get_db)
):
    bill = (
        db.query(BillDB)
        .filter(BillDB.id == bill_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill not found"
        )

    bill.paid = True

    db.commit()
    db.refresh(bill)

    return bill

@app.delete("/bills/{bill_id}")
def delete_bill(
    bill_id: int,
    db: Session = Depends(get_db)
):
    bill = (
        db.query(BillDB)
        .filter(BillDB.id == bill_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill not found"
        )

    db.delete(bill)
    db.commit()

    return {
        "message": "Bill deleted"
    }

@app.get("/dashboard/")
def get_dashboard(
    db: Session = Depends(get_db)
):
    tasks = db.query(TaskDB).all()
    bills = db.query(BillDB).all()

    completed_tasks = sum(
        1 for task in tasks
        if task.completed
    )

    pending_tasks = sum(
        1 for task in tasks
        if not task.completed
    )

    paid_bills = sum(
        1 for bill in bills
        if bill.paid
    )

    unpaid_bills = sum(
        1 for bill in bills
        if not bill.paid
    )

    focus_task = None

    active_tasks = [
        task
        for task in tasks
        if not task.completed
    ]

    if active_tasks:
        focus_task = max(
            active_tasks,
            key=compute_score
        )

    return {
        "focus_task": (
            focus_task.title
            if focus_task
            else None
        ),

        "tasks": {
            "total": len(tasks),
            "completed": completed_tasks,
            "pending": pending_tasks
        },

        "bills": {
            "total": len(bills),
            "paid": paid_bills,
            "unpaid": unpaid_bills
        }
    }