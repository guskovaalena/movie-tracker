import os
import logging

logger = logging.getLogger(__name__)

OMDB_API_KEY = os.environ.get('OMDB_API_KEY')
BASE_URL = 'http://www.omdbapi.com/'


def _get_requests():
    """Ленивый импорт requests, чтобы тесты без сети не падали при импорте модуля."""
    try:
        import requests
        return requests
    except ImportError:
        logger.error("requests package is not installed")
        return None


def search_movies(query):
    """
    Ищет фильмы по названию, возвращает список словарей.
    Обходит ограничение бесплатного ключа OMDb.
    """
    if not OMDB_API_KEY:
        logger.warning("OMDB_API_KEY is not set")
        return []

    requests = _get_requests()
    if requests is None:
        return []

    # Сначала пробуем обычный поиск
    params = {
        'apikey': OMDB_API_KEY,
        's': query,
        'type': 'movie',
        'page': 1
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()

        if data.get('Response') == 'True':
            return data.get('Search', [])

        # Если ошибка "Too many results" — пробуем искать точнее
        if data.get('Error') == 'Too many results.':
            logger.info("Too many results, trying exact title search")
            return _search_by_title(requests, query)

        if 'Error' in data:
            logger.error(f"OMDb error: {data['Error']}")

        return []
    except Exception as e:
        logger.error(f"OMDb request failed: {e}")
        return []


def _search_by_title(requests, query):
    """
    Поиск по точному названию.
    Возвращает один фильм, но лучше чем ничего.
    """
    params = {
        'apikey': OMDB_API_KEY,
        't': query,
        'type': 'movie'
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()

        if data.get('Response') == 'True':
            # Преобразуем в формат, как у search
            return [{
                'Title': data.get('Title'),
                'Year': data.get('Year'),
                'imdbID': data.get('imdbID'),
                'Type': 'movie',
                'Poster': data.get('Poster')
            }]

        if 'Error' in data:
            logger.error(f"OMDb title search error: {data['Error']}")

        return []
    except Exception as e:
        logger.error(f"OMDb title request failed: {e}")
        return []


def get_movie_details(imdb_id):
    """Получает подробную информацию о фильме по IMDb ID."""
    if not OMDB_API_KEY:
        return None

    requests = _get_requests()
    if requests is None:
        return None

    params = {
        'apikey': OMDB_API_KEY,
        'i': imdb_id,
        'plot': 'short'
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        data = response.json()

        if data.get('Response') == 'True':
            return {
                'title': data.get('Title'),
                'year': data.get('Year'),
                'poster': data.get('Poster') if data.get('Poster') != 'N/A' else None,
                'plot': data.get('Plot'),
                'imdb_id': data.get('imdbID')
            }
    except Exception as e:
        logger.error(f"OMDb details request failed: {e}")

    return None