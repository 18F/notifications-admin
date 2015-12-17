import pytest
import sqlalchemy

from app.main.dao import services_dao
from tests.app.main import create_test_user


def test_can_insert_and_retrieve_new_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    id = services_dao.insert_new_service('testing service', user)
    saved_service = services_dao.get_service_by_id(id)
    assert id == saved_service.id
    assert saved_service.users == [user]
    assert saved_service.name == 'testing service'


def test_unrestrict_service_updates_the_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    id = services_dao.insert_new_service('unrestricted service', user)
    saved_service = services_dao.get_service_by_id(id)
    assert saved_service.restricted is True
    services_dao.unrestrict_service(id)
    unrestricted_service = services_dao.get_service_by_id(id)
    assert unrestricted_service.restricted is False


def test_activate_service_update_service(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    id = services_dao.insert_new_service('activated service', user)
    service = services_dao.get_service_by_id(id)
    assert service.active is False
    services_dao.activate_service(id)
    activated_service = services_dao.get_service_by_id(id)
    assert activated_service.active is True


def test_get_service_returns_none_if_service_does_not_exist(notifications_admin,
                                                            notifications_admin_db,
                                                            notify_db_session):
    service = services_dao.get_service_by_id(1)
    assert service is None


def test_find_by_service_name_returns_right_service(notifications_admin,
                                                    notifications_admin_db,
                                                    notify_db_session):
    user = create_test_user('active')
    id = services_dao.insert_new_service('testing service', user)
    another = services_dao.insert_new_service('Testing the Service', user)
    found = services_dao.find_service_by_service_name('testing service')
    assert found.id == id
    assert found.name == 'testing service'
    found_another = services_dao.find_service_by_service_name('Testing the Service')
    assert found_another == services_dao.get_service_by_id(another)


def test_should_not_allow_two_services_of_the_same_name(notifications_admin, notifications_admin_db, notify_db_session):
    user = create_test_user('active')
    services_dao.insert_new_service('duplicate service', user)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        services_dao.insert_new_service('duplicate service', user)
        assert 'duplicate key value violates unique constraint "services_name_key' in error.value
