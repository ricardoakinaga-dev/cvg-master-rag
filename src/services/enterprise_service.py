"""
Enterprise session and tenancy contracts for the Phase 3 foundation.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from services.admin_service import (
    can_access_tenant,
    get_accessible_tenants,
    get_tenant,
    get_user,
    get_user_by_email,
    list_tenants,
    verify_password,
)
from services.enterprise_store import (
    load_recovery_state,
    load_session_state,
    save_recovery_state,
    save_session_state,
)
from core.config import SESSION_TTL_HOURS

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["read", "write", "admin", "tenant:switch", "audit:view"],
    "operator": ["read", "write", "tenant:switch", "audit:view"],
    "viewer": ["read", "tenant:switch"],
}

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _default_tenant() -> dict:
    tenant = get_tenant("default")
    if tenant is not None:
        return tenant
    tenants = list_tenants()
    if tenants:
        return tenants[0]
    return {
        "tenant_id": "default",
        "name": "Workspace Principal",
        "workspace_id": "default",
        "plan": "enterprise",
        "status": "active",
        "document_count": 0,
    }


def _active_tenant_for_user(user: dict, tenant_id: str | None = None) -> dict:
    accessible = get_accessible_tenants(user)
    if not accessible:
        return _default_tenant()
    if tenant_id:
        for tenant in accessible:
            if tenant["tenant_id"] == tenant_id:
                return tenant
    return accessible[0]


def _build_authenticated_session(user: dict, tenant_id: str, session_token: str, expires_at: str) -> dict:
    normalized_role = user["role"] if user["role"] in ROLE_PERMISSIONS else "viewer"
    permissions = ROLE_PERMISSIONS.get(normalized_role, ROLE_PERMISSIONS["viewer"])
    active_tenant = _active_tenant_for_user(user, tenant_id)
    return {
        "authenticated": True,
        "session_state": "active",
        "expires_at": expires_at,
        "session_token": session_token,
        "user": {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
            "role": normalized_role,
            "permissions": permissions,
        },
        "active_tenant": active_tenant,
        "available_tenants": get_accessible_tenants(user),
        "message": "Sessão enterprise carregada com sucesso",
    }


def bootstrap_session() -> dict:
    tenant = _default_tenant()
    return {
        "authenticated": False,
        "session_state": "anonymous",
        "expires_at": None,
        "session_token": None,
        "user": {
            "user_id": "anonymous",
            "name": "Visitante",
            "email": "",
            "role": "viewer",
            "permissions": [],
        },
        "active_tenant": tenant,
        "available_tenants": list_tenants(),
        "message": "Sessão enterprise pronta para login.",
    }


def _load_sessions() -> dict[str, dict]:
    return load_session_state().get("sessions", {})


def _save_sessions(sessions: dict[str, dict]) -> None:
    save_session_state({"sessions": sessions})


def _load_recovery_requests() -> list[dict]:
    return load_recovery_state().get("requests", [])


def _save_recovery_requests(requests: list[dict]) -> None:
    save_recovery_state({"requests": requests})


def _persist_session(user: dict, tenant_id: str) -> dict:
    sessions = _load_sessions()
    session_token = secrets.token_urlsafe(32)
    expires_at = _to_iso(_utc_now() + timedelta(hours=SESSION_TTL_HOURS))
    sessions[session_token] = {
        "session_token": session_token,
        "user_id": user["user_id"],
        "tenant_id": tenant_id,
        "expires_at": expires_at,
        "created_at": _to_iso(_utc_now()),
    }
    _save_sessions(sessions)
    return _build_authenticated_session(user, tenant_id, session_token, expires_at)


def _prune_expired_sessions(sessions: dict[str, dict]) -> dict[str, dict]:
    now = _utc_now()
    active_sessions: dict[str, dict] = {}
    for token, payload in sessions.items():
        expires_at = payload.get("expires_at")
        if not expires_at:
            continue
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if expires_dt > now:
            active_sessions[token] = payload
    if active_sessions != sessions:
        _save_sessions(active_sessions)
    return active_sessions


def extract_session_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_session(session_token: str | None) -> dict:
    if not session_token:
        return bootstrap_session()
    sessions = _prune_expired_sessions(_load_sessions())
    record = sessions.get(session_token)
    if not record:
        expired = bootstrap_session()
        expired["session_state"] = "expired"
        expired["message"] = "Sessão inválida ou expirada. Faça login novamente."
        return expired
    user = get_user(record["user_id"])
    if not user or user.get("status") != "active":
        sessions.pop(session_token, None)
        _save_sessions(sessions)
        expired = bootstrap_session()
        expired["session_state"] = "expired"
        expired["message"] = "Sessão revogada. Faça login novamente."
        return expired

    # Invalidate session if password was changed after session was created
    password_changed_at = user.get("password_changed_at")
    if password_changed_at:
        try:
            session_created = datetime.fromisoformat(record.get("created_at", "").replace("Z", "+00:00"))
            pw_changed = datetime.fromisoformat(password_changed_at.replace("Z", "+00:00"))
            if session_created < pw_changed:
                sessions.pop(session_token, None)
                _save_sessions(sessions)
                expired = bootstrap_session()
                expired["session_state"] = "expired"
                expired["message"] = "Sessão revogada. Credenciais alteradas. Faça login novamente."
                return expired
        except (ValueError, TypeError):
            pass  # Malformed timestamp — skip check

    # Invalidate session if status was changed after session was created
    status_changed_at = user.get("status_changed_at")
    if status_changed_at:
        try:
            session_created = datetime.fromisoformat(record.get("created_at", "").replace("Z", "+00:00"))
            status_changed = datetime.fromisoformat(status_changed_at.replace("Z", "+00:00"))
            if session_created < status_changed:
                sessions.pop(session_token, None)
                _save_sessions(sessions)
                expired = bootstrap_session()
                expired["session_state"] = "expired"
                expired["message"] = "Sessão revogada. Status alterado. Faça login novamente."
                return expired
        except (ValueError, TypeError):
            pass

    tenant_id = record.get("tenant_id") or user["tenant_id"]
    if not can_access_tenant(user, tenant_id):
        tenant_id = user["tenant_id"]
    return _build_authenticated_session(user, tenant_id, session_token, record["expires_at"])


def login(email: str, password: str, tenant_id: str | None = None) -> dict:
    user = get_user_by_email(email)
    if not user:
        raise ValueError("invalid_credentials")
    if user.get("status") != "active":
        raise ValueError("inactive_user")
    if not verify_password(user, password):
        raise ValueError("invalid_credentials")
    requested_tenant = tenant_id or user["tenant_id"]
    if not can_access_tenant(user, requested_tenant):
        raise PermissionError(f"tenant_forbidden:{requested_tenant}")
    return _persist_session(user, requested_tenant)


def logout(session_token: str | None) -> None:
    if not session_token:
        return
    sessions = _load_sessions()
    if sessions.pop(session_token, None) is not None:
        _save_sessions(sessions)


def switch_tenant(session_token: str | None, tenant_id: str) -> dict:
    if not session_token:
        raise PermissionError("missing_session")
    sessions = _prune_expired_sessions(_load_sessions())
    record = sessions.get(session_token)
    if not record:
        raise PermissionError("missing_session")
    current = get_session(session_token)
    if not current.get("authenticated"):
        raise PermissionError("missing_session")
    user = get_user_by_email(current["user"]["email"])
    if not user or not can_access_tenant(user, tenant_id):
        raise PermissionError(f"tenant_forbidden:{tenant_id}")
    record["tenant_id"] = tenant_id
    sessions[session_token] = record
    _save_sessions(sessions)
    return get_session(session_token)


def queue_recovery(email: str, tenant_id: str | None = None, reason: str | None = None) -> dict:
    normalized_email = email.strip().lower()
    target_tenant = (tenant_id or "default").strip() or "default"
    detail = reason.strip() if reason and reason.strip() else "sem motivo informado"
    now = _to_iso(_utc_now())
    requests = _load_recovery_requests()
    user = get_user_by_email(normalized_email)
    tenant = get_tenant(target_tenant)

    existing = next(
        (
            item
            for item in requests
            if item.get("email") == normalized_email
            and item.get("tenant_id") == target_tenant
            and item.get("status") == "queued"
        ),
        None,
    )

    if existing is not None:
        existing["reason"] = detail
        existing["updated_at"] = now
        existing["attempts"] = int(existing.get("attempts", 1)) + 1
        existing["user_exists"] = user is not None
        existing["tenant_exists"] = tenant is not None
        recovery_id = existing["recovery_id"]
    else:
        recovery_id = f"recovery_{secrets.token_hex(8)}"
        requests.append(
            {
                "recovery_id": recovery_id,
                "email": normalized_email,
                "tenant_id": target_tenant,
                "reason": detail,
                "status": "queued",
                "attempts": 1,
                "created_at": now,
                "updated_at": now,
                "user_exists": user is not None,
                "tenant_exists": tenant is not None,
                "user_id": user.get("user_id") if user else None,
            }
        )

    _save_recovery_requests(requests)
    return {
        "status": "queued",
        "message": (
            f"Solicitação de recuperação registrada para {normalized_email} "
            f"no tenant {target_tenant}. Protocolo: {recovery_id}."
        ),
    }
