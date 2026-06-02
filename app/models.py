from flask_login import UserMixin
from app import db, login_manager
from datetime import datetime, timezone

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    movies = db.relationship('UserMovie', back_populates='user')

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), unique=True, nullable=False)
    year = db.Column(db.String(10))              
    poster = db.Column(db.String(500))           
    plot = db.Column(db.Text)                    
    imdb_id = db.Column(db.String(20))           
    users = db.relationship('UserMovie', back_populates='movie')

class UserMovie(db.Model):
    __tablename__ = 'user_movies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    status = db.Column(db.String(20), default='to_watch')
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='movies')
    movie = db.relationship('Movie', back_populates='users')