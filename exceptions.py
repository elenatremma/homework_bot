class RequestError(Exception):
    """Сбой при запросе к эндпоинту."""

    pass


class ServerError(Exception):
    """Cервер недоступен."""

    pass


class UknownStatusError(Exception):
    """Статус работы неизвестен."""

    pass
