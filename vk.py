import requests
from datetime import datetime
import time

class VKPostAnalyzer:
    def __init__(self, access_token, post_url):
        self.access_token = access_token
        self.version = '5.199'
        parts = post_url.split('wall')[-1]
        if '_' in parts:
            owner_id, post_id = parts.split('_')
            self.owner_id = int(owner_id)
            self.post_id = int(post_id)
        else:
            raise ValueError("Некорректный URL поста")

    def _make_api_request(self, method, params):
        params['access_token'] = self.access_token
        params['v'] = self.version
        response = requests.get(
            f'https://api.vk.com/method/{method}',
            params=params
        )
        if response.status_code == 200:
            data = response.json()
            if 'error' in data:
                print(f"Ошибка API: {data['error']['error_msg']}")
                return None
            return data['response']
        return None

    def get_likers(self):
        likers = []
        offset = 0
        count = 100
        print("Сбор списка лайкнувших...")
        while True:
            response = self._make_api_request('likes.getList', {
                'type': 'post',
                'owner_id': self.owner_id,
                'item_id': self.post_id,
                'offset': offset,
                'count': count,
                'filter': 'likes'
            })
            if not response or 'items' not in response:
                break
            users = response['items']
            if not users:
                break
            likers.extend(users)
            offset += count
            time.sleep(0.1)
            if len(users) < count:
                break
        print(f"Найдено {len(likers)} лайкнувших")
        return likers

    def get_users_info(self, user_ids):
        if not user_ids:
            return []
        users_info = []
        for i in range(0, len(user_ids), 1000):
            batch = user_ids[i:i + 1000]
            response = self._make_api_request('users.get', {
                'user_ids': ','.join(map(str, batch)),
                'fields': 'sex,bdate'
            })
            if response:
                users_info.extend(response)
            time.sleep(0.1)
        return users_info

    def analyze_age(self, bdate_str):
        if not bdate_str or bdate_str.count('.') < 2:
            return 'unknown'
        try:
            bdate_parts = bdate_str.split('.')
            if len(bdate_parts) == 3:
                birth_year = int(bdate_parts[2])
                current_year = datetime.now().year
                age = current_year - birth_year
                if age <= 18:
                    return '0-18'
                elif 19 <= age <= 35:
                    return '19-35'
                elif 36 <= age <= 50:
                    return '36-50'
                else:
                    return '>50'
        except (ValueError, IndexError):
            pass
        return 'unknown'
    def analyze_sex(self, sex_id):
        if sex_id == 2:
            return 'male'
        elif sex_id == 1:
            return 'female'
        else:
            return 'unknown'

    def build_statistics(self, users_info):
        stats = {
            "post_id": self.post_id,
            "age": {
                "0-18": 0,
                "19-35": 0,
                "36-50": 0,
                ">50": 0,
                "unknown": 0
            },
            "sex": {
                "male": 0,
                "female": 0,
                "unknown": 0
            }
        }
        for user in users_info:
            bdate = user.get('bdate', '')
            age_group = self.analyze_age(bdate)
            stats['age'][age_group] += 1
            sex = user.get('sex', 0)
            sex_group = self.analyze_sex(sex)
            stats['sex'][sex_group] += 1
        return stats

    def run_analysis(self):
        print(f"Анализ поста {self.owner_id}_{self.post_id}")
        likers = self.get_likers()
        if not likers:
            print("Пост не найден или нет лайков")
            return None
        users_info = self.get_users_info(likers)
        stats = self.build_statistics(users_info)
        return stats

def print_statistics(stats):
    print(f"Статистика для поста ID: {stats['post_id']}")

    print("\nВозрастная статистика:")
    total_age = sum(stats['age'].values())
    for group, count in stats['age'].items():
        percentage = (count / total_age * 100) if total_age > 0 else 0
        print(f"{group:10} | {count:5} | {percentage:6.2f}%")

    print("\nСтатистика по полу:")
    total_sex = sum(stats['sex'].values())
    for sex, count in stats['sex'].items():
        percentage = (count / total_sex * 100) if total_sex > 0 else 0
        print(f"{sex:10} | {count:5} | {percentage:6.2f}%")

if __name__ == "__main__":
    ACCESS_TOKEN = 'vk1.a.B_gkUUu3uEE055HbRTP9LPj3WjWCiFqR2DePJ_1Ymk7GK5us4yGXkJYRBu97Hu4TEDSH3deapF6dFzjG6HtdPtKlyMV4qoTLkNNjJ9upkdR1loyu_egWupcJDGdUsbi9FszaminTIVLMYcfosiY4QTPoJprH8uW-CvskddaJrBRFzeftTKmM8E-immb_8XA2vc0Yd84frTRLV-lwZ5roTg'
    POST_URL = 'https://vk.com/wall-84648738_222312'

    analyzer = VKPostAnalyzer(ACCESS_TOKEN, POST_URL)
    statistics = analyzer.run_analysis()
    if statistics:
        print_statistics(statistics)
        print(statistics)