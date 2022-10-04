import logging
import sys
import os
import requests
import telegram
import time

from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import RequestError, ServerError, UknownStatusError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
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
        logger.info('Сообщение отправлено')
    except Exception:
        logger.error('Ошибка отправки сообщения')


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
    except Exception as e:
        logger.error('Сбой при запросе к эндпоинту')
        raise RequestError('Сбой при запросе к эндпоинту') from e
    response = requests.get(**request_content)
    if response.status_code != HTTPStatus.OK:
        logger.error('Cервер недоступен')
        raise ServerError('Cервер недоступен')

    return response.json()


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        logger.error('Данные в виде словаря отсутствуют')
        raise TypeError('Данные в виде словаря отсутствуют')
    if type(response['homeworks']) is not list:
        logger.error('В словаре homeworks отсутствуют данные в виде списка')
        raise TypeError('В словаре homeworks отсутствуют данные в виде списка')
    try:
        homework_list = response['homeworks']
    except KeyError as e:
        logger.error('Ответ API не содержит ключ homeworks')
        raise KeyError('Ответ API не содержит ключ homeworks') from e
    try:
        homework = homework_list[0]
    except IndexError as e:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст') from e

    return homework


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе ее статус."""
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
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(f'Статус работы {homework_status} неизвестен')
        raise UknownStatusError(f'Статус работы {homework_status} неизвестен')
    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):

        return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Отсутствуе(-ю)т переменная(-ые) окружения. Выход из системы.'
        )
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    intermediate_status = 'reviewing'

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            hw_status = parse_status(homework)

            if hw_status != intermediate_status:
                send_message(bot, hw_status)
            logger.info('Статус работы изменился')
            time.sleep(RETRY_TIME)
        except Exception as e:
            error_message = f'Сбой в работе программы: {e}'
            logging.error(error_message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
