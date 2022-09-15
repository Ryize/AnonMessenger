import config
from cryptography.fernet import Fernet

message = "hello geeks"

key = config.SECRET_KEY
print(key)

fernet = Fernet(key)

encMessage = fernet.encrypt(message.encode())

print("original string: ", message)
print("encrypted string: ", encMessage)

decMessage = fernet.decrypt(encMessage).decode()

print("decrypted string: ", decMessage)
