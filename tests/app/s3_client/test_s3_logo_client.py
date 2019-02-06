from collections import namedtuple
from unittest.mock import call

import pytest

from app.s3_client.s3_logo_client import (
    EMAIL_LOGO_LOCATION_STRUCTURE,
    TEMP_TAG,
    delete_email_temp_file,
    delete_email_temp_files_created_by,
    permanent_email_logo_name,
    persist_logo,
    upload_email_logo,
)

bucket = 'test_bucket'
data = {'data': 'some_data'}
filename = 'test.png'
upload_id = 'test_uuid'
region = 'eu-west1'


@pytest.fixture
def upload_filename(fake_uuid):
    return EMAIL_LOGO_LOCATION_STRUCTURE.format(
        temp=TEMP_TAG.format(user_id=fake_uuid), unique_id=upload_id, filename=filename)


def test_upload_email_logo_calls_correct_args(client, mocker, fake_uuid, upload_filename):
    mocker.patch('uuid.uuid4', return_value=upload_id)
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_s3_upload = mocker.patch('app.s3_client.s3_logo_client.utils_s3upload')

    upload_email_logo(filename=filename, user_id=fake_uuid, filedata=data, region=region)

    assert mocked_s3_upload.called_once_with(
        filedata=data,
        region=region,
        file_location=upload_filename,
        bucket_name=bucket
    )


def test_persist_logo(client, mocker, fake_uuid, upload_filename):
    mocker.patch.dict('flask.current_app.config', {'LOGO_UPLOAD_BUCKET_NAME': bucket})
    mocked_get_s3_object = mocker.patch('app.s3_client.s3_logo_client.get_s3_object')
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    new_filename = permanent_email_logo_name(upload_filename, fake_uuid)

    persist_logo(upload_filename, new_filename)

    assert mocked_get_s3_object.called_once_with(bucket, new_filename)
    assert mocked_delete_s3_object.called_once_with(bucket, upload_filename)


def test_persist_logo_returns_if_not_temp(client, mocker, fake_uuid):
    filename = 'logo.png'
    persist_logo(filename, filename)

    mocked_get_s3_object = mocker.patch('app.s3_client.s3_logo_client.get_s3_object')
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    mocked_get_s3_object.assert_not_called()
    mocked_delete_s3_object.assert_not_called()


def test_permanent_email_logo_name_removes_TEMP_TAG_from_filename(upload_filename, fake_uuid):
    new_name = permanent_email_logo_name(upload_filename, fake_uuid)

    assert new_name == 'test_uuid-test.png'


def test_permanent_email_logo_name_does_not_change_filenames_with_no_TEMP_TAG():
    filename = 'logo.png'
    new_name = permanent_email_logo_name(filename, filename)

    assert new_name == filename


def test_delete_email_temp_files_created_by_user(client, mocker, fake_uuid):
    obj = namedtuple("obj", ["key"])
    objs = [obj(key='test1'), obj(key='test2')]

    mocker.patch('app.s3_client.s3_logo_client.get_s3_objects_filter_by_prefix', return_value=objs)
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    delete_email_temp_files_created_by(fake_uuid)

    assert mocked_delete_s3_object.called_with_args(objs[0].key)
    for index, arg in enumerate(mocked_delete_s3_object.call_args_list):
        assert arg == call(objs[index].key)


def test_delete_single_temp_file(client, mocker, fake_uuid, upload_filename):
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    delete_email_temp_file(upload_filename)

    assert mocked_delete_s3_object.called_with_args(upload_filename)


def test_does_not_delete_non_temp_file(client, mocker, fake_uuid):
    filename = 'logo.png'
    mocked_delete_s3_object = mocker.patch('app.s3_client.s3_logo_client.delete_s3_object')

    with pytest.raises(ValueError) as error:
        delete_email_temp_file(filename)

    assert mocked_delete_s3_object.called_with_args(filename)
    assert str(error.value) == 'Not a temp file: {}'.format(filename)
