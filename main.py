import requests
import json
from flask import Flask

app = Flask(__name__)


@app.route('/imports', methods=['POST'])
def imports():
    return 'привте'


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1')
    #app.run(port=80, host='0.0.0.0')
