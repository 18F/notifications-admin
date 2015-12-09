from flask import render_template, redirect, jsonify
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao
from app.main.encryption import checkpw
from app.main.forms import LoginForm


@main.route("/sign-in", methods=(['GET']))
def render_sign_in():
    return render_template('signin.html', form=LoginForm())


@main.route('/sign-in', methods=(['POST']))
def process_sign_in():
    form = LoginForm()
    if form.validate_on_submit():
        user = users_dao.get_user_by_email(form.email_address.data)
        if user is None:
            return jsonify(authorization=False), 401
        if user.is_locked():
            return jsonify(locked_out=True), 401
        if not user.is_active():
            return jsonify(active_user=False), 401
        if checkpw(form.password.data, user.password):
            login_user(user)
        else:
            users_dao.increment_failed_login_count(user.id)
            return jsonify(authorization=False), 401
    else:
        return jsonify(form.errors), 400
    return redirect('/two-factor')
