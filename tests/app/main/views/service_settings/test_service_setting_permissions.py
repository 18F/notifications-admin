import functools

import pytest
from flask import url_for

from app.main.views.service_settings import PLATFORM_ADMIN_SERVICE_PERMISSIONS
from tests.conftest import SERVICE_ONE_ID, normalize_spaces, set_config


@pytest.fixture
def get_service_settings_page(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_inbound_number_for_service,
    mock_get_all_letter_branding,
    mock_get_organisation,
    mock_get_free_sms_fragment_limit,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    single_sms_sender,
    mock_get_service_data_retention,
):
    client_request.login(platform_admin_user)
    return functools.partial(client_request.get, 'main.service_settings', service_id=service_one['id'])


def test_service_set_permission_requires_platform_admin(
    mocker,
    client_request,
    service_one,
    mock_get_inbound_number_for_service,
):
    client_request.post(
        'main.service_set_permission', service_id=service_one['id'], permission='email_auth',
        _data={'enabled': 'True'},
        _expected_status=403
    )


@pytest.mark.parametrize('initial_permissions, permission, form_data, expected_update', [
    (
        [],
        'inbound_sms',
        'True',
        ['inbound_sms'],
    ),
    (
        ['inbound_sms'],
        'inbound_sms',
        'False',
        [],
    ),
    (
        [],
        'email_auth',
        'True',
        ['email_auth'],
    ),
    (
        ['email_auth'],
        'email_auth',
        'False',
        [],
    ),
    (
        [],
        'international_letters',
        'True',
        ['international_letters'],
    ),
    (
        ['international_letters'],
        'international_letters',
        'False',
        [],
    ),
    (
        ['email', 'sms', 'letter', 'international_sms', 'international_letters'],
        'broadcast',
        'True',
        ['international_sms', 'international_letters', 'broadcast'],
    ),
    (
        ['broadcast', 'international_sms', 'international_letters'],
        'broadcast',
        'False',
        ['international_sms', 'international_letters'],
    ),
])
def test_service_set_permission(
    mocker,
    platform_admin_client,
    service_one,
    mock_get_inbound_number_for_service,
    permission,
    initial_permissions,
    form_data,
    expected_update,
):
    service_one['permissions'] = initial_permissions
    mock_update_service = mocker.patch('app.service_api_client.update_service')
    response = platform_admin_client.post(
        url_for('main.service_set_permission', service_id=service_one['id'], permission=permission),
        data={'enabled': form_data}
    )
    assert response.status_code == 302
    assert response.location == url_for('main.service_settings', service_id=service_one['id'], _external=True)

    assert mock_update_service.call_args[0][0] == service_one['id']
    new_permissions = mock_update_service.call_args[1]['permissions']
    assert len(new_permissions) == len(set(new_permissions))
    assert set(new_permissions) == set(expected_update)


@pytest.mark.parametrize('service_fields, endpoint, kwargs, text', [
    ({'restricted': True}, '.service_switch_live', {}, 'Live Off Change service status'),
    ({'restricted': False}, '.service_switch_live', {}, 'Live On Change service status'),
    ({'permissions': ['sms']}, '.service_set_inbound_number', {},
        'Receive inbound SMS Off Change your settings for Receive inbound SMS'),
    ({'permissions': ['letter']},
     '.service_set_permission', {'permission': 'upload_letters'},
        'Uploading letters Off Change your settings for Uploading letters'),
    ({'permissions': ['letter']},
     '.service_set_permission', {'permission': 'international_letters'},
        'Send international letters Off Change your settings for Send international letters'),
])
def test_service_setting_toggles_show(
    mocker,
    mock_get_service_organisation,
    get_service_settings_page,
    service_one,
    service_fields,
    endpoint,
    kwargs,
    text,
):
    link_url = url_for(endpoint, **kwargs, service_id=service_one['id'])
    service_one.update(service_fields)
    page = get_service_settings_page()
    assert normalize_spaces(page.find('a', {'href': link_url}).find_parent('tr').text.strip()) == text


