from app.notify_client import NotifyAdminAPIClient

class InboundNumberClient(NotifyAdminAPIClient):

    def __init__(self):
        super().__init__("a" * 73, "b")

    def init_app(self, app):
        self.base_url = app.config['API_HOST_NAME']
        self.service_id = app.config['ADMIN_CLIENT_USER_NAME']
        self.api_key = app.config['ADMIN_CLIENT_SECRET']

    def get_inbound_sms_number_service(self):
        endpoint = '/inbound_number'
        return self.get(endpoint)