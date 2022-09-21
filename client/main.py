import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pywebio.session
import requests
import websockets
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
from websockets.exceptions import InvalidStatusCode

from config import SERVER_URL

DATETIME_TEMPLATE = '%Y-%m-%d %H:%M:%S.%f'

# TODO: 1) Провести масштабный рефакторинг кода, пока это не разрослось в большую проблему (Critical);
# TODO: 2) Новый диалог попадает на предпоследний элемент (Bug); (✅)
# TODO: 3) Окрасить кнопку "Создать диалог" в какой-нибудь цвет (Minor);
# TODO: 4) Попробовать убрать кнопку "Сброс", толку от неё нет (Minor);
# TODO: 5) Попроовать убрать фразу с тайтлом библиотеки на сайте (Will).


@dataclass
class Storage:
    code: str
    msg_box: Any
    dialogs: list
    recipient: str
    all_messages: list


async def main():
    msg_box = output()
    pywebio.session.set_env(title='Анонимный мессенджер Ryize')
    Storage.msg_box = msg_box
    put_markdown("<center><h2>Анонимный мессенджер Ryize</h2></center>")
    action = await actions("Выберите действие: ", ["Войти", "Регистрация"])
    if action == "Регистрация":
        login = await input('Введите login:')
        Storage.code = login

        res = requests.post(SERVER_URL + '/auth/register', data={'login': login})
        Storage.code = res.text
        if res.status_code != 201:
            Storage.msg_box.append(put_markdown(f'❌ <strong>Возникла ошибка: {Storage.code}</strong>'))
            put_buttons(["Начать заново"], onclick=lambda btn: run_js('window.location.reload()'))
        put_scrollable(Storage.msg_box, height=400, keep_bottom=True)
        Storage.msg_box.append(put_markdown(f'❗️❗️❗️Ваш код для входа, не потеряйте его!\n<i>{Storage.code}</i>'))

    elif action == "Войти":
        code = await input('Введите код:')
        Storage.code = code
        put_scrollable(Storage.msg_box, height=400, keep_bottom=True)
    else:
        toast('❌ Вы указали неверное действие!')
        put_buttons(["Начать заново"], onclick=lambda btn: run_js('window.location.reload()'))

    run_async(refresh_msg())

    while True:
        try:
            recipient = Storage.recipient
            data = await input_group('Отправить сообщение', [input('Введите текст сообщения...', name='message')])
            post_data = {
                'sender': Storage.code,
                'recipient': recipient,
                'message': data['message'],
            }
            requests.post(SERVER_URL + '/chat/send_message', data=post_data)
        except AttributeError:
            await asyncio.sleep(0.25)


async def refresh_msg():
    try:
        async with websockets.connect(f'ws://127.0.0.1:5000/chat/accept/{Storage.code}') as websocket:
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
            Storage.dialogs = list(set(dialogs))
            recipient = await actions("Выберите диалог: ", list(set(dialogs)))
            await change_dialog(recipient)
            await display_list_of_dialogs()
            first_iter = False
        if messages:
            for message in messages:
                if not (isinstance(message, dict)) or message['recipient'] != Storage.recipient:
                    continue
                Storage.all_messages.append(message)
                Storage.msg_box.append(put_markdown(f"`{message['sender']}`: {message['message']}"))
            Storage.msg_box.append()


async def change_dialog(btn: str):
    if not await check_new_dialog(btn):
        Storage.recipient = btn
        messages_in_dialog = [i for i in Storage.all_messages if i['sender'] == btn or i['recipient'] == btn]
        Storage.msg_box.append(
            put_markdown(f'\n\n{"-" * 32}\n\n<strong>Диалог с <i>{Storage.recipient}</i></strong>\n'))
        for message in messages_in_dialog:
            Storage.msg_box.append(put_markdown(f"`{message['sender']}`: {message['message']}"))
        Storage.msg_box.append()


async def check_new_dialog(message: str) -> bool:
    if message != 'Создать диалог':
        return False
    with use_scope('buttons_under_chat'):
        clear()
        data = await input_group('Создать диалог', [input('Введите ник...', name='recipient')])
        post_data = {
            'sender': Storage.code,
            'recipient': data['recipient'],
            'message': '👐',
        }
        res = requests.post(SERVER_URL + '/chat/send_message', data=post_data)
        if res.status_code != 201:
            toast(f'❌ {res.text}')
        else:
            Storage.dialogs.append(data['recipient'])
            Storage.dialogs.append(Storage.dialogs.pop(-1))
            await change_dialog(data['recipient'])
    with use_scope('buttons_under_chat'):
        await display_list_of_dialogs()


async def display_list_of_dialogs():
    with use_scope('buttons_under_chat'):
        put_buttons([dict(label='Создать диалог', value='Создать диалог', color='success')], onclick=check_new_dialog)
        put_buttons(Storage.dialogs, onclick=change_dialog)


async def get_list_with_dialogs(messages: dict):
    dialogs = []
    all_messages = []
    for i in [messages['sender'], messages['recipient']]:
        for user in i:
            dialogs.append(user['sender'] if user['recipient'] == messages['login'] else user['recipient'])
            all_messages.append(user)
    all_messages.sort(key=lambda i: datetime.strptime(i['created_at'], DATETIME_TEMPLATE))
    Storage.dialogs = dialogs
    Storage.all_messages = all_messages
    return dialogs


if __name__ == "__main__":
    start_server(main, debug=True, port=8080)
