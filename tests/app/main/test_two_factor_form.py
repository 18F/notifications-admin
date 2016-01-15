from datetime import datetime, timedelta

from app.main.dao import verify_codes_dao
from app.main.forms import TwoFactorForm
from tests.app.main import create_test_user


def test_form_is_valid_returns_no_errors(app_, db_, db_session):
    with app_.test_request_context(method='POST',
                                                  data={'sms_code': '12345'}) as req:
        user = set_up_test_data()
        codes = verify_codes_dao.get_codes(user.id)
        form = TwoFactorForm(codes)
        assert form.validate() is True
        assert len(form.errors) == 0


def test_returns_errors_when_code_is_too_short(app_, db_, db_session):
    with app_.test_request_context(method='POST',
                                                  data={'sms_code': '145'}) as req:
        user = set_up_test_data()
        codes = verify_codes_dao.get_codes(user.id)
        form = TwoFactorForm(codes)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must be 5 digits', 'Code does not match']})


def test_returns_errors_when_code_is_missing(app_, db_, db_session):
    with app_.test_request_context(method='POST',
                                                  data={}) as req:
        user = set_up_test_data()
        codes = verify_codes_dao.get_codes(user.id)
        form = TwoFactorForm(codes)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must not be empty']})


def test_returns_errors_when_code_contains_letters(app_, db_, db_session):
    with app_.test_request_context(method='POST',
                                                  data={'sms_code': 'asdfg'}) as req:
        user = set_up_test_data()
        codes = verify_codes_dao.get_codes(user.id)
        form = TwoFactorForm(codes)
        assert form.validate() is False
        assert len(form.errors) == 1
        assert set(form.errors) == set({'sms_code': ['Code must be 5 digits', 'Code does not match']})


def test_should_return_errors_when_code_is_expired(app_, db_, db_session):
    with app_.test_request_context(method='POST',
                                                  data={'sms_code': '23456'}) as req:
        user = create_test_user('active')
        verify_codes_dao.add_code_with_expiry(user_id=user.id,
                                              code='23456',
                                              code_type='sms',
                                              expiry=datetime.now() + timedelta(hours=-2))
        codes = verify_codes_dao.get_codes(user.id)
        form = TwoFactorForm(codes)
        assert form.validate() is False
        errors = form.errors
        assert len(errors) == 1
        assert errors == {'sms_code': ['Code has expired']}


def set_up_test_data():
    user = create_test_user('active')
    verify_codes_dao.add_code(user_id=user.id, code='12345', code_type='sms')
    return user
