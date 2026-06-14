from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str
    priority: int = 1
    due_date: str | None = None

class TaskResponse(BaseModel):
    id: int
    title: str
    completed: bool
    priority: int
    created_at: str | None = None
    due_date: str | None = None

    class Config:
        from_attributes = True