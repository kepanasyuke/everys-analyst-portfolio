"""Доменные ошибки приложения офисины и проверки-утверждения."""

from __future__ import annotations


class OfficineError(Exception):
    """Ошибка бизнес-правила: несёт HTTP-статус и сообщение на языке пользователя."""

    def __init__(self, status: int, message: str) -> None:
        self.status, self.message = status, message
        super().__init__(message)


def fail(status: int, message: str) -> None:
    raise OfficineError(status, message)


def require(condition: bool, message: str, status: int = 409) -> None:
    return None if condition else fail(status, message)
