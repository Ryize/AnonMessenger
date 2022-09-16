from typing import Optional

import config
from cryptography.fernet import Fernet


class Crypt:
    __key = config.SECRET_KEY
    __fernet = Fernet(__key)

    def __init__(self, message: Optional[str] = None):
        self.message = message

    def encrypt(self, message: Optional[str] = None) -> str:
        message = self.message or message
        return self.__fernet.encrypt(message.encode()).decode()

    def decrypt(self, message: Optional[str] = None) -> str:
        message = self.message or message
        return self.__fernet.decrypt(message).decode()
