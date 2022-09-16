import re
import time

from quart import request, make_response, websocket

from application import application, db
from server.crypt import Crypt
from server.models import User, Message

TEXT_DIRECTORY = 'text'

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
            'login содержит запрещённые символы (разрешены только буквы и цифры) или слишком длинный (максимум 24 символа)!',
            409)

    for user_in_db in User.query.all():
        if Crypt().decrypt(user_in_db.code) == login:
            return await make_response('Такой login уже существует!', 406)

    code = Crypt(login).encrypt()

    user = User(code=code)

    db.session.add(user)
    db.session.commit()
    return await make_response(code, 201)


@application.route(NAMESCPACES['chat'] + '/send_message', methods=['POST'])
async def chat_send_message():
    data = await request.form
    sender = data.to_dict().get('sender')
    recipient = data.to_dict().get('recipient')
    message = data.to_dict().get('message')
    if not message:
        return await make_response('Сообщение не может быть пустым!', 409)
    message = Crypt(message).encrypt()
    if not (sender and recipient and message):
        return await make_response('Вы передали не все обязательные параметры (sender, recipient, message)!', 400)
    for user_in_db in User.query.all():
        login_in_db = Crypt().decrypt(user_in_db.code)
        if login_in_db == sender:
            sender = user_in_db
        elif login_in_db == recipient:
            recipient = user_in_db
    if not (isinstance(sender, User) and isinstance(recipient, User)):
        return await make_response('Отправитель или получатель не найдены!', 400)
    message = Message(sender=sender.id, recipient=recipient.id, message=message)
    db.session.add(message)
    db.session.commit()

    return await make_response(message.message, 201)


@application.websocket(NAMESCPACES['chat'] + '/accept/<code>')
async def polling(code):
    print(code)
    while True:
        await websocket.send('data')
