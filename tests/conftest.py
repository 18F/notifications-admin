import os
import pytest
from alembic.command import upgrade
from alembic.config import Config
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.script import Manager
from sqlalchemy.schema import MetaData
from . import (
    create_test_user, create_another_test_user, service_json, TestClient)
from app import create_app, db


@pytest.fixture(scope='session')
def app_(request):
    app = create_app('test')

    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    app.test_client_class = TestClient
    return app


@pytest.fixture(scope='session')
def db_(app_, request):
    Migrate(app_, db)
    Manager(db, MigrateCommand)
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    ALEMBIC_CONFIG = os.path.join(BASE_DIR, 'migrations')
    config = Config(ALEMBIC_CONFIG + '/alembic.ini')
    config.set_main_option("script_location", ALEMBIC_CONFIG)

    with app_.app_context():
        upgrade(config, 'head')

    def teardown():
        db.session.remove()
        db.drop_all()
        db.engine.execute("drop table alembic_version")
        db.get_engine(app_).dispose()

    request.addfinalizer(teardown)


@pytest.fixture(scope='function')
def db_session(request):
    def teardown():
        db.session.remove()
        for tbl in reversed(meta.sorted_tables):
            if tbl.fullname not in ['roles']:
                db.engine.execute(tbl.delete())

    meta = MetaData(bind=db.engine, reflect=True)
    request.addfinalizer(teardown)


@pytest.fixture(scope='function')
def service_one(request):
    usr = create_test_user('active')
    return service_json(1, 'service one', [usr])


@pytest.fixture(scope='function')
def active_user(request, db_, db_session):
    return create_test_user('active')


@pytest.fixture(scope='function')
def mock_send_sms(request, mocker):
    return mocker.patch("app.notifications_api_client.send_sms")


@pytest.fixture(scope='function')
def mock_send_email(request, mocker):
    return mocker.patch("app.notifications_api_client.send_email")


@pytest.fixture(scope='function')
def mock_get_service(mocker):
    return mocker.patch('app.notifications_api_client.get_service')


@pytest.fixture(scope='function')
def mock_create_service(mocker):
    # TODO fix token generation
    def _create(service_name, active, limit, restricted, user_id):
        service = service_json(
            101, service_name, [user_id], limit=limit,
            active=active, restricted=restricted)
        return {'data': service, 'token': 1}
    mock_class = mocker.patch(
        'app.notifications_api_client.create_service', side_effect=_create)
    return mock_class


@pytest.fixture(scope='function')
def mock_update_service(mocker):
    def _update(service_id,
                service_name,
                active,
                limit,
                restricted,
                users):
        service = service_json(
            service_id, service_name, users, limit=limit,
            active=active, restricted=restricted)
        return {'data': service}
    mock_class = mocker.patch(
        'app.notifications_api_client.update_service', side_effect=_update)
    return mock_class


@pytest.fixture(scope='function')
def mock_get_services(mocker, active_user):
    def _create():
        service_one = service_json(
            1, "service_one", [active_user.id], 1000, True, False)
        service_two = service_json(
            2, "service_two", [active_user.id], 1000, True, False)
        return {'data': [service_one, service_two]}
    mock_class = mocker.patch(
        'app.notifications_api_client.get_services', side_effect=_create)
    return mock_class
