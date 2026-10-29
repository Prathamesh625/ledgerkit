from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.api.v1.deps import DbSession
from app.schemas.user import Token, UserCreate, UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(data: UserCreate, db: DbSession):
    service = AuthService(db)
    user = await service.register(data)
    return user


@router.post("/login", response_model=Token)
async def login(db: DbSession, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    service = AuthService(db)
    return await service.authenticate(form_data.username, form_data.password)


