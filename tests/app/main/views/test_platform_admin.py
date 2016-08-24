from datetime import date

from flask import url_for
from freezegun import freeze_time
import pytest
from bs4 import BeautifulSoup

from tests.conftest import mock_get_user
from tests import service_json

from app.main.views.platform_admin import get_statistics, format_stats_by_service, create_global_stats


def test_should_redirect_if_not_logged_in(app_):
    with app_.test_request_context():
        with app_.test_client() as client:
            response = client.get(url_for('main.platform_admin'))
            assert response.status_code == 302
            assert url_for('main.index', _external=True) in response.location


def test_should_403_if_not_platform_admin(app_, active_user_with_permissions, mocker):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=active_user_with_permissions)
            client.login(active_user_with_permissions)

            response = client.get(url_for('main.platform_admin'))

            assert response.status_code == 403


@pytest.mark.parametrize('restricted, research_mode, displayed', [
    (True, False, ''),
    (False, False, 'Live'),
    (False, True, 'research mode'),
    (True, True, 'research mode')
])
def test_should_show_research_and_restricted_mode(
    restricted,
    research_mode,
    displayed,
    app_,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
    fake_uuid
):
    services = [service_json(fake_uuid, 'My Service', [], restricted=restricted, research_mode=research_mode)]
    services[0]['statistics'] = create_stats()

    mock_get_detailed_services.return_value = {'data': services}
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    mock_get_detailed_services.assert_called_once_with({'detailed': True})
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    # get second column, which contains flags as text.
    assert page.tbody.select('td:nth-of-type(2)')[0].text.strip() == displayed


def test_should_render_platform_admin_page(
    app_,
    platform_admin_user,
    mocker,
    mock_get_detailed_services,
):
    with app_.test_request_context():
        with app_.test_client() as client:
            mock_get_user(mocker, user=platform_admin_user)
            client.login(platform_admin_user)
            response = client.get(url_for('main.platform_admin'))

    assert response.status_code == 200
    resp_data = response.get_data(as_text=True)
    assert 'Platform admin' in resp_data
    assert 'Today' in resp_data
    assert 'Services' in resp_data
    mock_get_detailed_services.assert_called_once_with({'detailed': True})


def test_create_global_stats_sets_failure_rates(fake_uuid):
    services = [
        service_json(fake_uuid, 'a', []),
        service_json(fake_uuid, 'b', [])
    ]
    services[0]['statistics'] = create_stats(
            emails_requested=1,
            emails_delivered=1,
            emails_failed=0,
    )
    services[1]['statistics'] = create_stats(
            emails_requested=2,
            emails_delivered=1,
            emails_failed=1,
    )

    stats = create_global_stats(services)

    assert stats == {
        'email': {
            'delivered': 2,
            'failed': 1,
            'requested': 3,
            'failure_rate': '33.3'
        },
        'sms': {
            'delivered': 0,
            'failed': 0,
            'requested': 0,
            'failure_rate': '0'
        }
    }


def create_stats(
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0
):
    return {
        'sms': {
            'requested': sms_requested,
            'delivered': sms_delivered,
            'failed': sms_failed,
        },
        'email': {
            'requested': emails_requested,
            'delivered': emails_delivered,
            'failed': emails_failed,
        }
    }


def test_format_stats_by_service_sums_values_for_sending(fake_uuid):
    services = [service_json(fake_uuid, 'a', [])]
    services[0]['statistics'] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11
    )

    ret = list(format_stats_by_service(services))

    assert len(ret) == 1
    assert ret[0]['sending'] == 34
    assert ret[0]['delivered'] == 10
    assert ret[0]['failed'] == 16
