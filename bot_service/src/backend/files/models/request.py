from typing import Optional

from pydantic import BaseModel


class CreateFileRequest(BaseModel):
    job_id: int
    sequence_no: Optional[int] = None
    language_hint: Optional[str] = None
