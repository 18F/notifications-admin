from flask import url_for
from app.models import User
from tests import create_test_user


def test_should_return_list_of_all_jobs(app_, db_, db_session, service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = User.query.first()
            client.login(user)
            response = client.get(url_for('main.view_jobs', service_id=101))

        assert response.status_code == 200
        assert 'Test message 1' in response.get_data(as_text=True)
        assert 'Final reminder' in response.get_data(as_text=True)


def test_should_show_page_for_one_job(app_, db_, db_session, service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            # TODO filename will be part of job metadata not in session
            with client.session_transaction() as s:
                s[456] = 'dispatch_20151114.csv'
        user = User.query.first()
        client.login(user)
        response = client.get(url_for('main.view_job', service_id=123, job_id=456))

        assert response.status_code == 200
        assert 'dispatch_20151114.csv' in response.get_data(as_text=True)
        assert 'Test message 1' in response.get_data(as_text=True)


def test_should_show_page_for_one_notification(app_, db_, db_session, service_one):
    with app_.test_request_context():
        with app_.test_client() as client:
            user = User.query.first()
            client.login(user)
            response = client.get(url_for(
                'main.view_notification',
                service_id=101,
                job_id=123,
                notification_id=3))

        assert response.status_code == 200
        assert 'Text message' in response.get_data(as_text=True)
        assert '+44 7700 900 522' in response.get_data(as_text=True)
