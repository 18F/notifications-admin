from flask import url_for
from datetime import datetime
from client.errors import HTTPError, InvalidResponse
from sqlalchemy.orm import load_only
from flask.ext.login import current_user
from app import (db, notifications_api_client)
from app.main.utils import BrowsableItem


def insert_new_service(service_name, user_id):
    # Add a service with default attributes
    # Should we try and handle exception here
    resp = notifications_api_client.create_service(
        service_name, False, 1000, True, user_id)

    return resp['data']['id']


def get_service_by_id(id_):
    return notifications_api_client.get_service(id_)


def get_services():
    return notifications_api_client.get_services()


def unrestrict_service(service_id):
    resp = notifications_api_client.get_service(service_id)
    if resp['data']['restricted']:
        resp = notifications_api_client.update_service(
            service_id,
            resp['data']['name'],
            resp['data']['active'],
            resp['data']['limit'],
            False,
            resp['data']['users'])


def activate_service(service_id):
    resp = notifications_api_client.get_service(service_id)
    if not resp['data']['active']:
        resp = notifications_api_client.update_service(
            service_id,
            resp['data']['name'],
            True,
            resp['data']['limit'],
            resp['data']['restricted'],
            resp['data']['users'])


# TODO Fix when functionality is added to the api.
def find_service_by_service_name(service_name):
    resp = notifications_api_client.get_services()
    retval = None
    for srv_json in resp['data']:
        if srv_json['name'] == service_name:
            retval = srv_json
            break
    return retval


def delete_service(id_):
    return notifications_api_client.delete_service(id_)


def find_all_service_names():
    resp = notifications_api_client.get_services()
    return [x['name'] for x in resp['data']]


class ServicesBrowsableItem(BrowsableItem):

    @property
    def title(self):
        return self._item['name']

    @property
    def link(self):
        return url_for('main.service_dashboard', service_id=self._item['id'])

    @property
    def destructive(self):
        return False

    @property
    def hint(self):
        return "Some service hint here"
