from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Movie, UserMovie, User, Friendship
from app.omdb import search_movies, get_movie_details

main = Blueprint('main', __name__)


@main.route('/')
def index():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('filter', 'all')  # all, to_watch, watched
    page = request.args.get('page', 1, type=int)
    per_page = 8

    if current_user.is_authenticated:
        base_query = UserMovie.query.filter_by(user_id=current_user.id)\
                                     .join(Movie)\
                                     .order_by(UserMovie.timestamp.desc())

        # Фильтр по статусу
        if status_filter == 'to_watch':
            base_query = base_query.filter(UserMovie.status == 'to_watch')
        elif status_filter == 'watched':
            base_query = base_query.filter(UserMovie.status == 'watched')

        # Поиск по названию
        if search_query:
            base_query = base_query.filter(Movie.title.ilike(f'%{search_query}%'))

        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
        user_movies = pagination.items

        # Счётчики для статистики 
        watched_count = UserMovie.query.filter_by(
            user_id=current_user.id, status='watched'
        ).count()
        to_watch_count = UserMovie.query.filter_by(
            user_id=current_user.id, status='to_watch'
        ).count()
    else:
        user_movies = []
        pagination = None
        watched_count = 0
        to_watch_count = 0

    return render_template(
        'index.html',
        user_movies=user_movies,
        watched_count=watched_count,
        to_watch_count=to_watch_count,
        pagination=pagination,
        search_query=search_query,
        status_filter=status_filter
    )


@main.route('/search')
def search():
    query = request.args.get('q', '')
    results = []
    if query:
        results = search_movies(query)
    return render_template('search_results.html', results=results, query=query)


@main.route('/add_from_api', methods=['POST'])
@login_required
def add_from_api():
    imdb_id = request.form.get('imdb_id')
    status = request.form.get('status', 'to_watch')  
    
    if not imdb_id:
        flash('Ошибка: не указан идентификатор фильма')
        return redirect(url_for('main.index'))

    # Проверяем, есть ли уже фильм в базе
    movie = Movie.query.filter_by(imdb_id=imdb_id).first()
    if not movie:
        details = get_movie_details(imdb_id)
        if not details:
            flash('Не удалось получить информацию о фильме')
            return redirect(url_for('main.index'))
        movie = Movie(
            title=details['title'],
            year=details['year'],
            poster=details['poster'],
            plot=details['plot'],
            imdb_id=details['imdb_id']
        )
        db.session.add(movie)
        db.session.commit()

    existing = UserMovie.query.filter_by(
        user_id=current_user.id, movie_id=movie.id
    ).first()
    
    if existing:
        flash('Этот фильм уже в вашем списке')
        return redirect(url_for('main.index'))
    
    user_movie = UserMovie(
        user_id=current_user.id,
        movie_id=movie.id,
        status=status
    )
    db.session.add(user_movie)
    db.session.commit()
    
    if status == 'watched':
        flash('Фильм добавлен в просмотренные. Оставьте отзыв!')
        return redirect(url_for('main.rate_movie', user_movie_id=user_movie.id))
    
    flash('Фильм добавлен в список "Буду смотреть"')
    return redirect(url_for('main.index'))


@main.route('/add', methods=['POST'])
@login_required
def add_movie():
    title = request.form.get('title', '').strip()
    if not title:
        flash('Введите название фильма')
        return redirect(url_for('main.index'))

    movie = Movie.query.filter_by(title=title).first()
    if not movie:
        movie = Movie(title=title)
        db.session.add(movie)
        db.session.commit()

    existing = UserMovie.query.filter_by(
        user_id=current_user.id, movie_id=movie.id
    ).first()
    if existing:
        flash('Этот фильм уже в вашем списке')
    else:
        user_movie = UserMovie(
            user_id=current_user.id,
            movie_id=movie.id,
            status='to_watch'
        )
        db.session.add(user_movie)
        db.session.commit()
        flash('Фильм добавлен в список "Буду смотреть"')
    return redirect(url_for('main.index'))


@main.route('/update_status/<int:user_movie_id>', methods=['POST'])
@login_required
def update_status(user_movie_id):
    user_movie = UserMovie.query.get_or_404(user_movie_id)
    if user_movie.user_id != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('main.index'))
    
    new_status = request.form.get('status')
    if new_status in ('to_watch', 'watched'):
        user_movie.status = new_status
        db.session.commit()
    
    # Если переключили на "просмотрено", перенаправляем на страницу оценки
    if new_status == 'watched':
        return redirect(url_for('main.rate_movie', user_movie_id=user_movie_id))
    
    return redirect(url_for('main.index'))


@main.route('/rate/<int:user_movie_id>', methods=['GET', 'POST'])
@login_required
def rate_movie(user_movie_id):
    """Страница оценки и отзыва."""
    user_movie = UserMovie.query.get_or_404(user_movie_id)
    if user_movie.user_id != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        review = request.form.get('review', '').strip()
        
        if rating and 1 <= rating <= 10:
            user_movie.rating = rating
        if review:
            user_movie.review = review
        
        db.session.commit()
        flash('Спасибо за отзыв!')
        return redirect(url_for('main.index'))
    
    return render_template('rate_movie.html', user_movie=user_movie)


