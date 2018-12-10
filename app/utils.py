import csv
import os
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from functools import wraps
from io import StringIO
from itertools import chain
from os import path
from urllib.parse import urlparse

import ago
import dateutil
import pyexcel
import yaml
from flask import (
    Markup,
    abort,
    current_app,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_utils.field import Field
from notifications_utils.formatters import make_quotes_smart
from notifications_utils.recipients import RecipientCSV
from notifications_utils.take import Take
from notifications_utils.template import (
    EmailPreviewTemplate,
    LetterImageTemplate,
    LetterPreviewTemplate,
    SMSPreviewTemplate,
)
from notifications_utils.timezones import convert_utc_to_bst
from orderedset._orderedset import OrderedSet
from werkzeug.datastructures import MultiDict

SENDING_STATUSES = ['created', 'pending', 'sending', 'pending-virus-check']
DELIVERED_STATUSES = ['delivered', 'sent', 'returned-letter']
FAILURE_STATUSES = ['failed', 'temporary-failure', 'permanent-failure',
                    'technical-failure', 'virus-scan-failed', 'cancelled']
REQUESTED_STATUSES = SENDING_STATUSES + DELIVERED_STATUSES + FAILURE_STATUSES


def user_has_permissions(*permissions, **permission_kwargs):
    def wrap(func):
        @wraps(func)
        def wrap_func(*args, **kwargs):
            if current_user and current_user.is_authenticated:
                if current_user.has_permissions(
                    *permissions,
                    **permission_kwargs
                ):
                    return func(*args, **kwargs)
                else:
                    abort(403)
            else:
                abort(401)
        return wrap_func
    return wrap


def user_is_platform_admin(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.platform_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapped


def redirect_to_sign_in(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_details' not in session:
            return redirect(url_for('main.sign_in'))
        else:
            return f(*args, **kwargs)
    return wrapped


def get_errors_for_csv(recipients, template_type):

    errors = []

    if any(recipients.rows_with_bad_recipients):
        number_of_bad_recipients = len(list(recipients.rows_with_bad_recipients))
        if 'sms' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 phone number")
            else:
                errors.append("fix {} phone numbers".format(number_of_bad_recipients))
        elif 'email' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 email address")
            else:
                errors.append("fix {} email addresses".format(number_of_bad_recipients))
        elif 'letter' == template_type:
            if 1 == number_of_bad_recipients:
                errors.append("fix 1 address")
            else:
                errors.append("fix {} addresses".format(number_of_bad_recipients))

    if any(recipients.rows_with_missing_data):
        number_of_rows_with_missing_data = len(list(recipients.rows_with_missing_data))
        if 1 == number_of_rows_with_missing_data:
            errors.append("enter missing data in 1 row")
        else:
            errors.append("enter missing data in {} rows".format(number_of_rows_with_missing_data))

    return errors


def generate_notifications_csv(**kwargs):
    from app import notification_api_client
    from app.main.s3_client import s3download
    if 'page' not in kwargs:
        kwargs['page'] = 1

    if kwargs.get('job_id'):
        original_file_contents = s3download(kwargs['service_id'], kwargs['job_id'])
        original_upload = RecipientCSV(
            original_file_contents,
            template_type=kwargs['template_type'],
        )
        original_column_headers = original_upload.column_headers
        fieldnames = ['Row number'] + original_column_headers + ['Template', 'Type', 'Job', 'Status', 'Time']
    else:
        fieldnames = ['Recipient', 'Template', 'Type', 'Sent by', 'Sent by email', 'Job', 'Status', 'Time']

    yield ','.join(fieldnames) + '\n'

    while kwargs['page']:
        notifications_resp = notification_api_client.get_notifications_for_service(**kwargs)
        for notification in notifications_resp['notifications']:
            if kwargs.get('job_id'):
                values = [
                    notification['row_number'],
                ] + [
                    original_upload[notification['row_number'] - 1].get(header).data
                    for header in original_column_headers
                ] + [
                    notification['template_name'],
                    notification['template_type'],
                    notification['job_name'],
                    notification['status'],
                    notification['created_at'],
                ]
            else:
                values = [
                    notification['recipient'],
                    notification['template_name'],
                    notification['template_type'],
                    notification['created_by_name'] or '',
                    notification['created_by_email_address'] or '',
                    notification['job_name'] or '',
                    notification['status'],
                    notification['created_at']
                ]
            yield Spreadsheet.from_rows([map(str, values)]).as_csv_data

        if notifications_resp['links'].get('next'):
            kwargs['page'] += 1
        else:
            return
    raise Exception("Should never reach here")


def get_page_from_request():
    if 'page' in request.args:
        try:
            return int(request.args['page'])
        except ValueError:
            return None
    else:
        return 1


def generate_previous_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page - 1, 'Previous page', url_args or {})


def generate_next_dict(view, service_id, page, url_args=None):
    return generate_previous_next_dict(view, service_id, page + 1, 'Next page', url_args or {})


def generate_previous_next_dict(view, service_id, page, title, url_args):
    return {
        'url': url_for(view, service_id=service_id, page=page, **url_args),
        'title': title,
        'label': 'page {}'.format(page)
    }


def email_safe(string, whitespace='.'):
    # strips accents, diacritics etc
    string = ''.join(c for c in unicodedata.normalize('NFD', string) if unicodedata.category(c) != 'Mn')
    string = ''.join(
        word.lower() if word.isalnum() or word == whitespace else ''
        for word in re.sub(r'\s+', whitespace, string.strip())
    )
    string = re.sub(r'\.{2,}', '.', string)
    return string.strip('.')


def id_safe(string):
    return email_safe(string, whitespace='-')


class Spreadsheet():

    allowed_file_extensions = ['csv', 'xlsx', 'xls', 'ods', 'xlsm', 'tsv']

    def __init__(self, csv_data, filename=''):
        self.filename = filename
        self.as_csv_data = csv_data
        self.as_dict = {
            'file_name': self.filename,
            'data': self.as_csv_data
        }

    @classmethod
    def can_handle(cls, filename):
        return cls.get_extension(filename) in cls.allowed_file_extensions

    @staticmethod
    def get_extension(filename):
        return path.splitext(filename)[1].lower().lstrip('.')

    @staticmethod
    def normalise_newlines(file_content):
        return '\r\n'.join(file_content.read().decode('utf-8').splitlines())

    @classmethod
    def from_rows(cls, rows, filename=''):
        with StringIO() as converted:
            output = csv.writer(converted)

            for row in rows:
                output.writerow(row)
            return cls(converted.getvalue(), filename)

    @classmethod
    def from_dict(cls, dictionary, filename=''):
        return cls.from_rows(
            zip(
                *sorted(dictionary.items(), key=lambda pair: pair[0])
            ),
            filename
        )

    @classmethod
    def from_file(cls, file_content, filename=''):
        extension = cls.get_extension(filename)

        if extension == 'csv':
            return cls(Spreadsheet.normalise_newlines(file_content), filename)

        if extension == 'tsv':
            file_content = StringIO(
                Spreadsheet.normalise_newlines(file_content))

        instance = cls.from_rows(
            pyexcel.iget_array(
                file_type=extension,
                file_stream=file_content),
            filename)
        pyexcel.free_resources()
        return instance


def get_help_argument():
    return request.args.get('help') if request.args.get('help') in ('1', '2', '3') else None


def is_gov_user(email_address):
    try:
        GovernmentEmailDomain(email_address)
        return True
    except NotGovernmentEmailDomain:
        return False


def get_template(
    template,
    service,
    show_recipient=False,
    expand_emails=False,
    letter_preview_url=None,
    page_count=1,
    redact_missing_personalisation=False,
    email_reply_to=None,
    sms_sender=None,
):
    if 'email' == template['template_type']:
        return EmailPreviewTemplate(
            template,
            from_name=service.name,
            from_address='{}@notifications.service.gov.uk'.format(service.email_from),
            expanded=expand_emails,
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
            reply_to=email_reply_to,
        )
    if 'sms' == template['template_type']:
        return SMSPreviewTemplate(
            template,
            prefix=service.name,
            show_prefix=service.prefix_sms,
            sender=sms_sender,
            show_sender=bool(sms_sender),
            show_recipient=show_recipient,
            redact_missing_personalisation=redact_missing_personalisation,
        )
    if 'letter' == template['template_type']:
        if letter_preview_url:
            return LetterImageTemplate(
                template,
                image_url=letter_preview_url,
                page_count=int(page_count),
                contact_block=template['reply_to_text']
            )
        else:
            return LetterPreviewTemplate(
                template,
                contact_block=template['reply_to_text'],
                admin_base_url=current_app.config['ADMIN_BASE_URL'],
                redact_missing_personalisation=redact_missing_personalisation,
            )


def get_current_financial_year():
    now = datetime.utcnow()
    current_month = int(now.strftime('%-m'))
    current_year = int(now.strftime('%Y'))
    return current_year if current_month > 3 else current_year - 1


def get_time_left(created_at, service_data_retention_days=7):
    return ago.human(
        (
            datetime.now(timezone.utc)
        ) - (
            dateutil.parser.parse(created_at).replace(hour=0, minute=0, second=0) + timedelta(
                days=service_data_retention_days + 1
            )
        ),
        future_tense='Data available for {}',
        past_tense='Data no longer available',  # No-one should ever see this
        precision=1
    )


def email_or_sms_not_enabled(template_type, permissions):
    return (template_type in ['email', 'sms']) and (template_type not in permissions)


def get_logo_cdn_domain():
    parsed_uri = urlparse(current_app.config['ADMIN_BASE_URL'])

    if parsed_uri.netloc.startswith('localhost'):
        return 'static-logos.notify.tools'

    subdomain = parsed_uri.hostname.split('.')[0]
    domain = parsed_uri.netloc[len(subdomain + '.'):]

    return "static-logos.{}".format(domain)


def parse_filter_args(filter_dict):
    if not isinstance(filter_dict, MultiDict):
        filter_dict = MultiDict(filter_dict)

    return MultiDict(
        (
            key,
            (','.join(filter_dict.getlist(key))).split(',')
        )
        for key in filter_dict.keys()
        if ''.join(filter_dict.getlist(key))
    )


def set_status_filters(filter_args):
    status_filters = filter_args.get('status', [])
    return list(OrderedSet(chain(
        (status_filters or REQUESTED_STATUSES),
        DELIVERED_STATUSES if 'delivered' in status_filters else [],
        SENDING_STATUSES if 'sending' in status_filters else [],
        FAILURE_STATUSES if 'failed' in status_filters else []
    )))


_dir_path = os.path.dirname(os.path.realpath(__file__))


class AgreementInfo:

    with open('{}/domains.yml'.format(_dir_path)) as domains:
        domains = yaml.safe_load(domains)
        domain_names = sorted(domains.keys(), key=len, reverse=True)

    def __init__(self, email_address_or_domain):

        self._match = next(filter(
            self.get_matching_function(email_address_or_domain),
            self.domain_names,
        ), None)

        self._domain = email_address_or_domain.split('@')[-1]

        (
            self.owner,
            self.crown_status,
            self.agreement_signed,
            self.canonical_domain,
        ) = self._get_info()

    @classmethod
    def from_user(cls, user):
        return cls(user.email_address if user.is_authenticated else '')

    @classmethod
    def from_current_user(cls):
        return cls.from_user(current_user)

    @property
    def as_human_readable(self):
        if self.agreement_signed:
            return 'Yes, on behalf of {}'.format(self.owner)
        elif self.owner:
            return '{} (organisation is {}, {})'.format(
                {
                    False: 'No',
                    None: 'Can’t tell',
                }.get(self.agreement_signed),
                self.owner,
                {
                    True: 'a crown body',
                    False: 'a non-crown body',
                    None: 'crown status unknown',
                }.get(self.crown_status),
            )
        else:
            return 'Can’t tell (domain is {})'.format(self._domain)

    @property
    def as_info_for_branding_request(self):
        return self.owner or 'Can’t tell (domain is {})'.format(self._domain)

    @property
    def as_jinja_template(self):
        if self.crown_status is None:
            return 'agreement-choose'
        if self.agreement_signed:
            return 'agreement-signed'
        return 'agreement'

    def as_terms_of_use_paragraph(self, **kwargs):
        return Markup(self._as_terms_of_use_paragraph(**kwargs))

    def _as_terms_of_use_paragraph(self, terms_link, download_link, support_link, signed_in):

        if not signed_in:
            return ((
                '{} <a href="{}">Sign in</a> to download a copy '
                'or find out if one is already in place.'
            ).format(self._acceptance_required, terms_link))

        if self.agreement_signed is None:
            return ((
                '{} <a href="{}">Download the agreement</a> or '
                '<a href="{}">contact us</a> to find out if we already '
                'have one in place with your organisation.'
            ).format(self._acceptance_required, download_link, support_link))

        if self.agreement_signed is False:
            return ((
                '{} <a href="{}">Download a copy</a>.'
            ).format(self._acceptance_required, download_link))

        return (
            'Your organisation ({}) has already accepted the '
            'GOV.UK&nbsp;Notify data sharing and financial '
            'agreement.'.format(self.owner)
        )

    def as_pricing_paragraph(self, **kwargs):
        return Markup(self._as_pricing_paragraph(**kwargs))

    def _as_pricing_paragraph(self, pricing_link, download_link, support_link, signed_in):

        if not signed_in:
            return ((
                '<a href="{}">Sign in</a> to download a copy or find '
                'out if one is already in place with your organisation.'
            ).format(pricing_link))

        if self.agreement_signed is None:
            return ((
                '<a href="{}">Download the agreement</a> or '
                '<a href="{}">contact us</a> to find out if we already '
                'have one in place with your organisation.'
            ).format(download_link, support_link))

        return (
            '<a href="{}">Download the agreement</a> '
            '({} {}).'.format(
                download_link,
                self.owner,
                {
                    True: 'has already accepted it',
                    False: 'hasn’t accepted it yet'
                }.get(self.agreement_signed)
            )
        )

    @property
    def _acceptance_required(self):
        return (
            'Your organisation {} must also accept our data sharing '
            'and financial agreement.'.format(
                '({})'.format(self.owner) if self.owner else '',
            )
        )

    @property
    def crown_status_or_404(self):
        if self.crown_status is None:
            abort(404)
        return self.crown_status

    @staticmethod
    def get_matching_function(email_address_or_domain):

        email_address_or_domain = email_address_or_domain.lower()

        def fn(domain):

            return (
                email_address_or_domain == domain
            ) or (
                email_address_or_domain.endswith("@{}".format(domain))
            ) or (
                email_address_or_domain.endswith(".{}".format(domain))
            )

        return fn

    def _get_info(self):

        details = self.domains.get(self._match) or {}

        if isinstance(details, str):
            self.is_canonical = False
            return AgreementInfo(details)._get_info()

        elif isinstance(details, dict):
            self.is_canonical = bool(details)
            return(
                details.get("owner"),
                details.get("crown"),
                details.get("agreement_signed"),
                self._match,
            )


class NotGovernmentEmailDomain(Exception):
    pass


class GovernmentEmailDomain(AgreementInfo):

    with open('{}/email_domains.yml'.format(_dir_path)) as email_domains:
        domain_names = yaml.safe_load(email_domains)

    def __init__(self, email_address_or_domain):
        try:
            self._match = next(filter(
                self.get_matching_function(email_address_or_domain),
                self.domain_names,
            ))
        except StopIteration:
            raise NotGovernmentEmailDomain()


def unicode_truncate(s, length):
    encoded = s.encode('utf-8')[:length]
    return encoded.decode('utf-8', 'ignore')


def starts_with_initial(name):
    return bool(re.match(r'^.\.', name))


def remove_middle_initial(name):
    return re.sub(r'\s+.\s+', ' ', name)


def remove_digits(name):
    return ''.join(c for c in name if not c.isdigit())


def normalize_spaces(name):
    return ' '.join(name.split())


def guess_name_from_email_address(email_address):

    possible_name = re.split(r'[\@\+]', email_address)[0]

    if '.' not in possible_name or starts_with_initial(possible_name):
        return ''

    return Take(
        possible_name
    ).then(
        str.replace, '.', ' '
    ).then(
        remove_digits
    ).then(
        remove_middle_initial
    ).then(
        str.title
    ).then(
        make_quotes_smart
    ).then(
        normalize_spaces
    )


def should_skip_template_page(template_type):
    return (
        current_user.has_permissions('send_messages') and
        not current_user.has_permissions('manage_templates', 'manage_api_keys') and
        template_type != 'letter'
    )


def get_default_sms_sender(sms_senders):
    return str(next((
        Field(x['sms_sender'], html='escape')
        for x in sms_senders if x['is_default']
    ), "None"))


def printing_today_or_tomorrow():
    now_utc = datetime.utcnow()
    now_bst = convert_utc_to_bst(now_utc)

    if now_bst.time() < time(17, 30):
        return 'today'
    else:
        return 'tomorrow'
