import json
from datetime import datetime

import requests
import websockets
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
from websockets.exceptions import InvalidStatusCode

from config import SERVER_URL

DATETIME_TEMPLATE = '%Y-%m-%d %H:%M:%S.%f'


async def main():
    global msg_box
    msg_box = output()
    action = await actions("Выберите действие: ", ["Войти", "Регистрация"])
    if action == "Регистрация":
        login = await input('Введите login:')
        put_markdown("Анонимный мессенджер Ryize")

        res = requests.post(SERVER_URL + '/auth/register', data={'login': login})
        code = res.text
        if res.status_code != 201:
            msg_box.append(put_markdown(f'❌ <strong>Возникла ошибка: {code}</strong>'))
            put_buttons(["Начать заново"], onclick=lambda btn: run_js('window.location.reload()'))
        put_scrollable(msg_box, height=400, keep_bottom=True)
        msg_box.append(put_markdown(f'❗️❗️❗️Ваш код для входа, не потеряйте его!\n<i>{code}</i>'))

    elif action == "Войти":
        code = await input('Введите код:')
        put_markdown("Анонимный мессенджер Ryize")
        put_scrollable(msg_box, height=400, keep_bottom=True)
    else:
        toast('❌ Вы указали неверное действие!')
        put_buttons(["Начать заново"], onclick=lambda btn: run_js('window.location.reload()'))

    run_async(refresh_msg(code))

    while True:
        data = await input_group('Отправить сообщение', [input('Введите текст сообщения...', name='message')])
        post_data = {
            'sender': code,
            'recipient': recipient,
            'message': data['message'],
        }
        requests.post(SERVER_URL + '/chat/send_message', data=post_data)


async def refresh_msg(code: str):
    global all_messages, recipient
    all_messages = []

    try:
        async with websockets.connect(f'ws://127.0.0.1:5000/chat/accept/{code}') as websocket:
            await update_message(websocket)
    except InvalidStatusCode:
        clear()
        put_markdown(f'❌ <strong>Неверный код!</strong>')
        put_buttons(["Попробовать снова"], onclick=lambda btn: run_js('window.location.reload()'))


async def update_message(websocket):
    first_iter = True
    while True:
        messages = await websocket.recv()
        messages = json.loads(messages)
        if first_iter:
            dialogs = await get_list_with_dialogs(messages)
            recipient = await actions("Выберите диалог: ", list(set(dialogs)))
            await change_dialog(recipient)
            with use_scope('buttons_under_chat'):
                list_unique_dialogs = list(set(dialogs))
                list_unique_dialogs.append('Создать диалог')
                put_buttons(list_unique_dialogs, onclick=change_dialog)
            first_iter = False
        if messages:
            for message in messages:
                if not (isinstance(message, dict)) or message['recipient'] != recipient:
                    continue
                all_messages.append(message)
                msg_box.append(put_markdown(f"`{message['sender']}`: {message['message']}"))
                with use_scope('buttons_under_chat'):
                    clear()
                    put_buttons(['wddwdwdw'], onclick=change_dialog)
            msg_box.append()


async def change_dialog(btn: str):
    global recipient
    recipient = btn
    messages_in_dialog = [i for i in all_messages if i['sender'] == btn or i['recipient'] == btn]
    msg_box.append(put_markdown(f'\n\n{"-" * 32}\n\n<strong>Диалог с <i>{recipient}</i></strong>\n'))
    for message in messages_in_dialog:
        msg_box.append(put_markdown(f"`{message['sender']}`: {message['message']}"))
    msg_box.append()


async def check_new_dialog(message: str) -> bool:
    if message != 'Создать диалог':
        return False
    pass


async def get_list_with_dialogs(messages: dict):
    global all_messages
    dialogs = []
    all_messages = []
    for i in [messages['sender'], messages['recipient']]:
        for user in i:
            dialogs.append(user['sender'] if user['recipient'] == messages['login'] else user['recipient'])
            all_messages.append(user)
    all_messages.sort(key=lambda i: datetime.strptime(i['created_at'], DATETIME_TEMPLATE))
    return dialogs


if __name__ == "__main__":
    start_server(main, debug=True, port=8080, cdn=False)
