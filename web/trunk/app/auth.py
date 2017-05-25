import uuid
from itsdangerous import URLSafeTimedSerializer
from .models import User
from . import app, lm


@lm.user_loader
def load_user(id):
    """ Flask-Login user_loader callback and the decorator function ask this function to get a User Object or
    return None based on the user id. The user id was stored in the session environment by Flask-Login.

    :param string id: use to reload a user from the session
    :return: object User: user_loader stores the returned User object in current_user in every flask request.
    """
    return User.query.get(int(id))


@lm.token_loader
def load_token(token):
    # Set token expiry based on cookie duration
    duration = app.config['REMEMBER_COOKIE_DURATION'].total_seconds()

    # Decrypt security token, data = [user.id, user.password]
    data = login_serializer().loads(token, max_age=duration)
    user_id = int(data[0])
    user_sess_key = data[1]

    obj = User.query.get(user_id)
    if obj and obj.session_key == user_sess_key:
        return obj
    return None


def login_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def generate_uuid():
    return uuid.uuid4().hex
