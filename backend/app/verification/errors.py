from __future__ import annotations

class VerificationError(Exception):
    def __init__(
        self, 
        code: str, 
        message: str, 
        field: str | None = None, 
        details: dict | None = None
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "details": self.details,
        }
