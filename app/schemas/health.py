from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str = "AI Document Intelligence Platform"
    version: str = "0.1.0"