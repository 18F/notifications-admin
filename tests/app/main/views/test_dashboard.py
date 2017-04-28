from functools import partial
import copy
from unittest.mock import call, ANY

from flask import url_for
import pytest
from bs4 import BeautifulSoup
from freezegun import freeze_time

from app.main.views.dashboard import (
    get_dashboard_totals,
    format_monthly_stats_to_list,
    get_free_paid_breakdown_for_billable_units,
    aggregate_status_types,
    format_template_stats_to_list,
    get_tuples_of_financial_years,
    get_dashboard_partials
)

from tests import validate_route_permission
from tests.conftest import SERVICE_ONE_ID
from tests.app.test_utils import normalize_spaces

stub_template_stats = [
    {
        'template_type': 'sms',
        'template_name': 'one',
        'template_id': 'id-1',
        'count': 100
    },
    {
        'template_type': 'email',
        'template_name': 'two',
        'template_id': 'id-2',
        'count': 200
    }
]


def test_get_started(
    logged_in_client,
    mocker,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_jobs,
    mock_get_detailed_service,
    mock_get_usage,
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates_when_no_templates_exist.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' in response.get_data(as_text=True)


def test_get_started_is_hidden_once_templates_exist(
    logged_in_client,
    mocker,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_detailed_service,
    mock_get_usage,
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    # mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
    assert response.status_code == 200
    assert 'Get started' not in response.get_data(as_text=True)


def test_should_show_recent_templates_on_dashboard(
    logged_in_client,
    mocker,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_detailed_service,
    mock_get_usage,
):
    mock_template_stats = mocker.patch('app.template_statistics_client.get_template_statistics_for_service',
                                       return_value=copy.deepcopy(stub_template_stats))

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200
    response.get_data(as_text=True)
    mock_template_stats.assert_called_once_with(SERVICE_ONE_ID, limit_days=7)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    headers = [header.text.strip() for header in page.find_all('h2') + page.find_all('h1')]
    assert 'In the last 7 days' in headers

    table_rows = page.find_all('tbody')[1].find_all('tr')

    assert len(table_rows) == 2

    assert 'two' in table_rows[0].find_all('th')[0].text
    assert 'Email template' in table_rows[0].find_all('th')[0].text
    assert '200' in table_rows[0].find_all('td')[0].text

    assert 'one' in table_rows[1].find_all('th')[0].text
    assert 'Text message template' in table_rows[1].find_all('th')[0].text
    assert '100' in table_rows[1].find_all('td')[0].text


@freeze_time("2016-07-01 12:00")  # 4 months into 2016 financial year
@pytest.mark.parametrize('partial_url', [
    partial(url_for),
    partial(url_for, year='2016'),
])
def test_should_show_monthly_breakdown_of_template_usage(
    logged_in_client,
    mock_get_monthly_template_statistics,
    partial_url,
):
    response = logged_in_client.get(
        partial_url('main.template_history', service_id=SERVICE_ONE_ID, _external=True)
    )

    assert response.status_code == 200
    mock_get_monthly_template_statistics.assert_called_once_with(SERVICE_ONE_ID, 2016)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    table_rows = page.select('tbody tr')

    assert ' '.join(table_rows[0].text.split()) == (
        'My first template '
        'Text message template '
        '2'
    )

    assert len(table_rows) == len(['April'])
    assert len(page.select('.table-no-data')) == len(['May', 'June', 'July'])


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_upcoming_jobs_on_dashboard(
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_get_usage,
):
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    first_call = mock_get_jobs.call_args_list[0]
    assert first_call[0] == (SERVICE_ONE_ID,)
    assert first_call[1]['statuses'] == ['scheduled']

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    table_rows = page.find_all('tbody')[0].find_all('tr')
    assert len(table_rows) == 2

    assert 'send_me_later.csv' in table_rows[0].find_all('th')[0].text
    assert 'Sending today at 11:09am' in table_rows[0].find_all('th')[0].text
    assert table_rows[0].find_all('td')[0].text.strip() == '1'
    assert 'even_later.csv' in table_rows[1].find_all('th')[0].text
    assert 'Sending today at 11:09pm' in table_rows[1].find_all('th')[0].text
    assert table_rows[1].find_all('td')[0].text.strip() == '1'


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_recent_jobs_on_dashboard(
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_get_usage,
):
    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    second_call = mock_get_jobs.call_args_list[1]
    assert second_call[0] == (SERVICE_ONE_ID,)
    assert second_call[1]['limit_days'] == 7
    assert 'scheduled' not in second_call[1]['statuses']

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    table_rows = page.find_all('tbody')[2].find_all('tr')

    assert len(table_rows) == 4

    for index, filename in enumerate((
            "export 1/1/2016.xls",
            "all email addresses.xlsx",
            "applicants.ods",
            "thisisatest.csv",
    )):
        assert filename in table_rows[index].find_all('th')[0].text
        assert 'Sent 1 January at 11:09' in table_rows[index].find_all('th')[0].text
        for column_index, count in enumerate((1, 0, 0)):
            assert table_rows[index].find_all('td')[column_index].text.strip() == str(count)


@freeze_time("2012-03-31 12:12:12")
def test_usage_page(
    logged_in_client,
    mock_get_usage,
    mock_get_billable_units,
):
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_usage.assert_called_once_with(SERVICE_ONE_ID, 2011)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-half'})
    nav = page.find('ul', {'class': 'pill', 'role': 'tablist'})
    nav_links = nav.find_all('a')

    assert normalize_spaces(nav_links[0].text) == '2010 to 2011 financial year'
    assert normalize_spaces(nav.find('li', {'aria-selected': 'true'}).text) == '2011 to 2012 financial year'
    assert normalize_spaces(nav_links[1].text) == '2012 to 2013 financial year'

    assert '123' in cols[0].text
    assert 'Emails' in cols[0].text

    assert '456,123' in cols[1].text
    assert 'Text messages' in cols[1].text

    table = page.find('table').text.strip()

    assert 'April' in table
    assert 'March' in table
    assert '123 free text messages' in table
    assert '£3,403.06' in table
    assert '249,877 free text messages' in table
    assert '206,246 text messages at 1.65p' in table


@freeze_time("2012-03-31 12:12:12")
def test_international_usage_page(
    logged_in_client,
    mock_get_international_usage,
    mock_get_billable_international_units,
):
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    mock_get_billable_international_units.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_international_usage.assert_called_once_with(SERVICE_ONE_ID, 2011)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-half'})
    nav = page.find('ul', {'class': 'pill', 'role': 'tablist'})
    nav_links = nav.find_all('a')

    assert normalize_spaces(nav_links[0].text) == '2010 to 2011 financial year'
    assert normalize_spaces(nav.find('li', {'aria-selected': 'true'}).text) == '2011 to 2012 financial year'
    assert normalize_spaces(nav_links[1].text) == '2012 to 2013 financial year'

    assert '0' in cols[0].text
    assert 'Emails' in cols[0].text

    assert '252,390' in cols[1].text
    assert 'Text messages' in cols[1].text

    table = page.find('table').text.strip()

    print(table)

    assert '249,900 UK free text messages' in table
    assert '100 international free text messages' in table
    assert '900 international text messages at 1.65p' in table
    assert 'April' in table
    assert 'March' in table
    assert '£20.30' in table
    assert '£19.14' in table


@freeze_time("2012-03-31 12:12:12")
def test_international_usage_page(
    logged_in_client,
    mock_get_international_usage,
    mock_get_billable_international_units,
):
    response = logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    mock_get_billable_international_units.assert_called_once_with(SERVICE_ONE_ID, 2011)
    mock_get_international_usage.assert_called_once_with(SERVICE_ONE_ID, 2011)

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')

    cols = page.find_all('div', {'class': 'column-half'})
    nav = page.find('ul', {'class': 'pill', 'role': 'tablist'})
    nav_links = nav.find_all('a')

    assert '252,390' in cols[1].text
    assert 'Text messages' in cols[1].text

    table = page.find('table').text.strip()

    print(table)

    assert '249,900 UK free text messages' in table
    assert '100 international free text messages' in table
    assert '900 international text messages at 1.65p' in table
    assert 'April' in table
    assert 'March' in table
    assert '£20.30' in table
    assert '£19.14' in table


def test_usage_page_with_year_argument(
    logged_in_client,
    mock_get_usage,
    mock_get_billable_units
):
    assert logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year=2000)).status_code == 200
    mock_get_billable_units.assert_called_once_with(SERVICE_ONE_ID, 2000)
    mock_get_usage.assert_called_once_with(SERVICE_ONE_ID, 2000)


