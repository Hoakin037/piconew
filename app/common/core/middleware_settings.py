from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.common.consts import CommonCodesEnum
from app.common.errors import BackendException
from app.common.logger import setup_logging
from app.common.schemas import ResultBase

logger = setup_logging(__name__)


class ExceptionMiddleware:
    async def __call__(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            logger.exception("CRITICAL UNKNOWN ERROR:")

            unknown_result = ResultBase(code=CommonCodesEnum.UNKNOWN_ERROR)

            error = BackendException(status_code=500, result=unknown_result)
            return error.response()


async def backend_exception_handler(
    request: Request, exc: BackendException
) -> JSONResponse:
    return exc.response()


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    result = ResultBase(
        code=CommonCodesEnum.VALIDATION_ERROR,
    )
    logger.exception(exc)
    return JSONResponse(status_code=422, content={"result": result.model_dump()})


async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("GLOBAL ERROR CAUGHT:")
    result = ResultBase(
        code=CommonCodesEnum.UNKNOWN_ERROR,
    )
    return JSONResponse(status_code=500, content={"result": result.model_dump()})
