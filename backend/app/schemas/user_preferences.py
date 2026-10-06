from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPreferencesCreate(BaseModel):
    theme: str = Field(
        default="dark",
        min_length=1,
        max_length=20,
    )

    daily_briefing_enabled: bool = True

    security_alerts_enabled: bool = True

    planner_start_hour: int = Field(
        default=8,
        ge=0,
        le=23,
    )

    timezone: str = Field(
        default="Asia/Kolkata",
        min_length=1,
        max_length=50,
    )

    time_format: str = Field(
        default="24h",
        pattern=r"^(12h|24h)$",
    )


class UserPreferencesUpdate(BaseModel):
    theme: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    daily_briefing_enabled: bool | None = None

    security_alerts_enabled: bool | None = None

    planner_start_hour: int | None = Field(
        default=None,
        ge=0,
        le=23,
    )

    timezone: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    time_format: str | None = Field(
        default=None,
        pattern=r"^(12h|24h)$",
    )

    onboarding_completed: bool | None = None

    onboarding_version: int | None = None


class UserPreferencesResponse(BaseModel):
    id: int
    user_id: int
    theme: str
    daily_briefing_enabled: bool
    security_alerts_enabled: bool
    planner_start_hour: int
    timezone: str
    time_format: str
    onboarding_completed: bool
    onboarding_version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)