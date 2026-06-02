from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Movie, UserMovie

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if current_user.is_authenticated:
        user_movies = current_user.movies  
        watched_count = sum(1 for um in user_movies if um.status == 'watched')
        to_watch_count = sum(1 for um in user_movies if um.status == 'to_watch')
    else:
        user_movies = []
        watched_count = 0
        to_watch_count = 0
    return render_template('index.html',
                           user_movies=user_movies,
                           watched_count=watched_count,
                           to_watch_count=to_watch_count)

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

    existing = UserMovie.query.filter_by(user_id=current_user.id, movie_id=movie.id).first()
    if existing:
        flash('Этот фильм уже в вашем списке')
    else:
        user_movie = UserMovie(user_id=current_user.id, movie_id=movie.id, status='to_watch')
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