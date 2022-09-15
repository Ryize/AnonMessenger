from flask import Flask

app = Flask(__name__)
TEXT_DIRECTORY = 'text'


NAMESCPACES = {
    'auth': '/auth',
    'chat': 'chat/',
    'info': '/',
}


@app.route(NAMESCPACES['auth'])
def auth_index():
    with open(TEXT_DIRECTORY+'/help_auth.txt', 'r', encoding='utf-8') as file:
        return file.read()

if __name__ == '__main__':
    app.run()