def test_usage_page_for_invalid_year(
    logged_in_client,
):
    assert logged_in_client.get(url_for('main.usage', service_id=SERVICE_ONE_ID, year='abcd')).status_code == 404


def _test_dashboard_menu(mocker, app_, usr, service, permissions):
    with app_.test_request_context():
        with app_.test_client() as client:
            usr._permissions[str(service['id'])] = permissions
            mocker.patch('app.user_api_client.check_verify_code', return_value=(True, ''))
            mocker.patch('app.service_api_client.get_services', return_value={'data': [service]})
            mocker.patch('app.user_api_client.get_user', return_value=usr)
            mocker.patch('app.user_api_client.get_user_by_email', return_value=usr)
            mocker.patch('app.service_api_client.get_service', return_value={'data': service})
            client.login(usr)
            return client.get(url_for('main.service_dashboard', service_id=service['id']))


def test_menu_send_messages(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_usage,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'send_texts', 'send_emails', 'send_letters'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page

        assert url_for('main.service_settings', service_id=service_one['id']) not in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page
        assert url_for('main.view_providers') not in page


def test_menu_manage_service(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_usage,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_users', 'manage_templates', 'manage_settings'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page

        assert url_for('main.api_keys', service_id=service_one['id']) not in page


def test_menu_manage_api_keys(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_usage,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            api_user_active,
            service_one,
            ['view_activity', 'manage_api_keys'])
        page = resp.get_data(as_text=True)
        assert url_for(
            'main.choose_template',
            service_id=service_one['id'],
        ) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) not in page

        assert url_for('main.api_integration', service_id=service_one['id']) in page


def test_menu_all_services_for_platform_admin_user(
    mocker,
    app_,
    platform_admin_user,
    service_one,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_usage,
):
    with app_.test_request_context():
        resp = _test_dashboard_menu(
            mocker,
            app_,
            platform_admin_user,
            service_one,
            [])
        page = resp.get_data(as_text=True)
        assert url_for('main.choose_template', service_id=service_one['id']) in page
        assert url_for('main.manage_users', service_id=service_one['id']) in page
        assert url_for('main.service_settings', service_id=service_one['id']) in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='email') in page
        assert url_for('main.view_notifications', service_id=service_one['id'], message_type='sms') in page
        assert url_for('main.api_keys', service_id=service_one['id']) not in page


