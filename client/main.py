import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pywebio.session
import requests
import websockets
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import run_async, run_js
from websockets.exceptions import InvalidStatusCode

from config import SERVER_URL

DATETIME_TEMPLATE = "%Y-%m-%d %H:%M:%S.%f"


# TODO: 1) Провести масштабный рефакторинг кода, пока это не разрослось в большую проблему (Critical) (✅);
# TODO: 2) Новый диалог попадает на предпоследний элемент (Bug); (✅)
# TODO: 3) Окрасить кнопку "Создать диалог" в какой-нибудь цвет (Minor) (✅);
# TODO: 4) Попробовать убрать кнопку "Сброс", толку от неё нет (Minor) (❌ Технически невозможно);
# TODO: 5) Попробовать убрать фразу с тайтлом библиотеки на сайте (Will) (✅).


@dataclass
class Storage:
    """
    Класс для хранения основных данных программы
    """
    code: str  # Код используемый для входа в систему
    msg_box: Any  # Объект получаемый от pywebio.output
    dialogs: list  # Список со всеми людьми, которым писал пользователь
    all_messages: list  # Все сообщения, которые были отправлены пользователем
    recipient: Optional[str] = None  # Получатель (обычно сообщения)


async def main():
    async def _register() -> None:
        """
        Используется для регистрации на платформе, устанавливает Strotage.code.
        :return: None
        """
        login = await input("Введите login:")
        Storage.code = login
        res = requests.post(SERVER_URL + "/auth/register", data={"login": login})
        Storage.code = res.text
        if res.status_code != 201:
            Storage.msg_box.append(
                put_markdown(f"❌ <strong>Возникла ошибка: {Storage.code}</strong>")
            )
            put_buttons(
                ["Начать заново"],
                onclick=lambda btn: run_js("window.location.reload()"),
            )
        put_scrollable(Storage.msg_box, height=400, keep_bottom=True)
        Storage.msg_box.append(
            put_markdown(
                f"❗️❗️❗️Ваш код для входа, не потеряйте его!\n<i>{Storage.code}</i>"
            )
        )

    async def _login() -> None:
        """
        Используется для авторизации в системе, устанавливает Strotage.code.
        :return: None
        """
        code = await input("Введите код:")
        Storage.code = code
        put_scrollable(Storage.msg_box, height=400, keep_bottom=True)

    async def _message_sending_block() -> None:
        """
        Блок отправки сообщения, добавляет блок "Отправить сообщение", устанавливает Storage.recipient.
        :return: None
        """
        while True:
            try:
                recipient = Storage.recipient
                data = await input_group(
                    "Отправить сообщение",
                    [input("Введите текст сообщения...", name="message")],
                )
                post_data = {
                    "sender": Storage.code,
                    "recipient": recipient,
                    "message": data["message"],
                }
                requests.post(SERVER_URL + "/chat/send_message", data=post_data)
            except AttributeError:
                await asyncio.sleep(0.25)

    async def _select_action(_login, _register, action: str) -> None:
        """
        Используется для вызова действия (регистрация, авторизация. В случае иного выбора выведет предупреждение и кнопку "Начать заново")
        :param _login: function (функция для авторизации)
        :param _register: function (функция для регистрации)
        :param action: str (выбранное действие)
        :return:
        """
        if action == "Регистрация":
            await _register()

        elif action == "Войти":
            await _login()
        else:
            toast("❌ Вы указали неверное действие!")
            put_buttons(
                ["Начать заново"],
                onclick=lambda btn: run_js("window.location.reload()"),
            )

    msg_box = output()
    pywebio.session.set_env(title="Анонимный мессенджер Ryize")
    Storage.msg_box = msg_box
    run_js("elem=document.getElementsByTagName(`footer`)[0]; elem.parentNode.removeChild(elem)")
    put_markdown("<center><h2>Анонимный мессенджер Ryize</h2></center>")
    action = await actions("Выберите действие: ", ["Войти", "Регистрация"])
    await _select_action(_login, _register, action)

    run_async(refresh_msg())

    await _message_sending_block()


async def refresh_msg() -> None:
    """
    Добавляет сообщение на экран, когда оно пришло.
    :return: None
    """
    try:
        await get_list_with_dialogs()
        await display_list_of_dialogs()
        while True:
            if Storage.recipient:
                async with websockets.connect(
                        f"ws://127.0.0.1:5000/chat/accept/{Storage.code}/{Storage.recipient}"
                ) as websocket:
                    await update_message(websocket)
            await asyncio.sleep(0.75)
    except InvalidStatusCode:
        clear()
        put_markdown(f"❌ <strong>Неверный код!</strong>")
        put_buttons(
            ["Попробовать снова"],
            onclick=lambda btn: run_js("window.location.reload()"),
        )


