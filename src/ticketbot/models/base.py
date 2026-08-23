from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every TicketBot ORM model.

    `Base.metadata` is what Alembic autogenerates migrations against, so every
    model module must be imported before Alembic inspects it (see models/__init__.py).
    """
