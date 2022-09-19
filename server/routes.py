import asyncio
import json
import re

from cryptography.fernet import InvalidToken
from quart import request, make_response, websocket

from application import application, TEXT_DIRECTORY
from server.buisness_logic import get_all_user_messages, login_existence_check, get_last_messages_date, to_json_type, \
    user_existence_check
from server.crypt import Crypt
from server.models import User, Message

NAMESCPACES = {
    'auth': '/auth',
    'chat': '/chat',
    'info': '/',
}


@application.route(NAMESCPACES['auth'])
async def auth_index():
    with open(TEXT_DIRECTORY + '/help_auth.txt', 'r', encoding='utf-8') as file:
        return file.read()


@application.route(NAMESCPACES['auth'] + '/register', methods=['POST'])
async def auth_register():
    login = await request.form
    login = login.to_dict().get('login')

    if not login:
        return await make_response('Вы не передали обязательный параметр login!', 400)

    # Проверка, что логин содержит только буквы и цифры
    if not re.fullmatch(r'[a-zA-Z0-9]*', login) or len(login) > 24:
        return await make_response(
            'login содержит запрещённые символы (разрешены только буквы и цифры) или слишком длинный (максимум 24 '
            'символа)!',
            409)

    if User.query.filter_by(login=login).first():
        return await make_response('Такой login уже существует!', 406)

    User.create(login=login)

    code = Crypt(login).encrypt()
    return await make_response(code, 201)


@application.route(NAMESCPACES['chat'] + '/send_message', methods=['POST'])
async def chat_send_message():
    data = await request.form
    try:
        sender = Crypt(data.to_dict().get('sender')).decrypt()
    except InvalidToken:
        sender = data.to_dict().get('sender')
    recipient = data.to_dict().get('recipient')
    message = data.to_dict().get('message')
    if not message:
        return await make_response('Сообщение не может быть пустым!', 409)
    message = Crypt(message).encrypt()
    if not (sender and recipient and message):
        return await make_response('Вы передали не все обязательные параметры (sender, recipient, message)!', 400)

    try:
        sender, recipient = await user_existence_check(sender, recipient)
    except ValueError:
        return await make_response('Отправитель или получатель не найдены!', 400)

    message = Message.create(sender=sender.id, recipient=recipient.id, message=message)

    return await make_response(message.message, 201)


@application.websocket(NAMESCPACES['chat'] + '/accept/<code>')
async def polling(code: str):
    try:
        user = await login_existence_check(code)
    except InvalidToken:
        return await websocket.close(code=400)

    all_messages = await get_all_user_messages(user)
    last_message_date = await get_last_messages_date(json.loads(all_messages))
    await websocket.send(all_messages)

    while True:
        new_message = Message.query.filter(Message.created_at > last_message_date,
                                           (Message.sender == user.id) | (Message.recipient == user.id)).all()
        if new_message:
            new_message = to_json_type(new_message)
            await websocket.send(json.dumps(new_message))
            last_message_date = new_message[-1]['created_at']
        await asyncio.sleep(1)
