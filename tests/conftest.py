import pytest
from app import create_app, db
from app.models import User, Movie, UserMovie
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret'


@pytest.fixture
def app():
    app = create_app()
    app.config.from_object(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, app):
    """Залогиненный клиент (testuser / password123)."""
    client.post('/register', data={
        'username': 'testuser',
        'password': 'password123'
    })
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    return client

@pytest.fixture
def db_session(app):
    """Сессия БД для тестов."""
    with app.app_context():
        yield db.session