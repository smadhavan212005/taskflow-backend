from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskCreate(BaseModel):
    text: str
    completed: bool = False

class TaskUpdate(BaseModel):
    text: Optional[str] = None
    completed: Optional[bool] = None

class TaskResponse(TaskCreate):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
