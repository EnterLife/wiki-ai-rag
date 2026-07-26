from dataclasses import dataclass
from contextvars import ContextVar


@dataclass(frozen=True)
class AccessContext:
    subject: str
    groups: frozenset[str] = frozenset()
    is_admin: bool = False
    is_system: bool = False

    @classmethod
    def system(cls) -> "AccessContext":
        return cls(subject="system", is_admin=True, is_system=True)

    def can_access_source(self, source: dict) -> bool:
        if self.is_admin or self.is_system:
            return True
        access_groups = frozenset(source.get("access_groups") or [])
        return not access_groups or bool(self.groups.intersection(access_groups))


SYSTEM_ACCESS_CONTEXT = AccessContext.system()
_current_access_context: ContextVar[AccessContext] = ContextVar(
    "current_access_context",
    default=SYSTEM_ACCESS_CONTEXT,
)


def remember_access_context(access_context: AccessContext) -> AccessContext:
    _current_access_context.set(access_context)
    return access_context


def current_access_context() -> AccessContext:
    return _current_access_context.get()
