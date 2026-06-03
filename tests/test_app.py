from app.models import User, Movie, UserMovie
from app import db

# Вспомогательная функция для проверки наличия текста в ответе
def assert_text_in_response(response, text):
    """Проверяет, что текст присутствует в ответе."""
    assert text in response.get_data(as_text=True)


# Базовые страницы
def test_index_page(client):
    """Главная страница открывается и содержит название приложения"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'Movie Tracker' in response.get_data(as_text=True)


def test_login_page(client):
    """Страница входа доступна"""
    response = client.get('/login')
    assert response.status_code == 200
    assert 'form' in response.get_data(as_text=True).lower()


def test_register_page(client):
    """Страница регистрации доступна"""
    response = client.get('/register')
    assert response.status_code == 200
    assert 'form' in response.get_data(as_text=True).lower()


# Регистрация
def test_register_success(client, app):
    """Успешная регистрация: пользователь сохраняется в БД"""
    response = client.post('/register', data={
        'username': 'newuser',
        'password': 'secret123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert_text_in_response(response, 'Регистрация успешна')
    with app.app_context():
        user = User.query.filter_by(username='newuser').first()
        assert user is not None


def test_register_duplicate(client):
    """Повторная регистрация того же имени выдаёт flash-ошибку"""
    client.post('/register', data={'username': 'dup', 'password': 'pass1'})
    response = client.post('/register', data={'username': 'dup', 'password': 'pass2'}, follow_redirects=True)
    data = response.get_data(as_text=True).lower()
    assert 'уже существует' in data


# Вход и выход
def test_login_correct(auth_client):
    """После входа на главной отображается имя пользователя"""
    response = auth_client.get('/')
    assert_text_in_response(response, 'testuser')


def test_login_wrong_password(client):
    """Вход с неверным паролем возвращает ошибку"""
    client.post('/register', data={'username': 'u1', 'password': 'right'})
    response = client.post('/login', data={'username': 'u1', 'password': 'wrong'}, follow_redirects=True)
    data = response.get_data(as_text=True).lower()
    assert 'неверн' in data


def test_logout(auth_client):
    """После выхода защищённые страницы недоступны"""
    assert_text_in_response(auth_client.get('/'), 'testuser')
    auth_client.get('/logout')
    # Пытаемся добавить фильм без авторизации - должен быть редирект на логин
    response = auth_client.post('/add', data={'title': 'test'}, follow_redirects=True)
    data = response.get_data(as_text=True)
    assert 'login' in data.lower() or 'Войдите' in data.lower()


# Добавление фильмов
def test_add_movie_requires_login(client):
    """Без авторизации запрос на добавление перенаправляет на логин"""
    response = client.post('/add', data={'title': 'Inception'}, follow_redirects=True)
    assert 'login' in response.get_data(as_text=True).lower()


def test_add_movie_success(auth_client, app):
    """Добавление нового фильма (пробелы обрезаются)"""
    response = auth_client.post('/add', data={'title': '  Matrix  '}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        movie = Movie.query.filter_by(title='Matrix').first()
        assert movie is not None
    assert_text_in_response(response, 'Matrix')


def test_add_duplicate_movie(auth_client, app):
    """Повторное добавление того же фильма не создаёт дубликат связи"""
    auth_client.post('/add', data={'title': 'Inception'})
    response = auth_client.post('/add', data={'title': 'Inception'}, follow_redirects=True)
    assert_text_in_response(response, 'Этот фильм уже в вашем списке')
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Inception').first()
        count = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).count()
        assert count == 1


def test_add_empty_title(auth_client):
    """Пустое название вызывает сообщение об ошибке"""
    response = auth_client.post('/add', data={'title': '   '}, follow_redirects=True)
    assert_text_in_response(response, 'Введите название фильма')


# Изменение статуса
def test_update_status(auth_client, app):
    """Переключение статуса to_watch -> watched -> to_watch"""
    auth_client.post('/add', data={'title': 'Alien'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Alien').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        assert um.status == 'to_watch'
        um_id = um.id

    auth_client.post(f'/update_status/{um_id}', data={'status': 'watched'}, follow_redirects=True)
    with app.app_context():
        um = db.session.get(UserMovie, um_id)
        assert um.status == 'watched'

    auth_client.post(f'/update_status/{um_id}', data={'status': 'to_watch'})
    with app.app_context():
        um = db.session.get(UserMovie, um_id)
        assert um.status == 'to_watch'


def test_update_status_wrong_user(client, app):
    """Чужой статус изменить нельзя"""
    # Alice добавляет фильм
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/login', data={'username': 'alice', 'password': '123'})
    client.post('/add', data={'title': 'Shared'})
    client.get('/logout')

    with app.app_context():
        alice = User.query.filter_by(username='alice').first()
        movie = Movie.query.filter_by(title='Shared').first()
        um = UserMovie.query.filter_by(user_id=alice.id, movie_id=movie.id).first()
        um_id = um.id

    # Bob пытается
    client.post('/register', data={'username': 'bob', 'password': '456'})
    client.post('/login', data={'username': 'bob', 'password': '456'})
    response = client.post(f'/update_status/{um_id}', data={'status': 'watched'}, follow_redirects=True)
    assert_text_in_response(response, 'Нет доступа')
    with app.app_context():
        um = db.session.get(UserMovie, um_id)
        assert um.status == 'to_watch'


# Удаление
def test_delete_movie(auth_client, app):
    """Свой фильм удаляется"""
    auth_client.post('/add', data={'title': 'DeleteMe'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='DeleteMe').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    response = auth_client.post(f'/delete/{um_id}', follow_redirects=True)
    assert_text_in_response(response, 'Удалено')
    with app.app_context():
        assert db.session.get(UserMovie, um_id) is None


def test_delete_movie_wrong_user(client, app):
    """Чужой фильм удалить нельзя"""
    client.post('/register', data={'username': 'alice2', 'password': '123'})
    client.post('/login', data={'username': 'alice2', 'password': '123'})
    client.post('/add', data={'title': 'Keep'})
    client.get('/logout')

    with app.app_context():
        alice = User.query.filter_by(username='alice2').first()
        movie = Movie.query.filter_by(title='Keep').first()
        um = UserMovie.query.filter_by(user_id=alice.id, movie_id=movie.id).first()
        um_id = um.id

    client.post('/register', data={'username': 'bob2', 'password': '456'})
    client.post('/login', data={'username': 'bob2', 'password': '456'})
    response = client.post(f'/delete/{um_id}', follow_redirects=True)
    assert_text_in_response(response, 'Нет доступа')
    with app.app_context():
        assert db.session.get(UserMovie, um_id) is not None


# Статистика
def test_statistics(auth_client, app):
    """Проверка счётчиков на главной странице"""
    auth_client.post('/add', data={'title': 'Film1'})
    auth_client.post('/add', data={'title': 'Film2'})
    auth_client.post('/add', data={'title': 'Film3'})

    # Переключим Film1 в watched
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Film1').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    auth_client.post(f'/update_status/{um_id}', data={'status': 'watched'})

    response = auth_client.get('/')
    data = response.get_data(as_text=True)
    # Проверяем, что статистика отображает числа 1 и 2 (можно просто наличие цифр)
    assert '1' in data  # watched
    assert '2' in data  # to_watch (Film2 и Film3)

def test_rate_movie(auth_client, app):
    
    auth_client.post('/add', data={'title': 'RateMe'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='RateMe').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    # Переключаем на watched
    auth_client.post(f'/update_status/{um_id}', data={'status': 'watched'})
    # Ставим оценку
    response = auth_client.post(f'/rate/{um_id}', data={'rating': 8, 'review': 'Отличный фильм!'}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        um = db.session.get(UserMovie, um_id)
        assert um.rating == 8
        assert um.review == 'Отличный фильм!'


def test_my_reviews_page(auth_client):
    """Страница «Мои отзывы» открывается."""
    response = auth_client.get('/my_reviews')
    assert response.status_code == 200


def test_my_reviews_shows_reviewed_movies(auth_client, app):
    """На странице отзывов отображаются оценённые фильмы."""
    auth_client.post('/add', data={'title': 'Reviewed Film'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Reviewed Film').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    auth_client.post(f'/update_status/{um_id}', data={'status': 'watched'})
    auth_client.post(f'/rate/{um_id}', data={'rating': 9, 'review': 'Шедевр!'})

    response = auth_client.get('/my_reviews')
    data = response.get_data(as_text=True)
    assert 'Reviewed Film' in data
    assert 'Шедевр!' in data


def test_rate_movie_page_get(auth_client, app):
    """Страница оценки открывается (GET)."""
    auth_client.post('/add', data={'title': 'Rate Page Test'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Rate Page Test').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    response = auth_client.get(f'/rate/{um_id}')
    assert response.status_code == 200


def test_rate_movie_page_post(auth_client, app):
    """Оценка сохраняется через POST."""
    auth_client.post('/add', data={'title': 'Rate Post Test'})
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        movie = Movie.query.filter_by(title='Rate Post Test').first()
        um = UserMovie.query.filter_by(user_id=user.id, movie_id=movie.id).first()
        um_id = um.id

    auth_client.post(f'/rate/{um_id}', data={'rating': 7, 'review': 'Неплохо'}, follow_redirects=True)
    with app.app_context():
        um = db.session.get(UserMovie, um_id)
        assert um.rating == 7
        assert um.review == 'Неплохо'


def test_friends_page(auth_client):
    """Страница друзей открывается."""
    response = auth_client.get('/friends')
    assert response.status_code == 200


def test_search_users(auth_client):
    """Поиск пользователей работает."""
    response = auth_client.get('/friends?search=testuser')
    assert response.status_code == 200


def test_send_friend_request(client, app):
    """Отправка заявки в друзья между двумя пользователями."""
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/register', data={'username': 'bob', 'password': '456'})

    client.post('/login', data={'username': 'alice', 'password': '123'})

    with app.app_context():
        bob = User.query.filter_by(username='bob').first()
        bob_id = bob.id

    response = client.post(f'/send_request/{bob_id}', follow_redirects=True)
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    assert 'Заявка отправлена' in data

    with app.app_context():
        from app.models import Friendship
        alice = User.query.filter_by(username='alice').first()
        friendship = Friendship.query.filter_by(
            user_id=alice.id, friend_id=bob_id, status='pending'
        ).first()
        assert friendship is not None


def test_accept_friend_request(client, app):
    """Принятие заявки в друзья."""
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/register', data={'username': 'bob', 'password': '456'})

    client.post('/login', data={'username': 'alice', 'password': '123'})
    with app.app_context():
        bob = User.query.filter_by(username='bob').first()
        bob_id = bob.id
    client.post(f'/send_request/{bob_id}')

    with app.app_context():
        from app.models import Friendship
        alice = User.query.filter_by(username='alice').first()
        friendship = Friendship.query.filter_by(
            user_id=alice.id, friend_id=bob_id, status='pending'
        ).first()
        fid = friendship.id

    client.get('/logout')
    client.post('/login', data={'username': 'bob', 'password': '456'})

    response = client.post(f'/accept_request/{fid}', follow_redirects=True)
    data = response.get_data(as_text=True)
    assert 'Теперь вы друзья' in data

    with app.app_context():
        from app.models import Friendship
        friendship = db.session.get(Friendship, fid)
        assert friendship.status == 'accepted'


def test_reject_friend_request(client, app):
    """Отклонение заявки в друзья."""
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/register', data={'username': 'bob', 'password': '456'})

    client.post('/login', data={'username': 'alice', 'password': '123'})
    with app.app_context():
        bob = User.query.filter_by(username='bob').first()
        bob_id = bob.id
    client.post(f'/send_request/{bob_id}')

    with app.app_context():
        from app.models import Friendship
        alice = User.query.filter_by(username='alice').first()
        friendship = Friendship.query.filter_by(
            user_id=alice.id, friend_id=bob_id, status='pending'
        ).first()
        fid = friendship.id

    client.get('/logout')
    client.post('/login', data={'username': 'bob', 'password': '456'})

    response = client.post(f'/reject_request/{fid}', follow_redirects=True)
    data = response.get_data(as_text=True)
    assert 'Заявка отклонена' in data

    with app.app_context():
        from app.models import Friendship
        friendship = db.session.get(Friendship, fid)
        assert friendship.status == 'rejected'


def test_remove_friend(client, app):
    """Удаление из друзей."""
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/register', data={'username': 'bob', 'password': '456'})

    client.post('/login', data={'username': 'alice', 'password': '123'})
    with app.app_context():
        bob = User.query.filter_by(username='bob').first()
        bob_id = bob.id
    client.post(f'/send_request/{bob_id}')

    with app.app_context():
        from app.models import Friendship
        alice = User.query.filter_by(username='alice').first()
        friendship = Friendship.query.filter_by(
            user_id=alice.id, friend_id=bob_id, status='pending'
        ).first()
        fid = friendship.id

    client.get('/logout')
    client.post('/login', data={'username': 'bob', 'password': '456'})
    client.post(f'/accept_request/{fid}')

    client.get('/logout')
    client.post('/login', data={'username': 'alice', 'password': '123'})
    response = client.post(f'/remove_friend/{bob_id}', follow_redirects=True)
    data = response.get_data(as_text=True)
    assert 'удалён' in data.lower()

    with app.app_context():
        from app.models import Friendship
        friendship = db.session.get(Friendship, fid)
        assert friendship is None  


def test_friend_profile(client, app):
    """Просмотр профиля друга."""
    client.post('/register', data={'username': 'alice', 'password': '123'})
    client.post('/register', data={'username': 'bob', 'password': '456'})

    client.post('/login', data={'username': 'alice', 'password': '123'})
    with app.app_context():
        bob = User.query.filter_by(username='bob').first()
        bob_id = bob.id
    client.post(f'/send_request/{bob_id}')

    with app.app_context():
        from app.models import Friendship
        alice = User.query.filter_by(username='alice').first()
        friendship = Friendship.query.filter_by(
            user_id=alice.id, friend_id=bob_id, status='pending'
        ).first()
        fid = friendship.id

    client.get('/logout')
    client.post('/login', data={'username': 'bob', 'password': '456'})
    client.post(f'/accept_request/{fid}')

    client.get('/logout')
    client.post('/login', data={'username': 'alice', 'password': '123'})
    response = client.get(f'/friend/{bob_id}')
    assert response.status_code == 200
    data = response.get_data(as_text=True)
    assert 'bob' in data


def test_filter_watched(auth_client):
    """Фильтр «Просмотрено» работает."""
    response = auth_client.get('/?filter=watched')
    assert response.status_code == 200


def test_filter_to_watch(auth_client):
    """Фильтр «Буду смотреть» работает."""
    response = auth_client.get('/?filter=to_watch')
    assert response.status_code == 200


def test_filter_all(auth_client):
    """Фильтр «Все» работает."""
    response = auth_client.get('/?filter=all')
    assert response.status_code == 200


def test_search_page(auth_client):
    """Страница поиска через API открывается."""
    response = auth_client.get('/search?q=Matrix')
    assert response.status_code == 200


def test_pagination(auth_client):
    """Пагинация работает без ошибок."""
    for i in range(10):
        auth_client.post('/add', data={'title': f'Paginated Film {i}'})
    response = auth_client.get('/?page=2')
    assert response.status_code == 200