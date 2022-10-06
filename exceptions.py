class NotSendingMessageError(Exception):
    """Ошибка отправки сообщения в Telegram-чат."""

    pass


class RequestError(Exception):
    """Сбой при запросе к эндпоинту."""

    pass


class ServerError(Exception):
    """Cервер недоступен."""

    pass


class UknownStatusError(Exception):
    """Статус работы неизвестен."""

    pass


class PropertyError(Exception):
    """Объект response не имет атрибута json."""

    pass
