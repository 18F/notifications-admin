from collections import defaultdict

from notifications_python_client.base import BaseAPIClient
from app.notify_client import _attach_current_user


class JobApiClient(BaseAPIClient):
    def __init__(self, base_url=None, service_id=None, api_key=None):
        super(self.__class__, self).__init__(base_url=base_url or 'base_url',
                                             service_id=service_id or 'service_id',
                                             api_key=api_key or 'api_key')

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    @staticmethod
    def __convert_statistics(job):
        results = defaultdict(int)
        for outcome in job['statistics']:
            if outcome['status'] in ['failed', 'technical-failure', 'temporary-failure', 'permanent-failure']:
                results['failed'] += outcome['count']
            if outcome['status'] in ['sending', 'pending', 'created']:
                results['sending'] += outcome['count']
            if outcome['status'] in ['delivered']:
                results['delivered'] += outcome['count']
            results['requested'] += outcome['count']
        return results

    def get_job(self, service_id, job_id=None, limit_days=None, status=None):
        if job_id:
            params = {}
            if status is not None:
                params['status'] = status
            job = self.get(url='/service/{}/job/{}'.format(service_id, job_id), params=params)

            stats = self.__convert_statistics(job['data'])
            job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
            job['data']['notifications_delivered'] = stats['delivered']
            job['data']['notifications_failed'] = stats['failed']
            job['data']['notifications_requested'] = stats['requested']

            return job

        params = {}
        if limit_days is not None:
            params['limit_days'] = limit_days

        jobs = self.get(url='/service/{}/job'.format(service_id), params=params)
        for job in jobs['data']:
            stats = self.__convert_statistics(job)
            job['notifications_sent'] = stats['delivered'] + stats['failed']
            job['notifications_delivered'] = stats['delivered']
            job['notifications_failed'] = stats['failed']
            job['notifications_requested'] = stats['requested']

        return jobs

    def create_job(self, job_id, service_id, template_id, original_file_name, notification_count, scheduled_for=None):
        data = {
            "id": job_id,
            "template": template_id,
            "original_file_name": original_file_name,
            "notification_count": notification_count
        }

        if scheduled_for:
            data.update({'scheduled_for': scheduled_for})

        data = _attach_current_user(data)
        job = self.post(url='/service/{}/job'.format(service_id), data=data)

        stats = self.__convert_statistics(job['data'])
        job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
        job['data']['notifications_delivered'] = stats['delivered']
        job['data']['notifications_failed'] = stats['failed']
        job['data']['notifications_requested'] = stats['requested']

        return job

    def cancel_job(self, service_id, job_id):

        job = self.post(
            url='/service/{}/job/{}/cancel'.format(service_id, job_id),
            data={}
        )

        stats = self.__convert_statistics(job['data'])
        job['data']['notifications_sent'] = stats['delivered'] + stats['failed']
        job['data']['notifications_delivered'] = stats['delivered']
        job['data']['notifications_failed'] = stats['failed']
        job['data']['notifications_requested'] = stats['requested']

        return job
