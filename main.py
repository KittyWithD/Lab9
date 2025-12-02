# import requests
#
# API_URL = 'https://api-metrika.yandex.ru/stat/v1/data.csv'
# API_token = 'y0__xDU2OvzAhiK9zsgqoCAthVD4yj2ma3d_pjyXQlbtX6gM0xbfg'
# params = {
#
#     'date1': '6daysAgo',
#     'date2': 'today',
#     'id': 105562414,
#     'metrics': 'ym:s:visits,ym:s:users',
#     'dimensions': 'ym:s:TrafficSource',
#     'limit': 100
# }
# r = requests.get(API_URL, params=params, headers={'Authorization': API_token})
#
# print(r.text)

import requests
import csv
import argparse
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import sys

load_dotenv()
API_URL = 'https://api-metrika.yandex.net/stat/v1/data'
API_TOKEN = os.getenv('API_TOKEN')
COUNTER_ID = int(os.getenv('COUNTER_ID'))

def validate_config():
    if not API_TOKEN:
        raise ValueError("Не найден YANDEX_METRIKA_OAUTH_TOKEN в файле .env")
    if not COUNTER_ID:
        raise ValueError("Не найден YANDEX_METRIKA_COUNTER_ID в файле .env")

    try:
        counter_id_int = int(COUNTER_ID)
        return counter_id_int
    except ValueError:
        raise ValueError("COUNTER_ID должен быть числом")

def validate_dates(date_from, date_to):
    try:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')

        if date_from_obj > date_to_obj:
            raise ValueError("Дата 'с' не может быть позже даты 'по'")

        if date_to_obj > datetime.now():
            raise ValueError("Дата 'по' не может быть в будущем")

        # Проверяем, что период не превышает 2 года (ограничение API)
        if (date_to_obj - date_from_obj).days > 730:
            raise ValueError("Период не может превышать 2 года")

        return True

    except ValueError as e:
        if "time data" in str(e):
            raise ValueError("Неверный формат даты. Используйте формат YYYY-MM-DD")
        else:
            raise e

def get_metrika_report(date_from, date_to):
    params = {
        'date1': date_from,
        'date2': date_to,
        'id': COUNTER_ID,
        'metrics': 'ym:s:visits,ym:s:pageviews,ym:s:users',
        'dimensions': 'ym:s:date',
        'sort': 'ym:s:date',
        'limit': 1000
    }

    headers = {
        'Authorization': f'OAuth {API_TOKEN}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(API_URL, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        if 'errors' in data and data['errors']:
            error_message = data['errors'][0].get('message', 'Неизвестная ошибка API')
            raise Exception(f"Ошибка API Яндекс.Метрики: {error_message}")

        return data

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            raise Exception("Ошибка авторизации: неверный OAuth токен")
        elif response.status_code == 403:
            raise Exception("Ошибка доступа: нет прав доступа к счётчику")
        elif response.status_code == 400:
            error_data = response.json()
            error_message = error_data.get('message', 'Некорректный запрос')
            raise Exception(f"Ошибка запроса: {error_message}")
        else:
            raise Exception(f"HTTP ошибка {response.status_code}: {str(e)}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка соединения: {str(e)}")

def print_table(data):
    if not data or 'data' not in data or not data['data']:
        print("Нет данных для отображения")
        return

    print(f"{'Дата':<12} {'Визиты':<10} {'Просмотры':<12} {'Посетители':<12}")

    total_visits = 0
    total_pageviews = 0
    total_users = 0

    for row in data['data']:
        date = row['dimensions'][0]['name']
        visits = row['metrics'][0]
        pageviews = row['metrics'][1]
        users = row['metrics'][2]

        total_visits += visits
        total_pageviews += pageviews
        total_users += users

        print(f"{date:<12} {visits:<10} {pageviews:<12} {users:<12}")
    print(f"{'ИТОГО':<12} {total_visits:<10} {total_pageviews:<12} {total_users:<12}")

def save_to_csv(data, filename=None):
    if not data or 'data' not in data or not data['data']:
        print("Нет данных для сохранения")
        return

    if not filename:
        filename = f"metrika_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Заголовок
            writer.writerow(['Дата', 'Визиты', 'Просмотры', 'Посетители'])

            # Данные
            for row in data['data']:
                date = row['dimensions'][0]['name']
                visits = row['metrics'][0]
                pageviews = row['metrics'][1]
                users = row['metrics'][2]

                writer.writerow([date, visits, pageviews, users])

        print(f"\nДанные сохранены в файл: {filename}")

    except Exception as e:
        raise Exception(f"Ошибка при сохранении в CSV: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Получение отчёта из Яндекс.Метрики')
    parser.add_argument('--date_from', type=str, help='Дата начала периода (YYYY-MM-DD)')
    parser.add_argument('--date_to', type=str, help='Дата окончания периода (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, help='Имя файла для сохранения CSV')

    args = parser.parse_args()

    try:
        counter_id = validate_config()
        if not args.date_from or not args.date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')
            date_from = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
        else:
            date_from = args.date_from
            date_to = args.date_to

        validate_dates(date_from, date_to)
        print(f"Получение данных за период: {date_from} - {date_to}")
        print(f"Счётчик: {counter_id}")

        data = get_metrika_report(date_from, date_to)
        print_table(data)
        save_to_csv(data, args.output)

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()