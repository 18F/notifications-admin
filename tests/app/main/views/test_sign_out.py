from datetime import datetime
from flask import url_for
from app.main.dao import users_dao
from app.models import User


def test_render_sign_out_redirects_to_sign_in(app_):
    with app_.test_request_context():
        response = app_.test_client().get(
            url_for('main.sign_out'))
        assert response.status_code == 302
        assert response.location == url_for(
            'main.sign_in', _external=True, next=url_for('main.sign_out'))


def test_sign_out_user(app_,
                       mock_send_sms,
                       mock_send_email,
                       mock_get_service,
                       mock_active_user,
                       mock_get_by_email):
    with app_.test_request_context():
        email = 'valid@example.gov.uk'
        password = 'val1dPassw0rd!'
        with app_.test_client() as client:
            client.login(mock_active_user)
            # Check we are logged in
            response = client.get(
                url_for('main.service_dashboard', service_id="123"))
            assert response.status_code == 200
            response = client.get(url_for('main.sign_out'))
            assert response.status_code == 302
            assert response.location == url_for(
                'main.index', _external=True)
