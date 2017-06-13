import json
import uuid
from urllib.parse import urlparse, quote, parse_qs

import pytest
from flask import url_for
from bs4 import BeautifulSoup

from app.main.views.jobs import get_time_left, get_status_filters
from tests import notification_json
from tests.conftest import SERVICE_ONE_ID
from freezegun import freeze_time


@pytest.mark.parametrize(
    "message_type,page_title", [
        ('email', 'Emails'),
        ('sms', 'Text messages')
    ]
)
@pytest.mark.parametrize(
    "status_argument, expected_api_call", [
        (
            '',
            [
                'created', 'pending', 'sending',
                'delivered', 'sent',
                'failed', 'temporary-failure', 'permanent-failure', 'technical-failure',
            ]
        ),
        (
            'sending',
            ['sending', 'created', 'pending']
        ),
        (
            'delivered',
            ['delivered', 'sent']
        ),
        (
            'failed',
            ['failed', 'temporary-failure', 'permanent-failure', 'technical-failure']
        )
    ]
)
@pytest.mark.parametrize(
    "page_argument, expected_page_argument", [
        (1, 1),
        (22, 22),
        (None, 1)
    ]
)
@pytest.mark.parametrize(
    "to_argument, expected_to_argument", [
        ('', ''),
        ('+447900900123', '+447900900123'),
        ('test@example.com', 'test@example.com'),
    ]
)
def test_can_show_notifications(
    logged_in_client,
    service_one,
    mock_get_notifications,
    mock_get_detailed_service,
    message_type,
    page_title,
    status_argument,
    expected_api_call,
    page_argument,
    expected_page_argument,
    to_argument,
    expected_to_argument,
):
    if expected_to_argument:
        response = logged_in_client.post(
            url_for(
                'main.view_notifications',
                service_id=service_one['id'],
                message_type=message_type,
                status=status_argument,
                page=page_argument,
            ),
            data={
                'to': to_argument
            }
        )
    else:
        response = logged_in_client.get(url_for(
            'main.view_notifications',
            service_id=service_one['id'],
            message_type=message_type,
            status=status_argument,
            page=page_argument,
        ))
    assert response.status_code == 200
    content = response.get_data(as_text=True)
    notifications = notification_json(service_one['id'])
    notification = notifications['notifications'][0]
    assert notification['to'] in content
    assert notification['status'] in content
    assert notification['template']['name'] in content
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    assert page_title in page.h1.text.strip()

    path_to_json = page.find("div", {'data-key': 'notifications'})['data-resource']

    url = urlparse(path_to_json)
    assert url.path == '/services/{}/notifications/{}.json'.format(service_one['id'], message_type)
    query_dict = parse_qs(url.query)
    if status_argument:
        assert query_dict['status'] == [status_argument]
    if expected_page_argument:
        assert query_dict['page'] == [str(expected_page_argument)]
    if to_argument:
        assert query_dict['to'] == [to_argument]

    mock_get_notifications.assert_called_with(
        limit_days=7,
        page=expected_page_argument,
        service_id=service_one['id'],
        status=expected_api_call,
        template_type=[message_type],
        to=expected_to_argument,
    )

    json_response = logged_in_client.get(url_for(
        'main.get_notifications_as_json',
        service_id=service_one['id'],
        message_type=message_type,
        status=status_argument
    ))
    json_content = json.loads(json_response.get_data(as_text=True))
    assert json_content.keys() == {'counts', 'notifications'}


@pytest.mark.parametrize((
    'initial_query_arguments,'
    'form_post_data,'
    'expected_status_field_value,'
    'expected_search_box_contents'
), [
    (
        {
            'message_type': 'sms',
        },
        {},
        'sending,delivered,failed',
        '',
    ),
    (
        {
            'message_type': 'sms',
        },
        {
            'to': '+33(0)5-12-34-56-78',
        },
        'sending,delivered,failed',
        '+33(0)5-12-34-56-78',
    ),
    (
        {
            'status': 'failed',
            'message_type': 'email',
            'page': '99',
        },
        {
            'to': 'test@example.com',
        },
        'failed',
        'test@example.com',
    ),
])
def test_search_recipient_form(
    logged_in_client,
    mock_get_notifications,
    mock_get_detailed_service,
    initial_query_arguments,
    form_post_data,
    expected_status_field_value,
    expected_search_box_contents,
):
    response = logged_in_client.post(
        url_for(
            'main.view_notifications',
            service_id=SERVICE_ONE_ID,
            **initial_query_arguments
        ),
        data=form_post_data
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    assert page.find("form")['method'] == 'post'
    action_url = page.find("form")['action']
    url = urlparse(action_url)
    assert url.path == '/services/{}/notifications/{}'.format(
        SERVICE_ONE_ID,
        initial_query_arguments['message_type']
    )
    query_dict = parse_qs(url.query)
    assert query_dict == {}

    assert page.find("input", {'name': 'status'})['value'] == expected_status_field_value
    assert page.find("input", {'name': 'to'})['value'] == expected_search_box_contents


def test_should_show_notifications_for_a_service_with_next_previous(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications_with_previous_next,
    mock_get_detailed_service,
    mocker,
):
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='sms',
        page=2
    ))
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    next_page_link = page.find('a', {'rel': 'next'})
    prev_page_link = page.find('a', {'rel': 'previous'})
    assert (
        url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=3) in
        next_page_link['href']
    )
    assert 'Next page' in next_page_link.text.strip()
    assert 'page 3' in next_page_link.text.strip()
    assert (
        url_for('main.view_notifications', service_id=service_one['id'], message_type='sms', page=1) in
        prev_page_link['href']
    )
    assert 'Previous page' in prev_page_link.text.strip()
    assert 'page 1' in prev_page_link.text.strip()


@pytest.mark.parametrize(
    "job_created_at, expected_message", [
        ("2016-01-10 11:09:00.000000+00:00", "Data available for 7 days"),
        ("2016-01-04 11:09:00.000000+00:00", "Data available for 1 day"),
        ("2016-01-03 11:09:00.000000+00:00", "Data available for 11 hours"),
        ("2016-01-02 23:59:59.000000+00:00", "Data no longer available")
    ]
)
@freeze_time("2016-01-10 12:00:00.000000")
def test_time_left(job_created_at, expected_message):
    assert get_time_left(job_created_at) == expected_message


STATISTICS = {
    'sms': {
        'requested': 6,
        'failed': 2,
        'delivered': 1
    }
}


def test_get_status_filters_calculates_stats(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert {label: count for label, _option, _link, count in ret} == {
        'total': 6,
        'sending': 3,
        'failed': 2,
        'delivered': 1
    }


def test_get_status_filters_in_right_order(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    assert [label for label, _option, _link, _count in ret] == [
        'total', 'sending', 'delivered', 'failed'
    ]


def test_get_status_filters_constructs_links(client):
    ret = get_status_filters({'id': 'foo'}, 'sms', STATISTICS)

    link = ret[0][2]
    assert link == '/services/foo/notifications/sms?status={}'.format(quote('sending,delivered,failed'))


def test_html_contains_notification_id(
    logged_in_client,
    service_one,
    active_user_with_permissions,
    mock_get_notifications,
    mock_get_detailed_service,
    mocker,
):
    response = logged_in_client.get(url_for(
        'main.view_notifications',
        service_id=service_one['id'],
        message_type='sms',
        status='')
    )
    assert response.status_code == 200
    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    notifications = page.tbody.find_all('tr')
    for tr in notifications:
        assert uuid.UUID(tr.attrs['id'])
