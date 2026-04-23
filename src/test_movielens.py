import pytest
import os

from movielens_analysis import Ratings, Tags, Movies, Links


def _make_ratings_with_data(data):
    """
    Создает объект Ratings с заданными данными для тестирования.
    """
    r = Ratings.__new__(Ratings)
    r.path = "dummy"
    r.data = data
    r.movies_data = {}
    r.movies = Ratings.Movies(r)
    r.users = Ratings.Users(r)
    return r


def _make_links_with_data(data, movies_data=None):
    """
    Создает объект Links с заданными данными для тестирования.
    """
    l = Links.__new__(Links)
    l.path = "dummy"
    l.data = data
    l.movies_data = movies_data or {}
    l._imdb_cache = {}
    l._movie_id_to_imdb = {}
    return l


class Tests:

    # Фикстуры для загрузки данных
    @pytest.fixture
    def ratings(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml-latest-small')
        return Ratings(os.path.join(data_path, 'ratings.csv'))

    @pytest.fixture
    def tags(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml-latest-small')
        return Tags(os.path.join(data_path, 'tags.csv'))

    @pytest.fixture
    def movies(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml-latest-small')
        return Movies(os.path.join(data_path, 'movies.csv'))

    @pytest.fixture
    def links(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml-latest-small')
        return Links(os.path.join(data_path, 'links.csv'))

    # Тесты для класса Ratings
    def test_dist_by_year_returns_dict(self, ratings):
        """
        Проверяет, что dist_by_year() возвращает словарь.
        """
        result = ratings.movies.dist_by_year()
        assert isinstance(result, dict)

    def test_dist_by_rating_keys_are_floats(self, ratings):
        """
        Проверяет, что ключи словаря — числа (int или float).
        """
        result = ratings.movies.dist_by_rating()
        for key in result.keys():
            assert isinstance(key, (int, float))

    def test_top_by_num_of_ratings_correct_length(self, ratings):
        """
        Проверяет, что результат содержит не более n элементов.
        """
        result = ratings.movies.top_by_num_of_ratings(5)
        assert len(result) <= 5

    def test_top_by_ratings_values_rounded(self, ratings):
        """
        Проверяет, что значения округлены до 2 знаков после запятой.
        """
        result = ratings.movies.top_by_ratings(5)
        for value in result.values():
            assert round(value, 2) == value

    def test_top_controversial_values_rounded(self, ratings):
        """
        Проверяет округление значений дисперсии до 2 знаков.
        """
        result = ratings.movies.top_controversial(5)
        for value in result.values():
            assert round(value, 2) == value

    def test_users_dist_by_num_of_ratings_returns_dict(self, ratings):
        """
        Проверяет, что Users.dist_by_num_of_ratings() возвращает словарь.
        """
        result = ratings.users.dist_by_num_of_ratings()
        assert isinstance(result, dict)

    def test_users_dist_by_ratings_returns_dict(self, ratings):
        """
        Проверяет, что Users.dist_by_ratings() возвращает словарь.
        """
        result = ratings.users.dist_by_ratings()
        assert isinstance(result, dict)

    def test_users_top_controversial_sorted_descending(self, ratings):
        """
        Проверяет сортировку по убыванию дисперсии у пользователей.
        """
        result = ratings.users.top_controversial(5)
        values = list(result.values())
        assert values == sorted(values, reverse=True)

    # Тесты для класса Tags
    def test_most_words_keys_are_strings(self, tags):
        """
        Проверяет, что ключи (теги) — строки.
        """
        result = tags.most_words(5)
        for key in result.keys():
            assert isinstance(key, str)

    def test_longest_returns_list(self, tags):
        """
        Проверяет, что longest() возвращает список (не словарь).
        """
        result = tags.longest(5)
        assert isinstance(result, list)

    def test_most_words_and_longest_elements_are_strings(self, tags):
        """
        Проверяет, что все элементы списка — строки.
        """
        result = tags.most_words_and_longest(10)
        for item in result:
            assert isinstance(item, str)

    def test_most_popular_sorted_descending(self, tags):
        """
        Проверяет сортировку по убыванию популярности.
        """
        result = tags.most_popular(5)
        values = list(result.values())
        assert values == sorted(values, reverse=True)

    def test_tags_with_sorted_alphabetically(self, tags):
        """
        Проверяет, что результат отсортирован по алфавиту.
        """
        result = tags.tags_with('a')
        assert result == sorted(result)

    # Тесты для класса Movies
    def test_dist_by_release_keys_are_integers(self, movies):
        """
        Проверяет, что ключи (годы) — целые числа.
        """
        result = movies.dist_by_release()
        for key in result.keys():
            assert isinstance(key, int)

    def test_dist_by_genres_keys_are_strings(self, movies):
        """
        Проверяет, что ключи (названия жанров) — строки.
        """
        result = movies.dist_by_genres()
        for key in result.keys():
            assert isinstance(key, str)

    def test_most_genres_correct_length(self, movies):
        """
        Проверяет, что результат содержит не более n элементов.
        """
        result = movies.most_genres(5)
        assert len(result) <= 5

    # Тесты для класса Links
    def test_get_imdb_sorted_descending(self, links):
        """
        Проверяет сортировку по убыванию movieId.
        Первым должен идти фильм с наибольшим ID.
        """
        result = links.get_imdb([1, 2, 3], ['Director'])
        if len(result) > 1:  # Проверяем только если несколько результатов
            movie_ids = [row[0] for row in result]
            assert movie_ids == sorted(movie_ids, reverse=True)

    def test_top_directors_returns_dict(self, links):
        """
        Проверяет, что top_directors() возвращает словарь.
        """
        result = links.top_directors(3)
        assert isinstance(result, dict)

    def test_most_expensive_returns_dict(self, links):
        """
        Проверяет, что most_expensive() возвращает словарь.
        """
        result = links.most_expensive(3)
        assert isinstance(result, dict)

    def test_most_profitable_returns_dict(self, links):
        """
        Проверяет, что most_profitable() возвращает словарь.
        """
        result = links.most_profitable(3)
        assert isinstance(result, dict)

    def test_longest_returns_dict(self, links):
        """
        Проверяет, что longest() возвращает словарь.
        """
        result = links.longest(3)
        assert isinstance(result, dict)

    def test_top_cost_per_minute_returns_dict(self, links):
        """
        Проверяет, что top_cost_per_minute() возвращает словарь.
        """
        result = links.top_cost_per_minute(3)
        assert isinstance(result, dict)

    def test_top_cost_per_minute_values_rounded(self, links):
        """
        Проверяет округление стоимости минуты до 2 знаков.
        """
        result = links.top_cost_per_minute(3)
        for value in result.values():
            assert round(value, 2) == value

    # Бонусные тесты для Ratings.Movies
    def test_high_rated_movies_by_year_returns_dict_and_sorted_and_correct_counts(self):
        """
        Проверяет, что high_rated_movies_by_year() возвращает словарь,
        отсортированный по годам, с правильными подсчетами фильмов.
        """
        data = [
            {"userId": 1, "movieId": 10, "rating": 5.0, "timestamp": 1577836800},
            {"userId": 2, "movieId": 10, "rating": 4.6, "timestamp": 1577836800},

            {"userId": 1, "movieId": 20, "rating": 4.7, "timestamp": 1609459200},
            {"userId": 3, "movieId": 20, "rating": 4.7, "timestamp": 1609459200},

            {"userId": 4, "movieId": 30, "rating": 4.6, "timestamp": 1609459200},
            {"userId": 5, "movieId": 30, "rating": 4.6, "timestamp": 1609459200},
        ]
        ratings = _make_ratings_with_data(data)

        result = ratings.movies.high_rated_movies_by_year(threshold=4.7)

        assert isinstance(result, dict)

        assert all(isinstance(k, int) for k in result.keys())
        assert all(isinstance(v, int) for v in result.values())

        years = list(result.keys())
        assert years == sorted(years)

        assert result == {2020: 1, 2021: 1}

    def test_high_rated_movies_by_year_threshold_stricter_changes_result(self):
        """
        Проверяет, что изменение порога threshold влияет на результат.
        """
        data = [
            {"userId": 1, "movieId": 10, "rating": 5.0, "timestamp": 1577836800},
            {"userId": 2, "movieId": 10, "rating": 4.6, "timestamp": 1577836800},  # avg 4.8
            {"userId": 1, "movieId": 20, "rating": 4.7, "timestamp": 1609459200},
            {"userId": 3, "movieId": 20, "rating": 4.7, "timestamp": 1609459200},  # avg 4.7
        ]
        ratings = _make_ratings_with_data(data)

        result = ratings.movies.high_rated_movies_by_year(threshold=4.75)
        assert result == {2020: 1}

    def test_trend_by_year_returns_dict_sorted_and_correct_averages(self):
        """
        Проверяет, что trend_by_year() возвращает словарь,
        отсортированный по годам, с правильными средними значениями рейтингов.
        """
        data = [
            # movie 10, year 2020: ratings 5.0 and 4.0 -> avg 4.5
            {"userId": 1, "movieId": 10, "rating": 5.0, "timestamp": 1577836800},
            {"userId": 2, "movieId": 10, "rating": 4.0, "timestamp": 1577836800},

            # movie 10, year 2021: rating 3.0 -> avg 3.0
            {"userId": 3, "movieId": 10, "rating": 3.0, "timestamp": 1609459200},

            # другой фильм, не должен мешать
            {"userId": 1, "movieId": 20, "rating": 5.0, "timestamp": 1609459200},
        ]
        ratings = _make_ratings_with_data(data)

        result = ratings.movies.trend_by_year(movie_id=10)

        assert isinstance(result, dict)

        assert all(isinstance(k, int) for k in result.keys())
        assert all(isinstance(v, float) for v in result.values())

        years = list(result.keys())
        assert years == sorted(years)

        assert result == {2020: 4.5, 2021: 3.0}

    def test_trend_by_year_for_missing_movie_returns_empty_dict(self):
        """
        Проверяет, что trend_by_year() возвращает пустой словарь
        для несуществующего movie_id.
        """
        data = [
            {"userId": 1, "movieId": 10, "rating": 5.0, "timestamp": 1577836800},
        ]
        ratings = _make_ratings_with_data(data)

        result = ratings.movies.trend_by_year(movie_id=999)
        assert isinstance(result, dict)
        assert result == {}

    # Бонусные тесты для Links
    def test_top_roi_returns_dict_sorted_desc_and_correct_values(self, monkeypatch):
        """
        Проверяет, что top_roi() возвращает словарь,
        отсортированный по убыванию ROI, с правильными значениями.
        """
        links_data = [
            {"movieId": 1, "imdbId": "aaa", "tmdbId": None},
            {"movieId": 2, "imdbId": "bbb", "tmdbId": None},
            {"movieId": 3, "imdbId": "ccc", "tmdbId": None},
        ]
        movies_data = {
            1: "Movie A",
            2: "Movie B",
            3: "Movie C",
        }
        links = _make_links_with_data(links_data, movies_data=movies_data)

        def fake_get_imdb_page(imdb_id):
            return f"<html>{imdb_id}</html>"

        # Movie A: budget 100, gross 300 => ROI = (300-100)/100 = 2.0
        # Movie B: budget 200, gross 300 => ROI = 0.5
        # Movie C: budget 100, gross 200 => ROI = 1.0
        imdb_fields = {
            "aaa": {"Budget": "$100", "Cumulative Worldwide Gross": "$300"},
            "bbb": {"Budget": "$200", "Cumulative Worldwide Gross": "$300"},
            "ccc": {"Budget": "$100", "Cumulative Worldwide Gross": "$200"},
        }

        def fake_parse_imdb_field(html, field):
            imdb_id = html.replace("<html>", "").replace("</html>", "")
            return imdb_fields[imdb_id].get(field)

        monkeypatch.setattr(links, "_get_imdb_page", fake_get_imdb_page)
        monkeypatch.setattr(links, "_parse_imdb_field", fake_parse_imdb_field)

        result = links.top_roi(n=3, max_movies=3)

        assert isinstance(result, dict)

        assert all(isinstance(k, str) for k in result.keys())
        assert all(isinstance(v, float) for v in result.values())

        rois = list(result.values())
        assert rois == sorted(rois, reverse=True)
        
        assert result == {
            "Movie A": 2.0,
            "Movie C": 1.0,
            "Movie B": 0.5,
        }

    def test_top_roi_respects_n_and_skips_invalid(self, monkeypatch):
        """
        Проверяет, что top_roi() учитывает параметр n
        и пропускает фильмы с невалидными данными.
        """
        links_data = [
            {"movieId": 1, "imdbId": "good", "tmdbId": None},     # валидный
            {"movieId": 2, "imdbId": "nogross", "tmdbId": None},  # gross отсутствует -> пропуск
            {"movieId": 3, "imdbId": "zerobudget", "tmdbId": None},  # budget=0 -> пропуск
            {"movieId": 4, "imdbId": "good2", "tmdbId": None},    # валидный
        ]
        movies_data = {1: "Good 1", 2: "No Gross", 3: "Zero Budget", 4: "Good 2"}
        links = _make_links_with_data(links_data, movies_data=movies_data)

        def fake_get_imdb_page(imdb_id):
            return imdb_id 

        imdb_fields = {
            "good": {"Budget": "$100", "Cumulative Worldwide Gross": "$200"},      # ROI 1.0
            "nogross": {"Budget": "$100", "Cumulative Worldwide Gross": None},    # пропуск
            "zerobudget": {"Budget": "$0", "Cumulative Worldwide Gross": "$100"}, # пропуск
            "good2": {"Budget": "$50", "Cumulative Worldwide Gross": "$200"},     # ROI 3.0
        }

        def fake_parse_imdb_field(html, field):
            return imdb_fields[html].get(field)

        monkeypatch.setattr(links, "_get_imdb_page", fake_get_imdb_page)
        monkeypatch.setattr(links, "_parse_imdb_field", fake_parse_imdb_field)

        # Берём max_movies=4, но валидных будет только 2; n=1 => вернётся только топ-1
        result = links.top_roi(n=1, max_movies=4)

        assert isinstance(result, dict)
        assert list(result.keys()) == ["Good 2"]
        assert list(result.values()) == [3.0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
