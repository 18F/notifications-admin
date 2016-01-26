from flask import url_for


def test_render_sign_in_returns_sign_in_template(app_):
    with app_.test_request_context():
        response = app_.test_client().get(url_for('main.sign_in'))
    assert response.status_code == 200
    assert 'Sign in' in response.get_data(as_text=True)
    assert 'Email address' in response.get_data(as_text=True)
    assert 'Password' in response.get_data(as_text=True)
    assert 'Forgotten password?' in response.get_data(as_text=True)


def test_logged_in_user_redirects_to_choose_service(app_,
                                                    db_,
                                                    db_session,
                                                    mock_active_user,
                                                    mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_active_user)
            response = client.get(url_for('main.sign_in'))
            assert response.status_code == 302

            response = client.get(url_for('main.sign_in', follow_redirects=True))
            assert response.location == url_for('main.choose_service', _external=True)


def test_process_sign_in_return_2fa_template(app_,
                                             db_,
                                             db_session,
                                             mock_send_sms,
                                             mock_send_email,
                                             mock_get_user,
                                             mock_get_by_email,
                                             mock_user_checkpassword):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'val1dPassw0rd!'})
    assert response.status_code == 302
    assert response.location == 'http://localhost/two-factor'


def test_should_return_locked_out_true_when_user_is_locked(app_, mock_get_by_email):
    with app_.test_request_context():
        for _ in range(10):
            app_.test_client().post(
                url_for('main.sign_in'), data={
                    'email_address': 'locked_user@example.gov.uk',
                    'password': 'whatIsMyPassword!'})

        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'val1dPassw0rd!'})

        assert response.status_code == 200
        assert 'Username or password is incorrect' in response.get_data(as_text=True)

        another_bad_attempt = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'valid@example.gov.uk',
                'password': 'whatIsMyPassword!'})
        assert another_bad_attempt.status_code == 200
        assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_active_user_is_false_if_user_is_inactive(app_, mock_get_by_email):

    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'inactive_user@example.gov.uk',
                'password': 'val1dPassw0rd!'})

    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_200_when_user_does_not_exist(app_, mock_get_by_email):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'notfound@gov.uk',
                'password': 'doesNotExist!'})
    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)


def test_should_return_200_when_user_is_not_active(app_, mock_get_by_email):
    with app_.test_request_context():
        response = app_.test_client().post(
            url_for('main.sign_in'), data={
                'email_address': 'pending_user@example.gov.uk',
                'password': 'val1dPassw0rd!'})
    assert response.status_code == 200
    assert 'Username or password is incorrect' in response.get_data(as_text=True)
