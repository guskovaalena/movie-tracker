from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Movie, UserMovie
from app.omdb import search_movies, get_movie_details

main = Blueprint('main', __name__)


@main.route('/')
def index():
    search_query = request.args.get('search', '')        # поиск в своём списке
    page = request.args.get('page', 1, type=int)
    per_page = 8

    if current_user.is_authenticated:
        # Базовый запрос: все записи пользователя
        base_query = UserMovie.query.filter_by(user_id=current_user.id)\
                                     .join(Movie)\
                                     .order_by(UserMovie.timestamp.desc())

        # Фильтрация по поисковому запросу
        if search_query:
            base_query = base_query.filter(Movie.title.ilike(f'%{search_query}%'))

        # Пагинация
        pagination = base_query.paginate(page=page, per_page=per_page, error_out=False)
        user_movies = pagination.items

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
        search_query=search_query
    )


@main.route('/search')
def search():
    """Поиск фильмов через OMDb API."""
    query = request.args.get('q', '')
    results = []
    if query:
        results = search_movies(query)
    return render_template('search_results.html', results=results, query=query)


@main.route('/add_from_api', methods=['POST'])
@login_required
def add_from_api():
    """Добавление фильма из результатов поиска API."""
    imdb_id = request.form.get('imdb_id')
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

    # Проверяем, нет ли уже такой связи у пользователя
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


@main.route('/add', methods=['POST'])
@login_required
def add_movie():
    """Добавление фильма вручную (по названию)."""
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
    return redirect(url_for('main.index'))


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