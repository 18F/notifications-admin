import os
import importlib
from unittest import mock

import pytest

from app import config


def cf_conf():
    os.environ['API_HOST_NAME'] = 'cf'


@pytest.fixture
def reload_config():
    """
    Reset config, by simply re-running config.py from a fresh environment
    """
    old_env = os.environ.copy()

    yield

    os.environ = old_env
    importlib.reload(config)


def test_load_cloudfoundry_config_if_available(monkeypatch, reload_config):
    os.environ['API_HOST_NAME'] = 'env'
    monkeypatch.setenv('VCAP_SERVICES', 'some json blob')

    with mock.patch('app.cloudfoundry_config.extract_cloudfoundry_config', side_effect=cf_conf) as cf_config:
        # reload config so that its module level code (ie: all of it) is re-instantiated
        importlib.reload(config)

    assert cf_config.called

    assert os.environ['API_HOST_NAME'] == 'cf'
    assert config.Config.API_HOST_NAME == 'cf'


def test_load_config_if_cloudfoundry_not_available(monkeypatch, reload_config):
    os.environ['API_HOST_NAME'] = 'env'

    monkeypatch.delenv('VCAP_SERVICES', raising=False)

    with mock.patch('app.cloudfoundry_config.extract_cloudfoundry_config') as cf_config:
        # reload config so that its module level code (ie: all of it) is re-instantiated
        importlib.reload(config)

    assert not cf_config.called

    assert os.environ['API_HOST_NAME'] == 'env'
    assert config.Config.API_HOST_NAME == 'env'


def test_cloudfoundry_config_has_different_defaults():
    # these should always be set on Sandbox
    assert config.Sandbox.DEBUG is True
