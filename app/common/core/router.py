from fastapi import APIRouter

from  app.modules import auth

router = APIRouter(prefix="/api")
router.include_router(auth)