async def update_message(websocket) -> None:
    """
    Для работы с добавлением диалогов, сообщений, работой с новыми сообщениями.
    :param websocket (объект возвращаемый websockets.connect)
    :return: None
    """

    async def _first_update_message(messages: dict) -> None:
        """
        Выводит список уникальных диалогов.
        :param messages: dict (словарь с сообщениями, который передал сервер)
        :return: None
        """
        dialogs = await get_list_with_dialogs(messages)
        Storage.dialogs = list(set(dialogs))
        recipient = await actions("Выберите диалог: ", list(set(dialogs)))
        await change_dialog(recipient)
        await display_list_of_dialogs()

    async def _output_new_message(messages: dict) -> None:
        """
        Выводит пришедшее сообщение.
        :param messages: dict (словарь с сообщением передаваемый сервером)
        :return: None
        """
        for message in messages:
            if (
                    not (isinstance(message, dict))
                    or message["recipient"] != Storage.recipient
            ):
                continue
            Storage.all_messages.append(message)
            Storage.msg_box.append(
                put_markdown(f"`{message['sender']}`: {message['message']}")
            )
        Storage.msg_box.append()

    while True:
        messages = await websocket.recv()
        messages = json.loads(messages)
        if messages:
            await _output_new_message(messages)


async def change_dialog(btn: str) -> None:
    """
    Используется для изменения текущего диалога, изменяет Storage.recipient.
    :param btn: str (пользователь, с которым мы теперь общаемся)
    :return: None
    """
    if not await check_new_dialog(btn):
        Storage.recipient = btn
        messages_in_dialog = [
            i
            for i in Storage.all_messages
            if i["sender"] == btn or i["recipient"] == btn
        ]
        Storage.msg_box.append(
            put_markdown(
                f'\n\n{"-" * 32}\n\n<strong>Диалог с <i>{Storage.recipient}</i></strong>\n'
            )
        )
        for message in messages_in_dialog:
            Storage.msg_box.append(
                put_markdown(f"`{message['sender']}`: {message['message']}")
            )
        Storage.msg_box.append()


async def check_new_dialog(message: str) -> bool:
    """
    Создаёт диалог на сервере и проверяет получившийся результат (по коду).
    :param message: str
    :return: bool
    """

    async def _get_send_data() -> dict:
        """
        Отправляет сообщение "👐" на сервер, для создания диалога.
        :return: dict (словарь с сообщением, получаемый от сервера)
        """
        data = await input_group(
            "Создать диалог", [input("Введите ник...", name="recipient")]
        )
        post_data = {
            "sender": Storage.code,
            "recipient": data["recipient"],
            "message": "👐",
        }
        return post_data

    async def _check_res(post_data: dict, res) -> None:
        """
        Проверка результата запроса, в случае кода ответа != 201, выводит ошибку.
        :param post_data: dict (словарь с данными от сервера)
        :param res: (объект, возвращаемый requests.post)
        :return: None
        """
        if res.status_code != 201:
            toast(f"❌ {res.text}")
        else:
            Storage.dialogs.append(post_data["recipient"])
            Storage.dialogs.append(Storage.dialogs.pop(-1))
            await change_dialog(post_data["recipient"])

    if message != "Создать диалог":
        return False
    with use_scope("buttons_under_chat"):
        clear()
        post_data = await _get_send_data()
        res = requests.post(SERVER_URL + "/chat/send_message", data=post_data)
        await _check_res(post_data, res)
    with use_scope("buttons_under_chat"):
        await display_list_of_dialogs()


async def display_list_of_dialogs() -> None:
    """
    Выводит список диалогов на сайте.
    :return: None
    """
    with use_scope("buttons_under_chat"):
        put_buttons(
            [dict(label="Создать диалог", value="Создать диалог", color="success")],
            onclick=check_new_dialog,
        )
        put_buttons(Storage.dialogs, onclick=change_dialog)


async def get_list_with_dialogs(messages: Optional[dict] = None) -> list:
    """
    Возвращает список всех диалогов пользователя.
    :param messages: list (список с сообщениями [0] - sender, [1] - recipient)
    :return:
    """
    dialogs = []
    all_messages = []
    messages = messages or json.loads(
        requests.post(f'{SERVER_URL}/chat/get_all_messages', data={'code': Storage.code}).text)
    for i in [messages["sender"], messages["recipient"]]:
        for user in i:
            dialogs.append(
                user["sender"]
                if user["recipient"] == messages["login"]
                else user["recipient"]
            )
            all_messages.append(user)
    all_messages.sort(
        key=lambda i: datetime.strptime(i["created_at"], DATETIME_TEMPLATE)
    )
    Storage.dialogs = list(set(dialogs))
    Storage.all_messages = all_messages
    return dialogs


if __name__ == "__main__":
    start_server(main, debug=True, port=8080, remote_access=True)
