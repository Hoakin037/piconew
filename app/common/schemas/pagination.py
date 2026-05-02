from pydantic import BaseModel


class Pagination(BaseModel):
    limit: int = 20
    offset: int = 0
