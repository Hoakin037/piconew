from app.common.schemas import CoreSchema


class Pagination(CoreSchema):
    limit: int = 20
    offset: int = 0


class CursorPagination(CoreSchema):
    total: int
    limit: int
    has_more: bool
