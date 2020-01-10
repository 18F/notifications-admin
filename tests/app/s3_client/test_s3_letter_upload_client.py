import urllib

from flask import current_app

from app.s3_client.s3_letter_upload_client import upload_letter_to_s3


def test_upload_letter_to_s3(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    recipient = 'Bugs Bunny\n123 Big Hole\nLooney Town'
    upload_letter_to_s3(
        'pdf_data',
        file_location='service_id/upload_id.pdf',
        status='valid',
        page_count=3,
        filename='my_doc',
        recipient=recipient
    )

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={'status': 'valid', 'page_count': '3', 'filename': 'my_doc',
                  'recipient': urllib.parse.quote(recipient)},
        region=current_app.config['AWS_REGION']
    )


def test_upload_letter_to_s3_with_message_and_invalid_pages(mocker):
    s3_mock = mocker.patch('app.s3_client.s3_letter_upload_client.utils_s3upload')

    upload_letter_to_s3(
        'pdf_data',
        file_location='service_id/upload_id.pdf',
        status='invalid',
        page_count=3,
        filename='my_doc',
        message='This file failed',
        invalid_pages=[1, 2, 5])

    s3_mock.assert_called_once_with(
        bucket_name=current_app.config['TRANSIENT_UPLOADED_LETTERS'],
        file_location='service_id/upload_id.pdf',
        filedata='pdf_data',
        metadata={
            'status': 'invalid',
            'page_count': '3',
            'filename': 'my_doc',
            'message': 'This file failed',
            'invalid_pages': '[1, 2, 5]'
        },
        region=current_app.config['AWS_REGION']
    )
