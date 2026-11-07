"""Structured weather data the copilot reasons over."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Wind(BaseModel):
    direction_deg: int | None = Field(
        None, ge=0, le=360, description="True direction; None if variable (VRB)"
    )
    speed_kt: int = Field(ge=0)
    gust_kt: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def gust_exceeds_speed(self) -> "Wind":
        if self.gust_kt is not None and self.gust_kt <= self.speed_kt:
            raise ValueError("gust_kt must be greater than speed_kt")
        return self


class WeatherSummary(BaseModel):
    station: str = Field(pattern=r"^[A-Z0-9]{4}$", description="ICAO identifier")
    observed_at: datetime
    wind: Wind
    visibility_sm: float = Field(ge=0, description="Statute miles")
    ceiling_ft_agl: int | None = Field(
        None, ge=0, description="Lowest BKN, OVC, or VV layer; None if no ceiling"
    )
    hazards: list[str] = Field(default_factory=list)
