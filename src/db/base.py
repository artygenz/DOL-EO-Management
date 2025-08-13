# app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# Import models so Base.metadata is populated for Alembic
from src.models.executive_order import ExecutiveOrder  # noqa: F401
from src.models.user import User  # noqa: F401
from src.models.task import Task  # noqa: F401
from src.models.email_log import EmailLog  # noqa: F401
from src.models.attachment import Attachment  # noqa: F401
from src.models.task_log import TaskLog  # noqa: F401
from src.models.task_confirmation import TaskConfirmation  # noqa: F401
from src.models.auth_token import AuthToken  # noqa: F401