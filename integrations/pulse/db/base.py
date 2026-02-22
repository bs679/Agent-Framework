"""SQLAlchemy declarative base shared across all Pulse models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
