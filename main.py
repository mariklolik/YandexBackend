from dbremote import db_session
from flask import Flask
import os
import json
import api_new

app = Flask(__name__)
app.config["SECRET_KEY"] = "sk"
UPLOAD_FOLDER = '/data'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/400')
@app.errorhandler(400)
def val_failed_error():
    return json.loads("{\n  \"code\": 400,\n  \"message\": \"Validation Failed\"\n}"), 400

@app.route('/404')
@app.errorhandler(404)
def not_found_error():
    return json.loads("{\n  \"code\": 404,\n  \"message\": \"Item not found\"\n}"), 404


def main():
    db_session.global_init("db/data.sqlite")
    port = int(os.environ.get("PORT", 80))
    app.register_blueprint(api_new.blueprint)
    app.run(port=port, host='0.0.0.0', debug=True)
    return 0


if __name__ == "__main__":
    main()
