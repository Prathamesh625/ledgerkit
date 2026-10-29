from sqlalchemy.orm import DeclarativeBase
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models.user import User  # noqa: F401

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# Import all models here so Alembic autogenerate can discover them.
# from app.models.user import User  # noqa: E402, F401
from app.models.user import User