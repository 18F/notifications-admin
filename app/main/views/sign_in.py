from flask import render_template, redirect, jsonify
from flask import session

from app.main import main
from app.main.dao import users_dao
from app.main.encryption import check_hash
from app.main.encryption import hashpw
from app.main.forms import LoginForm
from app.main.views import send_sms_code


@main.route("/sign-in", methods=(['GET']))
def render_sign_in():
    return render_template('views/signin.html', form=LoginForm())


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
        if check_hash(form.password.data, user.password):
            sms_code = send_sms_code(user.id, user.mobile_number)
            session['user_id'] = user.id
        else:
            users_dao.increment_failed_login_count(user.id)
            return jsonify(authorization=False), 401
    else:
        return jsonify(form.errors), 400
    return redirect('/two-factor')
