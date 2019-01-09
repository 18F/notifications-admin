# -*- coding: utf-8 -*-
import base64
import io
import os
from datetime import datetime, timedelta

from dateutil import parser
from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)
from flask_login import login_required
from notifications_python_client.errors import APIError
from notifications_utils.letter_timings import (
    get_letter_timings,
    letter_can_be_cancelled,
)
from notifications_utils.pdf import pdf_page_count
from notifications_utils.timezones import utc_string_to_aware_gmt_datetime
from PyPDF2.utils import PdfReadError

from app import (
    _format_datetime_short,
    current_service,
    format_date_numeric,
    job_api_client,
    notification_api_client,
)
from app.main import main
from app.notify_client.api_key_api_client import KEY_TYPE_TEST
from app.template_previews import get_page_count_for_letter
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    generate_notifications_csv,
    get_help_argument,
    get_template,
    parse_filter_args,
    printing_today_or_tomorrow,
    set_status_filters,
    user_has_permissions,
)


@main.route("/services/<service_id>/notification/<uuid:notification_id>")
@login_required
@user_has_permissions('view_activity', 'send_messages')
def view_notification(service_id, notification_id):
    notification = notification_api_client.get_notification(service_id, str(notification_id))
    notification['template'].update({'reply_to_text': notification['reply_to_text']})

    personalisation = get_all_personalisation_from_notification(notification)

    if notification['template']['is_precompiled_letter']:
        try:
            file_contents = view_letter_notification_as_preview(service_id, notification_id, "pdf")
            page_count = pdf_page_count(io.BytesIO(file_contents))
        except PdfReadError:
            return render_template(
                'views/notifications/invalid_precompiled_letter.html',
                created_at=notification['created_at']
            )
    else:
        page_count = get_page_count_for_letter(notification['template'], values=personalisation)

    template = get_template(
        notification['template'],
        current_service,
        letter_preview_url=url_for(
            '.view_letter_notification_as_preview',
            service_id=service_id,
            notification_id=notification_id,
            filetype='png',
        ),
        expand_emails=True,
        page_count=page_count,
        show_recipient=True,
        redact_missing_personalisation=True,
    )
    template.values = personalisation
    if notification['job']:
        job = job_api_client.get_job(service_id, notification['job']['id'])['data']
    else:
        job = None

    letter_print_day = get_letter_printing_statement(notification['status'], notification['created_at'])

    notification_created = parser.parse(notification['created_at']).replace(tzinfo=None)

    show_cancel_button = notification['notification_type'] == 'letter' and \
        letter_can_be_cancelled(notification['status'], notification_created)

    return render_template(
        'views/notifications/notification.html',
        finished=(notification['status'] in (DELIVERED_STATUSES + FAILURE_STATUSES)),
        notification_status=notification['status'],
        uploaded_file_name='Report',
        template=template,
        job=job,
        updates_url=url_for(
            ".view_notification_updates",
            service_id=service_id,
            notification_id=notification['id'],
            status=request.args.get('status'),
            help=get_help_argument()
        ),
        partials=get_single_notification_partials(notification),
        created_by=notification.get('created_by'),
        created_at=notification['created_at'],
        updated_at=notification['updated_at'],
        help=get_help_argument(),
        estimated_letter_delivery_date=get_letter_timings(
            notification['created_at'],
            postage=notification['postage']
        ).earliest_delivery,
        notification_id=notification['id'],
        postage=notification['postage'],
        can_receive_inbound=(current_service.has_permission('inbound_sms')),
        is_precompiled_letter=notification['template']['is_precompiled_letter'],
        letter_print_day=letter_print_day,
        show_cancel_button=show_cancel_button
    )


@main.route("/services/<service_id>/notification/<uuid:notification_id>/cancel", methods=['GET', 'POST'])
@login_required
@user_has_permissions('view_activity', 'send_messages')
def cancel_letter(service_id, notification_id):

    if request.method == 'POST':
        notification_api_client.update_notification_to_cancelled(current_service.id, notification_id)
        return redirect(url_for('main.view_notification', service_id=service_id, notification_id=notification_id))

    flash("Are you sure you want to cancel sending this letter?", 'cancel')
    return view_notification(service_id, notification_id)


def get_letter_printing_statement(status, created_at):
    created_at_dt = parser.parse(created_at).replace(tzinfo=None)

    if letter_can_be_cancelled(status, created_at_dt):
        return 'Printing starts {} at 5.30pm'.format(printing_today_or_tomorrow())
    else:
        printed_datetime = utc_string_to_aware_gmt_datetime(created_at) + timedelta(hours=6, minutes=30)
        printed_date = _format_datetime_short(printed_datetime)

        return 'Printed on {}'.format(printed_date)


def get_preview_error_image():
    path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "images", "preview_error.png")
    with open(path, "rb") as file:
        return file.read()


@main.route("/services/<service_id>/notification/<uuid:notification_id>.<filetype>")
@login_required
@user_has_permissions('view_activity')
def view_letter_notification_as_preview(service_id, notification_id, filetype):

    if filetype not in ('pdf', 'png'):
        abort(404)

    try:
        preview = notification_api_client.get_notification_letter_preview(
            service_id,
            notification_id,
            filetype,
            page=request.args.get('page')
        )

        display_file = base64.b64decode(preview['content'])
    except APIError:
        display_file = get_preview_error_image()

    return display_file


@main.route("/services/<service_id>/notification/<notification_id>.json")
@user_has_permissions('view_activity', 'send_messages')
def view_notification_updates(service_id, notification_id):
    return jsonify(**get_single_notification_partials(
        notification_api_client.get_notification(service_id, notification_id)
    ))


def get_single_notification_partials(notification):
    return {
        'status': render_template(
            'partials/notifications/status.html',
            notification=notification,
            sent_with_test_key=(
                notification.get('key_type') == KEY_TYPE_TEST
            ),
        ),
    }


def get_all_personalisation_from_notification(notification):

    if notification['template'].get('redact_personalisation'):
        notification['personalisation'] = {}

    if notification['template']['template_type'] == 'email':
        notification['personalisation']['email_address'] = notification['to']

    if notification['template']['template_type'] == 'sms':
        notification['personalisation']['phone_number'] = notification['to']

    return notification['personalisation']


@main.route("/services/<service_id>/download-notifications.csv")
@login_required
@user_has_permissions('view_activity')
def download_notifications_csv(service_id):
    filter_args = parse_filter_args(request.args)
    filter_args['status'] = set_status_filters(filter_args)

    service_data_retention_days = current_service.get_days_of_retention(filter_args.get('message_type')[0])
    return Response(
        stream_with_context(
            generate_notifications_csv(
                service_id=service_id,
                job_id=None,
                status=filter_args.get('status'),
                page=request.args.get('page', 1),
                page_size=10000,
                format_for_csv=True,
                template_type=filter_args.get('message_type'),
                limit_days=service_data_retention_days,
            )
        ),
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'inline; filename="{} - {} - {} report.csv"'.format(
                format_date_numeric(datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")),
                filter_args['message_type'][0],
                current_service.name)
        }
    )
