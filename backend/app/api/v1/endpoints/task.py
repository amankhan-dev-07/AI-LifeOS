from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import (
    create_user_task,
    delete_user_task,
    get_user_task,
    get_user_tasks,
    update_user_task,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = create_user_task(
        db=db,
        user_id=current_user.id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        goal_id=data.goal_id,
        estimated_minutes=data.estimated_minutes,
    )

    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=list[TaskResponse],
)
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskResponse]:
    tasks = get_user_tasks(
        db=db,
        user_id=current_user.id,
    )

    return [
        TaskResponse.model_validate(task)
        for task in tasks
    ]


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    return TaskResponse.model_validate(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskResponse:
    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    updates = data.model_dump(
        exclude_unset=True,
    )

    task = update_user_task(
        db=db,
        task=task,
        **updates,
    )

    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    task = get_user_task(
        db=db,
        task_id=task_id,
        user_id=current_user.id,
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found.",
        )

    delete_user_task(
        db=db,
        task=task,
    )