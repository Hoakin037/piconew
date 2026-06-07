from pydantic import BaseModel

from app.common.consts import CommonCodesEnum


class ResultBase(BaseModel):
    code: CommonCodesEnum = CommonCodesEnum.DEFAULT


class ResultResponse(BaseModel):
    result: ResultBase