def test_route_for_service_permissions(
    mocker,
    app_,
    api_user_active,
    service_one,
    mock_get_service,
    mock_get_user,
    mock_get_service_templates,
    mock_get_jobs,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_usage,
):
    with app_.test_request_context():
        validate_route_permission(
            mocker,
            app_,
            "GET",
            200,
            url_for('main.service_dashboard', service_id=service_one['id']),
            ['view_activity'],
            api_user_active,
            service_one)


def test_aggregate_template_stats():
    from app.main.views.dashboard import aggregate_usage
    expected = aggregate_usage(copy.deepcopy(stub_template_stats))

    assert len(expected) == 2
    assert expected[0]['template_name'] == 'two'
    assert expected[0]['count'] == 200
    assert expected[0]['template_id'] == 'id-2'
    assert expected[0]['template_type'] == 'email'
    assert expected[1]['template_name'] == 'one'
    assert expected[1]['count'] == 100
    assert expected[1]['template_id'] == 'id-1'
    assert expected[1]['template_type'] == 'sms'


def test_service_dashboard_updates_gets_dashboard_totals(
    mocker,
    logged_in_client,
    mock_get_service_templates,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_get_usage,
):
    mocker.patch('app.main.views.dashboard.get_dashboard_totals', return_value={
        'email': {'requested': 123, 'delivered': 0, 'failed': 0},
        'sms': {'requested': 456, 'delivered': 0, 'failed': 0}
    })

    response = logged_in_client.get(url_for('main.service_dashboard', service_id=SERVICE_ONE_ID))

    assert response.status_code == 200

    page = BeautifulSoup(response.data.decode('utf-8'), 'html.parser')
    numbers = [number.text.strip() for number in page.find_all('div', class_='big-number-number')]
    assert '123' in numbers
    assert '456' in numbers


def test_get_dashboard_totals_adds_percentages():
    stats = {
        'sms': {
            'requested': 3,
            'delivered': 0,
            'failed': 2
        },
        'email': {
            'requested': 0,
            'delivered': 0,
            'failed': 0
        }
    }
    assert get_dashboard_totals(stats)['sms']['failed_percentage'] == '66.7'
    assert get_dashboard_totals(stats)['email']['failed_percentage'] == '0'


@pytest.mark.parametrize(
    'failures,expected', [
        (2, False),
        (3, False),
        (4, True)
    ]
)
def test_get_dashboard_totals_adds_warning(failures, expected):
    stats = {
        'sms': {
            'requested': 100,
            'delivered': 0,
            'failed': failures
        }
    }
    assert get_dashboard_totals(stats)['sms']['show_warning'] == expected


def test_format_monthly_stats_empty_case():
    assert format_monthly_stats_to_list({}) == []


def test_format_monthly_stats_labels_month():
    resp = format_monthly_stats_to_list({'2016-07': {}})
    assert resp[0]['name'] == 'July'


def test_format_monthly_stats_has_stats_with_failure_rate():
    resp = format_monthly_stats_to_list({
        '2016-07': {'sms': _stats(3, 1, 2)}
    })
    assert resp[0]['sms_counts'] == {
        'failed': 2,
        'failed_percentage': '66.7',
        'requested': 3,
        'show_warning': True,
    }


