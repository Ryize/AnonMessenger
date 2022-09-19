import datetime
import json
from datetime import datetime

from cryptography.fernet import InvalidToken

from server.application import DATETIME_TEMPLATE
from server.crypt import Crypt
from server.models import User, Message


async def get_all_user_messages(user_db: User) -> str:
    all_message_where_user_sender_object = Message.query.filter_by(sender=user_db.id).all()
    all_message_where_user_recipient_object = Message.query.filter_by(recipient=user_db.id).all()
    all_message_where_user_sender = to_json_type(all_message_where_user_sender_object)
    all_message_where_user_recipient = to_json_type(all_message_where_user_recipient_object)
    all_messages = json.dumps({
        'sender': all_message_where_user_sender,
        'recipient': all_message_where_user_recipient,
        'login': user_db.login,
    })

    return all_messages


async def login_existence_check(code):
    login = Crypt(code).decrypt()
    user = User.query.filter_by(login=login).first()
    if not user:
        raise InvalidToken
    return user


async def user_existence_check(sender: str, recipient: str):
    for user_in_db in User.query.all():
        login_in_db = user_in_db.login
        if login_in_db == sender:
            sender = user_in_db
        elif login_in_db == recipient:
            recipient = user_in_db
    if not (isinstance(sender, User) and isinstance(recipient, User)):
        raise ValueError
    return sender, recipient


async def get_last_messages_date(all_message: dict) -> datetime:
    sender, sender_last_date = all_message['sender'], datetime.fromtimestamp(0)
    recipient, recipient_last_date = all_message['recipient'], datetime.fromtimestamp(0)
    if sender:
        sender_last_date = datetime.strptime(sender[-1]['created_at'], DATETIME_TEMPLATE)
    if recipient:
        recipient_last_date = datetime.strptime(recipient[-1]['created_at'], DATETIME_TEMPLATE)
    return sender_last_date if sender_last_date > recipient_last_date else recipient_last_date


def to_json_type(data) -> list:
    return list(map(lambda i: i.to_list(), data))