@pytest.mark.parametrize('service_fields, endpoint, index, text', [
    ({'active': True}, '.archive_service', 0, 'Delete this service'),
    ({'active': True}, '.suspend_service', 1, 'Suspend service'),
    ({'active': False}, '.resume_service', 0, 'Resume service'),
    pytest.param(
        {'active': False}, '.archive_service', 1, 'Resume service',
        marks=pytest.mark.xfail(raises=IndexError)
    )
])
def test_service_setting_link_toggles(
    get_service_settings_page,
    service_one,
    service_fields,
    endpoint,
    index,
    text,
):
    link_url = url_for(endpoint, service_id=service_one['id'])
    service_one.update(service_fields)
    page = get_service_settings_page()
    link = page.select('.page-footer-delete-link a')[index]
    assert normalize_spaces(link.text) == text
    assert link['href'] == link_url


@pytest.mark.parametrize('permissions,permissions_text,visible', [
    ('sms', 'inbound SMS', True),
    ('inbound_sms', 'inbound SMS', False),                 # no sms parent permission
    # also test no permissions set
    ('', 'inbound SMS', False),
])
def test_service_settings_doesnt_show_option_if_parent_permission_disabled(
    get_service_settings_page,
    service_one,
    permissions,
    permissions_text,
    visible
):
    service_one['permissions'] = [permissions]
    page = get_service_settings_page()
    cells = page.find_all('td')
    assert any(cell for cell in cells if permissions_text in cell.text) is visible


@pytest.mark.parametrize('service_fields, link_text', [
    # can't archive or suspend inactive service. Can't resume active service.
    ({'active': False}, 'Archive service'),
    ({'active': False}, 'Suspend service'),
    ({'active': True}, 'Resume service'),
])
def test_service_setting_toggles_dont_show(get_service_settings_page, service_one, service_fields, link_text):
    service_one.update(service_fields)
    page = get_service_settings_page()
    toggles = page.find_all('a', {'class': 'govuk-link'})
    assert not any(link for link in toggles if link_text in link.text)


def test_normal_user_doesnt_see_any_platform_admin_settings(
    client_request,
    service_one,
    no_reply_to_email_addresses,
    no_letter_contact_blocks,
    mock_get_organisation,
    single_sms_sender,
    mock_get_all_letter_branding,
    mock_get_inbound_number_for_service,
    mock_get_free_sms_fragment_limit,
    mock_get_service_data_retention
):
    page = client_request.get('main.service_settings', service_id=service_one['id'])
    platform_admin_settings = [permission['title'] for permission in PLATFORM_ADMIN_SERVICE_PERMISSIONS.values()]

    for permission in platform_admin_settings:
        assert permission not in page


def test_setting_broadcast_sets_organisation_if_config_value_set(
    mock_update_service_organisation,
    mock_update_service,
    platform_admin_client,
    fake_uuid,
):
    with set_config(platform_admin_client.application, 'BROADCAST_ORGANISATION_ID', fake_uuid):
        response = platform_admin_client.post(
            url_for('main.service_set_permission', service_id=SERVICE_ONE_ID, permission='broadcast'),
            data={'enabled': True}
        )
        assert response.status_code == 302
        assert response.location == url_for('main.service_settings', service_id=SERVICE_ONE_ID, _external=True)

    mock_update_service_organisation.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        org_id=fake_uuid
    )


def test_setting_broadcast_doesnt_set_organisation_if_config_value_not_set(
    mock_update_service_organisation,
    mock_update_service,
    platform_admin_client,
):
    with set_config(platform_admin_client.application, 'BROADCAST_ORGANISATION_ID', None):
        response = platform_admin_client.post(
            url_for('main.service_set_permission', service_id=SERVICE_ONE_ID, permission='broadcast'),
            data={'enabled': True}
        )
        assert response.status_code == 302
        assert response.location == url_for('main.service_settings', service_id=SERVICE_ONE_ID, _external=True)
    assert not mock_update_service_organisation.called
