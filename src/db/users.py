# src/db/users.py
from __future__ import annotations

import uuid
from typing import Iterable, List
from sqlalchemy import select
from src.db.session import get_engine, get_session_maker
from src.models.user import User

SessionLocal = get_session_maker(get_engine())


def create_user(name: str, email: str, role: str, org_role: str | None = None) -> User:
    from src.core.auth import hash_password
    
    with SessionLocal() as db:
        user = User(
            name=name, 
            email=email, 
            role=role, 
            org_role=org_role, 
            password_hash=hash_password("Lumen@2025"),  # Default password
            is_active=True
        )
        db.add(user)
        db.commit(); db.refresh(user)
        return user


def create_users_bulk(users: Iterable[dict]) -> List[User]:
    """
    users: iterable of dicts with keys: name, email, role, org_role(optional)
    """
    from src.core.auth import hash_password
    
    created: List[User] = []
    with SessionLocal() as db:
        for item in users:
            user = User(
                name=item.get("name"),
                email=item.get("email"),
                role=item.get("role", "executor"),
                org_role=item.get("org_role"),
                password_hash=hash_password("Lumen@2025"),  # Default password
                is_active=True,
            )
            db.add(user)
            created.append(user)
        db.commit()
        for u in created:
            db.refresh(u)
    return created


def build_roles_with_members_text() -> str:
    """Build roles-with-members text for LLM assignment from DB users."""
    with SessionLocal() as db:
        rows = db.execute(select(User.org_role, User.name).where(User.is_active == True)).all()  # noqa: E712
    role_to_members: dict[str, list[str]] = {}
    for org_role, name in rows:
        if not org_role or not name:
            continue
        role_to_members.setdefault(org_role, []).append(name)
    parts: list[str] = []
    for role, members in role_to_members.items():
        parts.append(role)
        for idx, m in enumerate(members, start=1):
            parts.append(f"{idx}. {m}")
        parts.append("")
    return "\n".join(parts).strip()


def resolve_assignee_name_to_id(assignee_name: str | None) -> uuid.UUID | None:
    """Resolve assignee name to user ID for task assignment."""
    if not assignee_name:
        return None
    with SessionLocal() as db:
        # Try exact name match first
        user = db.execute(select(User.id).where(User.name == assignee_name, User.is_active == True)).scalar_one_or_none()  # noqa: E712
        if user:
            return user
        # Try case-insensitive match
        user = db.execute(select(User.id).where(User.name.ilike(assignee_name), User.is_active == True)).scalar_one_or_none()  # noqa: E712
        if user:
            return user
        # Try partial name match
        user = db.execute(select(User.id).where(User.name.ilike(f"%{assignee_name}%"), User.is_active == True)).scalar_one_or_none()  # noqa: E712
        return user 