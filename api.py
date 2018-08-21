import os
import json
import signal
import datetime
import jwt
from flask import request
from multiprocessing import Process
from TwitterFetcher import TwitterFetcher
from settings import app
from oauth import default_provider
from models.models import User, Topic
from flask_sqlalchemy import SQLAlchemy

oauth = default_provider(app)
db = SQLAlchemy(app)
EXPIRATION_HOURS = 24


@app.route("/start_thread", methods=['POST'])
def track():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    p = init_process(target=start_fetching, args=(req["topic"], req["end"], req["lang"]))
    response = {"topic": req["topic"], "end": req["end"], "lang": req["lang"], "process": p.pid}
    app.logger.debug("Response: %s", response)
    return json.dumps(response)


@app.route("/finish_thread", methods=['POST'])
def finish():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    os.kill(req["process"], signal.SIGTERM)
    response = {"process": req["process"], "status": "killed"}
    return json.dumps(response)


@app.route("/sign_up", methods=['POST'])
def sign_up():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    user = User.query.filter_by(name=req["name"]).first()
    if user:
        return json.dumps({'error': 'Usuario existente', 'code': 400}), 400

    user = User.create_user(req['name'], req['email'], req['password'])
    expiration_date, token = generateToken(user)
    app.logger.debug("User: %s", user)
    return json.dumps(
        {'name': user.name, 'token': token.decode('utf-8'), 'expire_utc': int(expiration_date.timestamp() * 1000)}), 200


@app.route("/login", methods=['POST'])
def login():
    req = request.get_json(force=True)
    name = req["name"]
    if not name:
        return json.dumps({'error': 'Nombre de usuario o email', 'code': 400}), 400
    password = req["password"]
    if not password:
        return json.dumps({'error': 'Una clave debe ser provista', 'code': 400}), 400
    user = User.query.filter_by(name=name).first()
    if not user or not User.validate_password(user, password):
        return json.dumps({'error': 'Usuario o clave incorrectos', 'code': 400}), 400

    expiration_date, token = generateToken(user)

    return json.dumps(
        {'name': user.name, 'token': token.decode('utf-8'), 'expire_utc': int(expiration_date.timestamp() * 1000)}), 200


def generateToken(user):
    expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=EXPIRATION_HOURS)
    token = jwt.encode({'user_id': user.id, 'exp': expiration_date}, app.secret_key, algorithm='HS256')
    return expiration_date, token


@app.route("/topics", methods=["GET"])
def get_topics():
    token, error = validateToken(request.headers)
    if error:
        return error
    app.logger.debug("Token: %s", token)
    topics = Topic.query.filter_by(user_id=token['user_id']).all()
    return json.dumps(topics)

@app.route("/topics/<topic_id>/results", methods=['GET'])
def get_results(topic_id):
    token, error = validateToken(request.headers)
    if error:
        return error
    app.logger.debug("Topic: %s", topic_id)
    # TODO
    return str(f"Results {topic_id}")


def validateToken(headers):
    token = headers.get('token')
    if not token:
        return None, ('Token missing', 400)

    token = jwt.decode(token, app.secret_key, algorithms=['HS256'])
    if datetime.datetime.utcfromtimestamp(token['exp']) < datetime.datetime.utcnow():
        return None, ('Expired token', 401)

    return token, None


def start_fetching(topic, end=datetime.date.today(), lang='es'):
    twitter_fetcher = TwitterFetcher()
    twitter_fetcher.stream(topic, languages=[lang])


def init_process(target, args):
    p = Process(target=target, args=args)
    p.daemon = True
    p.start()
    return p


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
