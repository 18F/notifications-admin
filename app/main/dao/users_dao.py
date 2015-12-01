from app import db, login_manager
from app.models import User
from app.main.encryption import hashpw


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(user_id)


def insert_user(user):
    user.password = hashpw(user.password)
    db.session.add(user)
    db.session.commit()


def get_user_by_id(id):
    return User.query.filter_by(id=id).first()


def get_all_users():
    return User.query.all()


def get_user_by_email(email_address):
    return User.query.filter_by(email_address=email_address).first()


def increment_failed_login_count(id):
    user = User.query.filter_by(id=id).first()
    user.failed_login_count += 1
    db.session.commit()
