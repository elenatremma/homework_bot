import logging
import sys
import os
import requests
import telegram
import time

from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import (
    NotSendingMessageError, RequestError, ServerError,
    UknownStatusError, PropertyError,
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправляет сообщения в Telegram-чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено')
    except NotSendingMessageError as e:
        raise NotSendingMessageError(
            'Ошибка отправки сообщения в Telegram-чат'
        )from e


def get_api_answer(current_timestamp: int) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса YaP."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        request_content = {
            'url': ENDPOINT,
            'params': params,
            'headers': HEADERS,
        }
        response = requests.get(**request_content)
    except RequestError as e:
        logger.error('Сбой при запросе к эндпоинту')
        raise RequestError('Сбой при запросе к эндпоинту') from e
    if response.status_code != HTTPStatus.OK:
        logger.error('Cервер недоступен')
        raise ServerError('Cервер недоступен')
    if not hasattr(response, 'json'):
        logger.error('Объект response не имет атрибута json')
        raise PropertyError('Объект response не имет атрибута json')

    return response.json()


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logger.error('Данные в виде словаря отсутствуют')
        raise TypeError('Данные в виде словаря отсутствуют')
    if not isinstance(response['homeworks'], list):
        logger.error('В словаре homeworks отсутствуют данные в виде списка')
        raise TypeError('В словаре homeworks отсутствуют данные в виде списка')
    try:
        homeworks = response['homeworks']
    except KeyError as e:
        logger.error('Ответ API не содержит ключ homeworks')
        raise KeyError('Ответ API не содержит ключ homeworks') from e

    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе ее статус."""
    if len(homework) == 0:
        logger.debug('Список домашних работ пуст')
    if 'homework_name' not in homework:
        logger.error(
            'Ключ homework_name отсутствует во вложенном словаре homework'
        )
        raise KeyError(
            'Ключ homework_name отсутствует во вложенном словаре homework'
        )
    if 'status' not in homework:
        logger.error('Ключ status отсутствует во вложенном словаре homework')
        raise KeyError(
            'Ключ status отсутствует во вложенном словаре homework'
        )
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error(f'Статус работы {homework_status} неизвестен')
        raise UknownStatusError(f'Статус работы {homework_status} неизвестен')
    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Отсутствуе(-ю)т переменная(-ые) окружения. Выход из системы.'
        )
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    last_hw_status = ''
    last_error_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if last_hw_status != message:
                    last_hw_status = message
                    send_message(bot, message)
            current_timestamp = response.get('current_date')
        except NotSendingMessageError:
            message = 'Ошибка отправки сообщения в Telegram-чат'
            logging.error(message, exc_info=True)
        except Exception as e:
            error_message = f'Сбой в работе программы: {e}'
            logging.error(error_message, exc_info=True)
            if last_error_message != error_message:
                last_error_message = error_message
                send_message(bot, error_message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
