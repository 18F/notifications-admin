from datetime import datetime

from notifications_utils.letter_timings import (
    CANCELLABLE_JOB_LETTER_STATUSES,
    get_letter_timings,
    letter_can_be_cancelled,
)
from werkzeug.utils import cached_property

from app.models import JSONModel
from app.notify_client.job_api_client import job_api_client
from app.notify_client.notification_api_client import notification_api_client
from app.notify_client.service_api_client import service_api_client
from app.utils import set_status_filters


class Job(JSONModel):

    ALLOWED_PROPERTIES = {
        'id',
        'service',
        'template',
        'template_version',
        'original_file_name',
        'created_at',
        'notification_count',
        'notifications_sent',
        'notifications_requested',
        'job_status',
        'statistics',
        'created_by',
        'scheduled_for',
    }

    @classmethod
    def from_id(cls, job_id, service_id):
        return cls(job_api_client.get_job(service_id, job_id)['data'])

    @property
    def status(self):
        return self.job_status

    @property
    def cancelled(self):
        return self.status == 'cancelled'

    @property
    def scheduled(self):
        return self.status == 'scheduled'

    @property
    def notification_count(self):
        return self._dict.get('notification_count', 0)

    @property
    def notifications_delivered(self):
        return self._dict.get('notifications_delivered', 0)

    @property
    def notifications_failed(self):
        return self._dict.get('notifications_failed', 0)

    @property
    def notifications_processed(self):
        return self.notifications_delivered + self.notifications_failed

    @property
    def notifications_sending(self):
        if self.scheduled:
            return 0
        return (
            self.notification_count -
            self.notifications_delivered -
            self.notifications_failed
        )

    @property
    def notifications_created(self):
        return notification_api_client.get_notification_count_for_job_id(
            service_id=self.service, job_id=self.id
        )

    @property
    def still_processing(self):
        return (
            self.status != 'finished' or
            self.notifications_created < self.notification_count
        )

    @property
    def template_id(self):
        return self._dict['template']

    @cached_property
    def template(self):
        return service_api_client.get_service_template(
            service_id=self.service,
            template_id=self.template_id,
            version=self.template_version,
        )['data']

    @property
    def template_type(self):
        return self.template['template_type']

    @property
    def percentage_complete(self):
        return self.notifications_requested / self.notification_count * 100

    @property
    def letter_job_can_be_cancelled(self):

        if self.template['template_type'] != 'letter':
            return False

        if any(self.uncancellable_notifications):
            return False

        if not letter_can_be_cancelled(
            'created', datetime.strptime(self.created_at[:-6], '%Y-%m-%dT%H:%M:%S.%f')
        ):
            return False

        return True

    @cached_property
    def all_notifications(self):
        return self.get_notifications(set_status_filters({}))['notifications']

    @property
    def uncancellable_notifications(self):
        return (
            n for n in self.all_notifications
            if n['status'] not in CANCELLABLE_JOB_LETTER_STATUSES
        )

    @cached_property
    def postage(self):
        # There might be no notifications if the job has only just been
        # created and the tasks haven't run yet
        try:
            return self.all_notifications[0]['postage']
        except IndexError:
            return self.template['postage']

    @property
    def letter_timings(self):
        return get_letter_timings(self.created_at, postage=self.postage)

    def get_notifications(self, status):
        return notification_api_client.get_notifications_for_service(
            self.service, self.id, status=status,
        )

    def cancel(self):
        if self.template_type == 'letter':
            return job_api_client.cancel_letter_job(self.service, self.id)
        else:
            return job_api_client.cancel_job(self.service, self.id)
