from pydantic import BaseModel, Field



class PaginationParams(BaseModel):
    limit: int = Field(20, le=50, description="Number of data items to return")
    offset: int = Field(0, ge=0, description="Number of data items to skip")
    search: str | None = Field(None, description="Search data items by keyword")
