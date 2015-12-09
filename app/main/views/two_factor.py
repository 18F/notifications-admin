from flask import render_template, redirect, jsonify, session
from flask_login import login_user

from app.main import main
from app.main.dao import users_dao
from app.main.forms import TwoFactorForm


@main.route("/two-factor", methods=['GET'])
def render_two_factor():
    return render_template('two-factor.html', form=TwoFactorForm())


@main.route('/two-factor', methods=['POST'])
def process_two_factor():
    form = TwoFactorForm()

    if form.validate_on_submit():
        user = users_dao.get_user_by_id(session['user_id'])
        login_user(user)
        return redirect('/dashboard')
    else:
        return jsonify(form.errors), 400
