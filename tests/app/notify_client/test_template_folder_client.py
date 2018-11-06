import pytest
import uuid

from app.notify_client.template_folder_api_client import TemplateFolderAPIClient


@pytest.mark.parametrize('parent_id', [uuid.uuid4(), None])
def test_create_template_folder_calls_correct_api_endpoint(mocker, api_user_active, parent_id):
    mock_redis_delete = mocker.patch('app.notify_client.RedisClient.delete')

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder'.format(some_service_id)
    data = {'name': 'foo', 'parent_id': parent_id}

    client = TemplateFolderAPIClient()

    mock_post = mocker.patch('app.notify_client.template_folder_api_client.TemplateFolderAPIClient.post')

    client.create_template_folder(some_service_id, name='foo', parent_id=parent_id)

    mock_post.assert_called_once_with(expected_url, data)
    mock_redis_delete.assert_called_once_with('service-{}-template-folders'.format(some_service_id))


def test_get_template_folders_calls_correct_api_endpoint(mocker, api_user_active):
    mock_redis_get = mocker.patch('app.notify_client.RedisClient.get', return_value=None)
    mock_api_get = mocker.patch('app.notify_client.NotifyAdminAPIClient.get', return_value={'data': {'a': 'b'}})
    mock_redis_set = mocker.patch('app.notify_client.RedisClient.set')

    some_service_id = uuid.uuid4()
    expected_url = '/service/{}/template-folder'.format(some_service_id)
    redis_key = 'service-{}-template-folders'.format(some_service_id)

    client = TemplateFolderAPIClient()

    ret = client.get_template_folders(some_service_id)

    assert ret == {'a': 'b'}

    mock_redis_get.assert_called_once_with(redis_key)
    mock_api_get.assert_called_once_with(expected_url)
    mock_redis_set.assert_called_once_with(redis_key, '{"a": "b"}', ex=604800)
