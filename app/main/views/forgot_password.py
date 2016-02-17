from flask import (
    render_template,
    flash
)

from app.main import main
from app.main.dao import users_dao
from app.main.forms import ForgotPasswordForm
from app.notify_client.sender import send_change_password_email


@main.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        if not users_dao.is_email_unique(form.email_address.data):
            user = users_dao.get_user_by_email(form.email_address.data)
            users_dao.request_password_reset(user)
            send_change_password_email(form.email_address.data)
            return render_template('views/password-reset-sent.html')
        else:
            return render_template('views/password-reset-sent.html')

    return render_template('views/forgot-password.html', form=form)