def test_format_monthly_stats_works_for_email_letter():
    resp = format_monthly_stats_to_list({
        '2016-07': {
            'sms': {},
            'email': {},
            'letter': {},
        }
    })
    assert isinstance(resp[0]['sms_counts'], dict)
    assert isinstance(resp[0]['email_counts'], dict)
    assert isinstance(resp[0]['letter_counts'], dict)


def _stats(requested, delivered, failed):
    return {'requested': requested, 'delivered': delivered, 'failed': failed}


@pytest.mark.parametrize('dict_in, expected_failed, expected_requested', [
    (
        {},
        0,
        0
    ),
    (
        {'temporary-failure': 1, 'permanent-failure': 1, 'technical-failure': 1},
        3,
        3,
    ),
    (
        {'created': 1, 'pending': 1, 'sending': 1, 'delivered': 1},
        0,
        4,
    ),
])
def test_aggregate_status_types(dict_in, expected_failed, expected_requested):
    sms_counts = aggregate_status_types({'sms': dict_in})['sms_counts']
    assert sms_counts['failed'] == expected_failed
    assert sms_counts['requested'] == expected_requested


@pytest.mark.parametrize(
    'now, expected_number_of_months', [
        (freeze_time("2017-12-31 11:09:00.061258"), 12),
        (freeze_time("2017-01-01 11:09:00.061258"), 10)
    ]
)
def test_get_free_paid_breakdown_for_billable_units(now, expected_number_of_months):
    with now:
        assert list(get_free_paid_breakdown_for_billable_units(
            2016, {
                'April': 100000,
                'May': 100000,
                'June': 100000,
                'February': 1234
            }
        )) == [
            {'name': 'April', 'free': 100000, 'paid': 0},
            {'name': 'May', 'free': 100000, 'paid': 0},
            {'name': 'June', 'free': 50000, 'paid': 50000},
            {'name': 'July', 'free': 0, 'paid': 0},
            {'name': 'August', 'free': 0, 'paid': 0},
            {'name': 'September', 'free': 0, 'paid': 0},
            {'name': 'October', 'free': 0, 'paid': 0},
            {'name': 'November', 'free': 0, 'paid': 0},
            {'name': 'December', 'free': 0, 'paid': 0},
            {'name': 'January', 'free': 0, 'paid': 0},
            {'name': 'February', 'free': 0, 'paid': 1234},
            {'name': 'March', 'free': 0, 'paid': 0}
        ][:expected_number_of_months]


def test_format_template_stats_to_list_with_no_stats():
    assert list(format_template_stats_to_list({})) == []


def test_format_template_stats_to_list():
    counts = {
        'created': 1,
        'pending': 1,
        'delivered': 1,
        'failed': 1,
        'temporary-failure': 1,
        'permanent-failure': 1,
        'technical-failure': 1,
        'do-not-count': 999,
    }
    stats_list = list(format_template_stats_to_list({
        'template_2_id': {
            'counts': {},
            'name': 'bar',
        },
        'template_1_id': {
            'counts': counts,
            'name': 'foo',
        },
    }))

    # we don’t care about the order of this function’s output
    assert len(stats_list) == 2
    assert {
        'counts': counts,
        'name': 'foo',
        'requested_count': 7,
        'id': 'template_1_id',
    } in stats_list
    assert {
        'counts': {},
        'name': 'bar',
        'requested_count': 0,
        'id': 'template_2_id',
    } in stats_list


def test_get_tuples_of_financial_years():
    assert list(get_tuples_of_financial_years(
        lambda year: 'http://example.com?year={}'.format(year),
        start=2040,
        end=2041,
    )) == [
        ('financial year', 2040, 'http://example.com?year=2040', '2040 to 2041'),
        ('financial year', 2041, 'http://example.com?year=2041', '2041 to 2042'),
    ]


def test_get_tuples_of_financial_years_defaults_to_2015():
    assert 2015 in list(get_tuples_of_financial_years(
        lambda year: 'http://example.com?year={}'.format(year),
        end=2040,
    ))[0]


@freeze_time("2016-01-01 11:09:00.061258")
def test_should_show_all_jobs_with_valid_statuses(
    logged_in_client,
    mock_get_template_statistics,
    mock_get_detailed_service,
    mock_get_jobs,
    mock_get_usage,
):
    get_dashboard_partials(service_id=SERVICE_ONE_ID)

    first_call = mock_get_jobs.call_args_list[0]
    # first call - scheduled jobs only
    assert first_call == call(ANY, statuses=['scheduled'])
    # second call - everything but scheduled and cancelled
    second_call = mock_get_jobs.call_args_list[1]
    assert second_call == call(ANY, limit_days=ANY, statuses={
        'pending',
        'in progress',
        'finished',
        'sending limits exceeded',
        'ready to send',
        'sent to dvla'
    })
