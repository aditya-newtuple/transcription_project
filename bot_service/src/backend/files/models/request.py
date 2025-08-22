from pydantic import BaseModel


class CreateFileRequest(BaseModel):
    job_id: int
