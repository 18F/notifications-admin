from app.models import User
from flask import url_for


def test_should_show_recent_jobs_on_dashboard(app_,
                                              db_,
                                              db_session,
                                              mock_api_user,
                                              mock_get_service,
                                              mock_get_by_email):
    with app_.test_request_context():
        with app_.test_client() as client:
            client.login(mock_api_user)
            response = client.get(url_for('main.service_dashboard', service_id=123))

        assert response.status_code == 200
        assert 'You haven’t sent any text messages yet' in response.get_data(as_text=True)
