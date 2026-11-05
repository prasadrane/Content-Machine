"""Framework-independent workflow domain failures.

Routes serialize these failures in a later packet. Nothing here depends on
FastAPI or on a request/response type, so services can raise the same error.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class WorkflowError(Exception):
    """A workflow failure with stable HTTP metadata.

    ``current`` optionally carries the acknowledged server state for conflict
    responses (for example revision, stage and active approval fields). It is
    copied so later mutation cannot rewrite the raised error.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        detail: str,
        *,
        current: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail
        self.current = dict(current) if current is not None else None


__all__ = ["WorkflowError"]
