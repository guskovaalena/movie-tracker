import pytest
from app import create_app, db
from app.models import User, Movie, UserMovie
from config import Config


class TestConfig(Config):
    """Конфигурация для тестов: база в памяти, отключение CSRF, тестовый ключ"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'


@pytest.fixture
def app():
    """Создаёт тестовое приложение с чистой БД перед каждым тестом"""
    app = create_app()
    app.config.from_object(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Тестовый HTTP-клиент (эмулирует браузер)"""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """
    Фикстура возвращает клиента, который уже залогинен
    под пользователем testuser / password123.
    """
    # Регистрируем пользователя
    client.post('/register', data={
        'username': 'testuser',
        'password': 'password123'
    })
    # Входим
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    return client