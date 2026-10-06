from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreate(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=200,
    )

    message: str

    type: str = Field(
        default="info",
        min_length=1,
        max_length=50,
    )

    link: str | None = Field(
        default=None,
        max_length=255,
    )


class NotificationUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    message: str | None = None

    type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    link: str | None = Field(
        default=None,
        max_length=255,
    )

    is_read: bool | None = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    link: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)