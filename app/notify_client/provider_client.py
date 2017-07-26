
from app.notify_client import _attach_current_user, NotifyAdminAPIClient


class ProviderClient(NotifyAdminAPIClient):
    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.api_key = '{}-{}'.format(
            app.config['ADMIN_CLIENT_USER_NAME'],
            app.config['ADMIN_CLIENT_SECRET'],
        )

    def get_all_providers(self):
        return self.get(
            url='/provider-details'
        )

    def get_provider_by_id(self, provider_id):
        return self.get(
            url='/provider-details/{}'.format(provider_id)
        )

    def get_provider_versions(self, provider_id):
        return self.get(
            url='/provider-details/{}/versions'.format(provider_id)
        )

    def update_provider(self, provider_id, priority):
        data = {
            "priority": priority
        }
        data = _attach_current_user(data)
        return self.post(url='/provider-details/{}'.format(provider_id), data=data)
