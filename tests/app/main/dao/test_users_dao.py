from datetime import datetime

import pytest
import sqlalchemy

from app.models import User
from app.main.dao import users_dao


def test_insert_user_should_add_user(notifications_admin, notifications_admin_db):
    user = User(name='test insert',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1)

    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user == user


def test_insert_user_with_role_that_does_not_exist_fails(notifications_admin, notifications_admin_db):
    user = User(name='role does not exist',
                password='somepassword',
                email_address='test@insert.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=100)
    with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
        users_dao.insert_user(user)
    assert 'insert or update on table "users" violates foreign key constraint "users_role_id_fkey"' in str(error.value)


def test_get_user_by_email(notifications_admin, notifications_admin_db):
    user = User(name='test_get_by_email',
                password='somepassword',
                email_address='email@example.gov.uk',
                mobile_number='+441234153412',
                created_at=datetime.now(),
                role_id=1)

    users_dao.insert_user(user)
    retrieved = users_dao.get_user_by_email(user.email_address)
    assert retrieved == user


def test_get_all_users_returns_all_users(notifications_admin, notifications_admin_db):
    user1 = User(name='test one',
                 password='somepassword',
                 email_address='test1@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)
    user2 = User(name='test two',
                 password='some2ndpassword',
                 email_address='test2@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)
    user3 = User(name='test three',
                 password='some2ndpassword',
                 email_address='test2@get_all.gov.uk',
                 mobile_number='+441234123412',
                 created_at=datetime.now(),
                 role_id=1)

    users_dao.insert_user(user1)
    users_dao.insert_user(user2)
    users_dao.insert_user(user3)
    users = users_dao.get_all_users()
    assert len(users) == 3
    assert users == [user1, user2, user3]


def test_increment_failed_lockout_count_should_increade_count_by_1(notifications_admin, notifications_admin_db):
    user = User(name='cannot remember password',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1)
    users_dao.insert_user(user)

    savedUser = users_dao.get_user_by_id(user.id)
    assert savedUser.failed_login_count == 0
    users_dao.increment_failed_login_count(user.id)
    assert users_dao.get_user_by_id(user.id).failed_login_count == 1


def test_user_is_locked_if_failed_login_count_is_10_or_greater(notifications_admin, notifications_admin_db):
    user = User(name='cannot remember password',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1)
    users_dao.insert_user(user)
    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.is_locked() is False

    for _ in range(10):
        users_dao.increment_failed_login_count(user.id)

    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.failed_login_count == 10
    assert saved_user.is_locked() is True


def test_user_is_active_is_false_if_state_is_inactive(notifications_admin, notifications_admin_db):
    user = User(name='inactive user',
                password='somepassword',
                email_address='test1@get_all.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1,
                state='inactive')
    users_dao.insert_user(user)

    saved_user = users_dao.get_user_by_id(user.id)
    assert saved_user.is_active() is False


def test_should_update_user_to_active(notifications_admin, notifications_admin_db):
    user = User(name='Make user active',
                password='somepassword',
                email_address='activate@user.gov.uk',
                mobile_number='+441234123412',
                created_at=datetime.now(),
                role_id=1,
                state='pending')
    users_dao.insert_user(user)
    users_dao.activate_user(user.id)
    updated_user = users_dao.get_user_by_id(user.id)
    assert updated_user.state == 'active'


def test_should_throws_error_when_id_does_not_exist(notifications_admin, notifications_admin_db):
    with pytest.raises(AttributeError) as error:
        users_dao.activate_user(123)
    assert '''object has no attribute 'state''''' in str(error.value)
