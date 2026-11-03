from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Actor:
    """Who performs an operation: account id (None for the system) and role name."""
    role: str
    account_id: Optional[int] = None


SYSTEM = Actor(role="SYSTEM")
