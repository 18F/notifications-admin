from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json


def test_simple_polygons(fake_uuid):
    broadcast_message = BroadcastMessage(broadcast_message_json(
        id_=fake_uuid,
        service_id=fake_uuid,
        template_id=fake_uuid,
        status='draft',
        created_by_id=fake_uuid,
        areas=[
            # Hackney Central
            'electoral-wards-of-the-united-kingdom-E05009372',
            # Hackney Wick
            'electoral-wards-of-the-united-kingdom-E05009374',
        ],
    ))

    assert [
        [len(polygon) for polygon in broadcast_message.polygons],
        [len(polygon) for polygon in broadcast_message.simple_polygons],
    ] == [
        # One polygon for each area
        [27, 31],
        # Because the areas are close to each other, the simplification
        # and unioning process results in a single polygon with fewer
        # total coordinates
        [34],
    ]
