from datetime import datetime, timedelta

from flask import (
    render_template,
    redirect,
    session,
    abort,
    url_for,
    flash
)

from flask.ext.login import current_user

from notifications_python_client.errors import HTTPError

from app.main import main
from app.main.dao import users_dao
from app.main.forms import (
    RegisterUserForm,
    RegisterUserFromInviteForm
)

from app import user_api_client


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user and current_user.is_authenticated():
        return redirect(url_for('main.choose_service'))

    form = RegisterUserForm()
    if form.validate_on_submit():
        return _do_registration(form)
    else:
        return render_template('views/register.html', form=form)


@main.route('/register-from-invite', methods=['GET', 'POST'])
def register_from_invite():

    form = RegisterUserFromInviteForm()
    invited_user = session.get('invited_user')
    if not invited_user:
        abort(404)

    if form.validate_on_submit():
        if form.service.data != invited_user['service'] or form.email_address.data != invited_user['email_address']:
            abort(400)
        return _do_registration(form)

    form.service.data = invited_user['service']
    form.email_address.data = invited_user['email_address']

    return render_template('views/register-from-invite.html', form=form)


def _do_registration(form, service=None):
    if users_dao.is_email_unique(form.email_address.data):
        try:
            user = user_api_client.register_user(form.name.data,
                                                 form.email_address.data,
                                                 form.mobile_number.data,
                                                 form.password.data)

        except HTTPError as e:
            if e.status_code == 404:
                abort(404)
            else:
                raise e

        # TODO possibly there should be some exception handling
        # for sending sms and email codes.
        # How do we report to the user there is a problem with
        # sending codes apart from service unavailable?
        # at the moment i believe http 500 is fine.
        users_dao.send_verify_code(user.id, 'sms', user.mobile_number)
        users_dao.send_verify_code(user.id, 'email', user.email_address)
        session['expiry_date'] = str(datetime.now() + timedelta(hours=1))
        session['user_details'] = {"email": user.email_address, "id": user.id}
        return redirect(url_for('main.verify'))
    else:
        flash('There was an error registering your account')