@main.route('/my_reviews')
@login_required
def my_reviews():
    """Страница со всеми отзывами пользователя."""
    reviewed_movies = UserMovie.query.filter_by(
        user_id=current_user.id
    ).filter(
        UserMovie.rating.isnot(None) | UserMovie.review.isnot(None)
    ).join(Movie).order_by(UserMovie.timestamp.desc()).all()
    
    return render_template('my_reviews.html', movies=reviewed_movies)


@main.route('/delete/<int:user_movie_id>', methods=['POST'])
@login_required
def delete_movie(user_movie_id):
    user_movie = UserMovie.query.get_or_404(user_movie_id)
    if user_movie.user_id != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('main.index'))
    db.session.delete(user_movie)
    db.session.commit()
    flash('Удалено')
    return redirect(url_for('main.index'))

# ==================== ДРУЗЬЯ ====================

@main.route('/friends')
@login_required
def friends():
    """Страница друзей: список друзей, входящие заявки, поиск."""
    search_query = request.args.get('search', '')
    
    # Поиск пользователей
    found_users = []
    if search_query:
        found_users = User.query.filter(
            User.username.ilike(f'%{search_query}%'),
            User.id != current_user.id
        ).all()
    
    # Входящие заявки (где текущий пользователь — friend_id, статус pending)
    incoming_requests = Friendship.query.filter_by(
        friend_id=current_user.id, status='pending'
    ).all()
    
    # Список друзей (все accepted-записи, где текущий пользователь — user_id или friend_id)
    friendships = Friendship.query.filter(
        (
            (Friendship.user_id == current_user.id) |
            (Friendship.friend_id == current_user.id)
        ),
        Friendship.status == 'accepted'
    ).all()
    
    # Собираем объекты друзей
    friends_list = []
    for f in friendships:
        if f.user_id == current_user.id:
            friends_list.append(f.friend)
        else:
            friends_list.append(f.user)
    
    return render_template(
        'friends.html',
        found_users=found_users,
        incoming_requests=incoming_requests,
        friends_list=friends_list,
        search_query=search_query
    )


@main.route('/send_request/<int:user_id>', methods=['POST'])
@login_required
def send_request(user_id):
    """Отправить заявку в друзья."""
    if user_id == current_user.id:
        flash('Нельзя отправить заявку самому себе')
        return redirect(url_for('main.friends'))
    
    # Проверяем, существует ли уже заявка
    existing = Friendship.query.filter(
        (
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)
        ) |
        (
            (Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id)
        )
    ).first()
    
    if existing:
        if existing.status == 'accepted':
            flash('Вы уже друзья')
        elif existing.status == 'pending':
            flash('Заявка уже отправлена')
        elif existing.status == 'rejected':
            # Можно отправить повторно
            existing.status = 'pending'
            db.session.commit()
            flash('Заявка отправлена повторно')
        return redirect(url_for('main.friends'))
    
    friendship = Friendship(user_id=current_user.id, friend_id=user_id, status='pending')
    db.session.add(friendship)
    db.session.commit()
    flash('Заявка отправлена')
    return redirect(url_for('main.friends'))


@main.route('/accept_request/<int:friendship_id>', methods=['POST'])
@login_required
def accept_request(friendship_id):
    """Принять заявку в друзья."""
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.friend_id != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('main.friends'))
    
    friendship.status = 'accepted'
    db.session.commit()
    flash('Заявка принята! Теперь вы друзья')
    return redirect(url_for('main.friends'))


@main.route('/reject_request/<int:friendship_id>', methods=['POST'])
@login_required
def reject_request(friendship_id):
    """Отклонить заявку."""
    friendship = Friendship.query.get_or_404(friendship_id)
    if friendship.friend_id != current_user.id:
        flash('Нет доступа')
        return redirect(url_for('main.friends'))
    
    friendship.status = 'rejected'
    db.session.commit()
    flash('Заявка отклонена')
    return redirect(url_for('main.friends'))


@main.route('/remove_friend/<int:friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    """Удалить из друзей."""
    friendship = Friendship.query.filter(
        (
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)
        ) |
        (
            (Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id)
        ),
        Friendship.status == 'accepted'
    ).first()
    
    if friendship:
        db.session.delete(friendship)
        db.session.commit()
        flash('Пользователь удалён из друзей')
    else:
        flash('Вы не друзья')
    
    return redirect(url_for('main.friends'))


@main.route('/friend/<int:friend_id>')
@login_required
def friend_profile(friend_id):
    """Просмотр списка фильмов друга."""
    # Проверяем, друзья ли мы
    friendship = Friendship.query.filter(
        (
            (Friendship.user_id == current_user.id) & (Friendship.friend_id == friend_id)
        ) |
        (
            (Friendship.user_id == friend_id) & (Friendship.friend_id == current_user.id)
        ),
        Friendship.status == 'accepted'
    ).first()
    
    if not friendship:
        flash('Вы не друзья с этим пользователем')
        return redirect(url_for('main.friends'))
    
    friend = User.query.get_or_404(friend_id)
    
    # Получаем фильмы друга
    friend_movies = UserMovie.query.filter_by(user_id=friend_id)\
                                   .join(Movie)\
                                   .order_by(UserMovie.timestamp.desc()).all()
    
    watched_count = UserMovie.query.filter_by(user_id=friend_id, status='watched').count()
    to_watch_count = UserMovie.query.filter_by(user_id=friend_id, status='to_watch').count()
    
    return render_template(
        'friend_profile.html',
        friend=friend,
        friend_movies=friend_movies,
        watched_count=watched_count,
        to_watch_count=to_watch_count
    )