from app.main.dao import users_dao
from app.main.forms import RegisterUserForm


def test_should_raise_validation_error_for_password(app_, mock_get_user_by_email):
    form = RegisterUserForm(users_dao.get_user_by_email)
    form.name.data = 'test'
    form.email_address.data = 'teset@example.gov.uk'
    form.mobile_number.data = '+441231231231'
    form.password.data = 'password1234'

    form.validate()
    assert 'That password is blacklisted, too common' in form.errors['password']
