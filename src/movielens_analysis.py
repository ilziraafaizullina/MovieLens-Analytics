import os
import sys
import re

import json
from datetime import datetime
from collections import Counter
from functools import reduce
import urllib.request
import urllib.error
from html import unescape
from bs4 import BeautifulSoup


class Ratings:
    def __init__(self, path_to_the_file):
        self.path = path_to_the_file
        self.data = [] # для хранения данных о рейтингах
        self.movies_data = {}  # соответствия movieId -> название фильма

        self.movies = self.Movies(self)
        self.users = self.Users(self)


        with open(path_to_the_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # header = lines[0].strip().split(',')

            for line in lines[1:1001]:
                parts = line.strip().split(',')

                self.data.append({
                    'userId': int(parts[0]),
                    'movieId': int(parts[1]),
                    'rating': float(parts[2]),
                    'timestamp': int(parts[3])
                })

        movies_path = os.path.join(os.path.dirname(path_to_the_file), 'movies.csv')
        with open(movies_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:]:
                parts = self._parse_csv_line(line.strip())

                if len(parts) >= 2:
                    movie_id = int(parts[0])
                    title = parts[1]
                    self.movies_data[movie_id] = title

    def _parse_csv_line(self, line):
        result = []
        current = ''
        in_quotes = False

        for char in line:
            if char == '"':
                in_quotes = not in_quotes  # перекл внутри или вне ковычек
            elif char == ',' and not in_quotes:
                result.append(current)
                current = ''
            else:
                current += char

        result.append(current)
        return result

    class Movies:
        def __init__(self, ratings_instance):
            self.ratings = ratings_instance

        def dist_by_year(self):
            year_counts = {}
            for record in self.ratings.data:
                year = datetime.fromtimestamp(record['timestamp']).year
                year_counts[year] = year_counts.get(year, 0) + 1
            return dict(sorted(year_counts.items()))

        def dist_by_rating(self):
            rating_counts = {}
            for record in self.ratings.data:
                rating = record['rating']
                rating_counts[rating] = rating_counts.get(rating, 0) + 1
            return dict(sorted(rating_counts.items()))

        def top_by_num_of_ratings(self, n):
            movie_counts = {}
            for record in self.ratings.data:
                movie_id = record['movieId']
                title = self.ratings.movies_data.get(movie_id, f"Movie {movie_id}")
                movie_counts[title] = movie_counts.get(title, 0) + 1
            sorted_movies = sorted(movie_counts.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_movies[:n])

        def top_by_ratings(self, n, metric='average'):
            movie_ratings = {}  # {название: список_оценок}

            # Группируем все оценки по фильмам
            for record in self.ratings.data:
                movie_id = record['movieId']
                title = self.ratings.movies_data.get(movie_id, f"Movie {movie_id}")

                # если фильма еще нет в списке
                if title not in movie_ratings:
                    movie_ratings[title] = []

                movie_ratings[title].append(record['rating'])

            movie_metrics = {}  # {название: значение_метрики}
            for title, ratings in movie_ratings.items():
                if metric == 'average':
                    value = sum(ratings) / len(ratings)
                elif metric == 'median':
                    sorted_ratings = sorted(ratings)
                    n_ratings = len(sorted_ratings)
                    if n_ratings % 2 == 0:
                        value = (sorted_ratings[n_ratings // 2 - 1] + sorted_ratings[n_ratings // 2]) / 2
                    else:
                        value = sorted_ratings[n_ratings // 2]
                else:
                    raise 'Укажите average/median'
                movie_metrics[title] = round(value, 2)



            sorted_movies = sorted(movie_metrics.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_movies[:n])

        def top_controversial(self, n):
            movie_ratings = {} # {название: список_оценок}
            for record in self.ratings.data:
                movie_id = record['movieId']
                title = self.ratings.movies_data.get(movie_id, f"Movie {movie_id}")

                if title not in movie_ratings:
                    movie_ratings[title] = []
                movie_ratings[title].append(record['rating'])

            movie_variance = {}  # {название: дисперсия}
            for title, ratings in movie_ratings.items():
                # Пропускаем фильмы с одной оценкой (нет смысла считать)
                if len(ratings) > 1:
                    mean = sum(ratings) / len(ratings)
                    variance = sum((r - mean) ** 2 for r in ratings) / len(ratings)
                    movie_variance[title] = round(variance, 2)
            sorted_movies = sorted(movie_variance.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_movies[:n])
        
        def high_rated_movies_by_year(self, threshold=4.7):
            """
            Возвращает словарь вида {год: количество фильмов с средним рейтингом >= threshold}.
            Год берётся из timestamp (год выставления оценки).
            Средний рейтинг фильма считается по всем его оценкам.
            Позволяет узнать, в каком году было больше всего фильмов с положительными оценками.
            """

            sums = {}   
            counts = {}  
            years = {}   

            for record in self.ratings.data:
                movie_id = record['movieId']
                rating = record['rating']
                year = datetime.fromtimestamp(record['timestamp']).year

                sums[movie_id] = sums.get(movie_id, 0.0) + rating
                counts[movie_id] = counts.get(movie_id, 0) + 1

                if movie_id not in years:
                    years[movie_id] = year

            year_counts = {} 

            for movie_id in counts:
                avg_rating = sums[movie_id] / counts[movie_id]
                if avg_rating >= threshold:
                    year = years[movie_id]
                    year_counts[year] = year_counts.get(year, 0) + 1

            return dict(sorted(year_counts.items()))
        
        def trend_by_year(self, movie_id):
            """
            Возвращает динамику средней оценки фильма по годам. типа в этом году фильм не зашел, а в следую
            щем зашел людям 

            Пример результата:
            {1997: 3.8, 1998: 4.1, 1999: 4.4}
            """

            rating_sums = {}
            rating_counts = {}

            for record in self.ratings.data:
                if record['movieId'] == movie_id:
                    year = datetime.fromtimestamp(record['timestamp']).year
                    rating = record['rating']

                    rating_sums[year] = rating_sums.get(year, 0.0) + rating
                    rating_counts[year] = rating_counts.get(year, 0) + 1

            yearly_average = {}
            for year in rating_sums:
                yearly_average[year] = round(rating_sums[year] / rating_counts[year], 2)

            return dict(sorted(yearly_average.items())) 

    class Users(Movies):
        def __init__(self, ratings_instance):
            super().__init__(ratings_instance)

        def dist_by_num_of_ratings(self):
            user_counts = {}  # {user_id: количество_оценок}
            for record in self.ratings.data:
                user_id = record['userId']
                user_counts[user_id] = user_counts.get(user_id, 0) + 1

            dist = {}
            for count in user_counts.values():
                dist[count] = dist.get(count, 0) + 1
            return dict(sorted(dist.items()))

        def dist_by_ratings(self, metric='average'):
            user_ratings = {}  # {user_id: список_оценок}
            for record in self.ratings.data:
                user_id = record['userId']
                if user_id not in user_ratings:
                    user_ratings[user_id] = []
                user_ratings[user_id].append(record['rating'])

            user_metrics = {}  # {user_id: значение_метрики}
            for user_id, ratings in user_ratings.items():
                if metric == 'average':
                    value = sum(ratings) / len(ratings)
                elif metric == 'median':
                    sorted_ratings = sorted(ratings)
                    n_ratings = len(sorted_ratings)
                    if n_ratings % 2 == 0:
                        value = (sorted_ratings[n_ratings // 2 - 1] + sorted_ratings[n_ratings // 2]) / 2
                    else:
                        value = sorted_ratings[n_ratings // 2]
                else:
                    raise 'Укажите average/median'
                user_metrics[user_id] = round(value, 1)

            dist = {}
            for value in user_metrics.values():
                dist[value] = dist.get(value, 0) + 1
            return dict(sorted(dist.items()))

        def top_controversial(self, n):
            user_ratings = {}  # {user_id: список_оценок}
            for record in self.ratings.data:
                user_id = record['userId']
                if user_id not in user_ratings:
                    user_ratings[user_id] = []
                user_ratings[user_id].append(record['rating'])

            user_variance = {}  # {user_id: дисперсия}
            for user_id, ratings in user_ratings.items():
                if len(ratings) > 1:
                    mean = sum(ratings) / len(ratings)
                    variance = sum((r - mean) ** 2 for r in ratings) / len(ratings)
                    user_variance[user_id] = round(variance, 2)
            sorted_users = sorted(user_variance.items(), key=lambda x: x[1], reverse=True)
            return dict(sorted_users[:n])


class Tags:
    def __init__(self, path_to_the_file):
        self.path = path_to_the_file
        self.data = []

        with open(path_to_the_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[1:1001]:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    # Обработка случая, когда тег содержит запятые:
                    # В этом случае parts будет содержать больше 4 элементов
                    self.data.append({
                        'userId': int(parts[0]),
                        'movieId': int(parts[1]),
                        # Если частей больше 4, объединяем средние элементы как тег
                        'tag': ','.join(parts[2:-1]) if len(parts) > 4 else parts[2],
                        'timestamp': int(parts[-1])
                    })
    def most_words(self, n):
        unique_tags = set(record['tag'] for record in self.data)
        tag_words = {tag: len(tag.split()) for tag in unique_tags}
        sorted_tags = sorted(tag_words.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:n])

    def longest(self, n):
        unique_tags = set(record['tag'] for record in self.data)
        sorted_tags = sorted(unique_tags, key=len, reverse=True)
        return sorted_tags[:n]

    def most_words_and_longest(self, n):
        most_words_tags = set(self.most_words(n).keys())
        longest_tags = set(self.longest(n))
        return list(most_words_tags & longest_tags)

    def most_popular(self, n):
        tag_counts = {}  # для подсчёта использований
        for record in self.data:
            tag = record['tag']
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_tags[:n])

    def tags_with(self, word):
        unique_tags = set(record['tag'] for record in self.data)
        matching_tags = [tag for tag in unique_tags if word.lower() in tag.lower()]
        return sorted(matching_tags)


class Movies:
    def __init__(self, path_to_the_file):
        self.path = path_to_the_file
        self.data = []

        with open(path_to_the_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

            for line in lines[1:1001]:
                parts = self._parse_csv_line(line.strip())

                if len(parts) >= 3:
                    self.data.append({
                        'movieId': int(parts[0]),
                        'title': parts[1],
                        # Разбиваем жанры по "|"
                        'genres': parts[2].split('|') if parts[2] != '(no genres listed)' else []
                    })

    def _parse_csv_line(self, line):
        result = []
        current = ''
        in_quotes = False

        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                result.append(current)
                current = ''
            else:
                current += char
        result.append(current)
        return result

    def _extract_year(self, title):
        match = re.search(r'\((\d{4})\)', title) # 4 цифры в скобках
        if match:
            return int(match.group(1))
        return None

    def dist_by_release(self):
        year_counts = {}
        for record in self.data:
            year = self._extract_year(record['title'])
            if year:  # пропускаем фильмы без года
                year_counts[year] = year_counts.get(year, 0) + 1
        sorted_years = sorted(year_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_years)

    def dist_by_genres(self):
        genre_counts = {}
        for record in self.data:
            for genre in record['genres']:
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_genres)

    def most_genres(self, n):
        movie_genres = {record['title']: len(record['genres']) for record in self.data}
        sorted_movies = sorted(movie_genres.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_movies[:n])


class Links:
    def __init__(self, path_to_the_file):
        self.path = path_to_the_file
        self.data = []
        self.movies_data = {}
        self._imdb_cache = {}
        self._movie_id_to_imdb = {}

        with open(path_to_the_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

            for line in lines[1:1001]:
                parts = line.strip().split(',')

                if len(parts) >= 3:
                    movie_id = int(parts[0])
                    imdb_id = parts[1]

                    self.data.append({
                        'movieId': movie_id,
                        'imdbId': imdb_id,
                        'tmdbId': parts[2] if parts[2] else None
                    })

                    self._movie_id_to_imdb[movie_id] = imdb_id

        movies_path = os.path.join(os.path.dirname(path_to_the_file), 'movies.csv')
        if os.path.exists(movies_path):
            with open(movies_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[1:]:
                    parts = self._parse_csv_line(line.strip())
                    if len(parts) >= 2:
                        movie_id = int(parts[0])
                        title = parts[1]
                        self.movies_data[movie_id] = title

    def _parse_csv_line(self, line):
        result = []
        current = ''
        in_quotes = False

        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                result.append(current)
                current = ''
            else:
                current += char
        result.append(current)
        return result

    def _get_imdb_page(self, imdb_id):
        if imdb_id in self._imdb_cache:
            return self._imdb_cache[imdb_id]

        url = f"https://www.imdb.com/title/tt{imdb_id}/"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        try:
            import ssl
            import gzip

            context = ssl._create_unverified_context()
            request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request, timeout=15, context=context) as response:
                content = response.read()

                content_encoding = response.headers.get('Content-Encoding', '').lower()
                if content_encoding == 'gzip':
                    content = gzip.decompress(content)
                elif content_encoding == 'deflate':
                    import zlib
                    content = zlib.decompress(content)

                html = content.decode('utf-8')
                if len(html) > 1000:
                    self._imdb_cache[imdb_id] = html
                    return html
                else:
                    print(f"HTML для tt{imdb_id} слишком короткий ({len(html)} символов)")
                    return None

        except Exception as e:
            print(f"ошибка для tt{imdb_id}: {type(e).__name__}: {str(e)}")
            print(f"URL: {url}")
            return None

    def _parse_imdb_field(self, html, field):

        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        if field == 'Director':
            excluded = {'cast & crew', 'cast &amp; crew', 'full cast & crew',
                        'see full cast & crew', 'director', 'directors',
                        'see more', 'more', 'see all'}

            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    json_data = json.loads(script.string)
                    # Обрабатываем как словарь или список
                    if isinstance(json_data, dict):
                        json_data = [json_data]
                    elif not isinstance(json_data, list):
                        continue

                    for item in json_data:
                        if isinstance(item, dict) and 'director' in item:
                            director_info = item['director']
                            if isinstance(director_info, list) and len(director_info) > 0:
                                director_info = director_info[0]
                            if isinstance(director_info, dict) and 'name' in director_info:
                                director = director_info['name'].strip()
                                if director and director.lower() not in excluded and 2 < len(director) < 50:
                                    return director
                except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
                    continue

            # Ищем заголовок "Director" и следующую за ним ссылку на страницу человека
            director_headers = soup.find_all(string=re.compile(r'Director[s]?', re.I))
            for header in director_headers:
                # Ищем родительский элемент и следующую ссылку на страницу человека
                parent = header.parent
                if parent:
                    # Ищем следующую ссылку на страницу человека (/name/nm...)
                    next_link = parent.find_next('a', href=re.compile(r'/name/nm\d+'))
                    if next_link:
                        director = next_link.get_text().strip()
                        if director and director.lower() not in excluded and 2 < len(director) < 50:
                            return unescape(director)

        elif field == 'Budget':
            budget_text = soup.find(string=re.compile(r'Budget', re.I))
            if budget_text:
                parent = budget_text.parent
                while parent and parent.name != 'html':
                    text = parent.get_text()
                    match = re.search(r'\$[\d,]+', text)
                    if match:
                        return match.group(0)
                    parent = parent.parent

            # Fallback: поиск по всему тексту
            all_text = soup.get_text()
            match = re.search(r'Budget.*?(\$[\d,]+)', all_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        elif field == 'Cumulative Worldwide Gross':
            gross_text = soup.find(string=re.compile(r'Gross worldwide|Cumulative Worldwide Gross', re.I))
            if gross_text:
                parent = gross_text.parent
                while parent and parent.name != 'html':
                    text = parent.get_text()
                    match = re.search(r'\$[\d,]+', text)
                    if match:
                        return match.group(0)
                    parent = parent.parent

            all_text = soup.get_text()
            match = re.search(r'Gross worldwide.*?(\$[\d,]+)', all_text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1)

        elif field == 'Runtime':
            runtime_text = soup.find(string=re.compile(r'Runtime|Running time', re.I))
            if runtime_text:
                parent = runtime_text.parent
                while parent and parent.name != 'html':
                    text = parent.get_text()
                    # Ищем формат "X hours Y minutes" или "X h Y min"
                    match = re.search(r'(\d+)\s*(?:hours?|h)\s*(\d+)?\s*(?:minutes?|min)?', text, re.IGNORECASE)
                    if match:
                        hours = int(match.group(1))
                        minutes = int(match.group(2)) if match.group(2) else 0
                        return hours * 60 + minutes

                    # Ищем формат "X minutes" или "X min"
                    match = re.search(r'(\d+)\s*(?:minutes?|min)', text, re.IGNORECASE)
                    if match:
                        return int(match.group(1))

                    parent = parent.parent

            # Fallback: поиск по всему тексту
            all_text = soup.get_text()
            match = re.search(r'(\d+)\s*(?:hours?|h)\s*(\d+)?\s*(?:minutes?|min)?', all_text, re.IGNORECASE)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2)) if match.group(2) else 0
                return hours * 60 + minutes

            match = re.search(r'(\d+)\s*(?:minutes?|min)', all_text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _parse_budget_to_number(self, budget_str):
        if not budget_str:
            return None
        return int(budget_str.replace('$', '').replace(',', ''))

    def _get_title(self, movie_id):
        return self.movies_data.get(movie_id, f"Movie {movie_id}")

    def get_imdb(self, list_of_movies, list_of_fields):
        result = []

        for movie_id in list_of_movies:
            imdb_id = self._movie_id_to_imdb.get(movie_id)

            if imdb_id:
                html = self._get_imdb_page(imdb_id)

                row = [movie_id]

                for field in list_of_fields:
                    value = self._parse_imdb_field(html, field)
                    row.append(value)

                result.append(row)

        result.sort(key=lambda x: x[0], reverse=True)
        return result

    def top_directors(self, n, max_movies=10):
        director_counts = {}

        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            director = self._parse_imdb_field(html, 'Director')

            if director:
                director_counts[director] = director_counts.get(director, 0) + 1

        sorted_directors = sorted(director_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_directors[:n])

    def most_expensive(self, n, max_movies=10):
        movie_budgets = {}

        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            budget = self._parse_imdb_field(html, 'Budget')

            if budget:
                title = self._get_title(record['movieId'])
                movie_budgets[title] = budget

        sorted_movies = sorted(
            movie_budgets.items(),
            key=lambda x: self._parse_budget_to_number(x[1]),
            reverse=True
        )
        return dict(sorted_movies[:n])

    def most_profitable(self, n, max_movies=10):
        movie_profits = {}

        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            budget = self._parse_imdb_field(html, 'Budget')
            gross = self._parse_imdb_field(html, 'Cumulative Worldwide Gross')

            if budget and gross:
                title = self._get_title(record['movieId'])

                budget_num = self._parse_budget_to_number(budget)
                gross_num = self._parse_budget_to_number(gross)

                profit = gross_num - budget_num
                movie_profits[title] = profit

        sorted_movies = sorted(movie_profits.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_movies[:n])

    def longest(self, n, max_movies=10):
        movie_runtimes = {}

        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            runtime = self._parse_imdb_field(html, 'Runtime')

            if runtime:
                title = self._get_title(record['movieId'])
                movie_runtimes[title] = runtime

        sorted_movies = sorted(movie_runtimes.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_movies[:n])

    def top_cost_per_minute(self, n, max_movies=10):
        movie_costs = {}

        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            budget = self._parse_imdb_field(html, 'Budget')
            runtime = self._parse_imdb_field(html, 'Runtime')

            if budget and runtime and runtime > 0:
                title = self._get_title(record['movieId'])
                budget_num = self._parse_budget_to_number(budget)

                cost_per_minute = round(budget_num / runtime, 2)
                movie_costs[title] = cost_per_minute

        sorted_movies = sorted(movie_costs.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_movies[:n])

    def top_roi(self, n, max_movies=10):
        """
        Здесь мы увидим фильмы, на которые был потрачен маленький бюджет, но получился огромный выхлоп (return on investment)
        ROI считают по формуле: ROI = (Доход от вложений — Сумма вложений) / Сумма вложений * 100 %
        """

        movie_roi = {}
        for record in self.data[:max_movies]:
            html = self._get_imdb_page(record['imdbId'])
            budget = self._parse_imdb_field(html, 'Budget') # сумма вложений
            gross = self._parse_imdb_field(html, 'Cumulative Worldwide Gross') # доход от вложений

            if budget and gross:
                budget_num = self._parse_budget_to_number(budget)
                gross_num = self._parse_budget_to_number(gross)
            
                if budget_num is None or gross_num is None or budget_num <= 0:
                    continue

                roi = (gross_num - budget_num) / budget_num

                title = self._get_title(record['movieId'])
                movie_roi[title] = round(roi, 2)

        sorted_movies = sorted(movie_roi.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_movies[:n])

if __name__ == '__main__':
    base_path = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base_path, 'ml-latest-small')

    print("=== Анализ оценок ===")
    ratings = Ratings(os.path.join(data_path, 'ratings.csv'))
    print("Распределение по годам:", ratings.movies.dist_by_year())
    print("Распределение по оценкам:", ratings.movies.dist_by_rating())
    print("Топ-5 по количеству оценок:", ratings.movies.top_by_num_of_ratings(5))
    print("Топ-5 по average/meadian рейтингу:", ratings.movies.top_by_ratings(5, 'average'))
    print("Топ-5 спорных фильмов:", ratings.movies.top_controversial(5))

    print("\n=== Анализ пользователей ===")
    print("Распределение пользователей по количеству оценок:", ratings.users.dist_by_num_of_ratings())
    print("Распределение пользователей по рейтингам:", ratings.users.dist_by_ratings('median'))
    print("Топ-5 непостоянных пользователей:", ratings.users.top_controversial(5))

    print("\n=== Анализ тегов ===")
    tags = Tags(os.path.join(data_path, 'tags.csv'))
    print("Топ-5 тегов с наибольшим количеством слов:", tags.most_words(5))
    print("Топ-5 самых длинных тегов:", tags.longest(5))
    print("Самые длинные и многословные теги:", tags.most_words_and_longest(5))
    print("Топ-5 популярных тегов:", tags.most_popular(5))
    print("Теги со словом 'love':", tags.tags_with('love'))

    print("\n=== Анализ фильмов ===")
    movies = Movies(os.path.join(data_path, 'movies.csv'))
    print("Распределение по годам выпуска:", dict(list(movies.dist_by_release().items())[:10]))
    print("Распределение по жанрам:", movies.dist_by_genres())
    print("Топ-5 фильмов с наибольшим количеством жанров:", movies.most_genres(5))

    print("\n=== Анализ ссылок ===")
    links = Links(os.path.join(data_path, 'links.csv'))
    print("Информация с IMDb для фильмов:", links.get_imdb([1, 2], ['Director', 'Budget', 'Runtime', 'Cumulative Worldwide Gross']))
    print("Топ-5 режиссёров:", links.top_directors(5, max_movies=10))
    print("Топ-5 самых дорогих фильмов:", links.most_expensive(5, max_movies=10))
    print("Топ-5 самых прибыльных фильмов:", links.most_profitable(5, max_movies=10))
    print("Топ-5 самых длинных фильмов:", links.longest(5, max_movies=10))
    print("Топ-5 фильмов по стоимости за минуту:", links.top_cost_per_minute(5, max_movies=10))
