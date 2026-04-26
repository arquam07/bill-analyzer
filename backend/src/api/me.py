from fastapi import APIRouter, Depends

from src.api.deps import get_current_user
from src.models.user import User
from src.schemas.auth import UserResponse

router = APIRouter(tags=["me"])


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
