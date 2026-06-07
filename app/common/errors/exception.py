from fastapi import HTTPException
from starlette.responses import JSONResponse

from app.common.schemas import ResultBase


class BackendException(HTTPException):
    def __init__(
        self, status_code: int, result: ResultBase, detail: dict | str | None = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.result = result

    def response(self):
        return JSONResponse(
            status_code=self.status_code, content={"result": self.result.model_dump()}
        )

    def __repr__(self):
        return f"\n\n\tstatus code: {self.status_code}\nmessage: {self.result.code}\ndetails: {self.detail}\n\n"

    def __str__(self):
        return str(self.status_code)
