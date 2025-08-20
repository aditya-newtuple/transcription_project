from typing import Optional

from pydantic import BaseModel


class CreateJobRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
