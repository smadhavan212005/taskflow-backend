from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import os
from datetime import datetime
import uuid
from pydantic import BaseModel

from database import get_db, Task
from models import TaskCreate, TaskUpdate, TaskResponse

app = FastAPI(title="TaskFlow API", version="1.0.0")

# CORS - Update with your frontend URL after deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend.onrender.com",
        "https://taskflow.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "TaskFlow API v1.0.0",
        "status": "healthy",
        "docs": "/docs",
        "database": "Supabase PostgreSQL"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.post("/tasks/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Create new task for authenticated user"""
    try:
        db_task = Task(
            user_id=uuid.UUID(x_user_id),
            text=task.text.strip(),
            completed=task.completed
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")

@app.get("/tasks/", response_model=List[TaskResponse])
async def get_tasks(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Get all tasks for authenticated user"""
    tasks = db.query(Task)\
        .filter(Task.user_id == uuid.UUID(x_user_id))\
        .order_by(Task.created_at.desc())\
        .all()
    return tasks

@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task: TaskUpdate,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Update existing task"""
    db_task = db.query(Task).filter(
        Task.id == uuid.UUID(task_id),
        Task.user_id == uuid.UUID(x_user_id)
    ).first()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Delete task"""
    db_task = db.query(Task).filter(
        Task.id == uuid.UUID(task_id),
        Task.user_id == uuid.UUID(x_user_id)
    ).first()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}

@app.delete("/tasks/clear-completed/")
async def clear_completed_tasks(
    x_user_id: str = Header(..., alias="X-User-ID"),
    db: Session = Depends(get_db)
):
    """Clear all completed tasks"""
    deleted_count = db.query(Task)\
        .filter(
            Task.user_id == uuid.UUID(x_user_id),
            Task.completed == True
        )\
        .delete()
    db.commit()
    return {"message": f"Deleted {deleted_count} completed tasks"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
