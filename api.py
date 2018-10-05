import datetime
import json
import os
import signal
from multiprocessing import Process

import jwt
from flask import request, url_for, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin

from TwitterFetcher import TwitterFetcher
from models.models import User, Topic
from oauth import default_provider
from settings import app
from models.models import db
from util.security import ts
from util.mailers import ResetPasswordMailer

oauth = default_provider(app)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
db.create_all()
db = SQLAlchemy(app)
EXPIRATION_HOURS = 24


@app.route("/api/ping", methods=['GET'])
def ping():
    return "pong"

@app.route("/api/start_thread", methods=['POST'])
def track():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    print("Spawining process")
    p = init_process(target=start_fetching, args=(req["topic"], req["end"], req["lang"]))
    print("Running process")
    response = {"topic": req["topic"], "end": req["end"], "lang": req["lang"], "process": p.pid}
    app.logger.debug("Response: %s", response)
    return json.dumps(response)


@app.route("/api/finish_thread", methods=['POST'])
def finish():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    os.kill(req["process"], signal.SIGTERM)
    response = {"process": req["process"], "status": "killed"}
    return json.dumps(response)


@app.route("/api/sign_up", methods=['POST'])
def sign_up():
    req = request.get_json(force=True)
    app.logger.debug("Request: %s", req)
    user = User.query.filter((User.email == req["email"]) | (User.name == req["name"])).first()
    if user:
        return json.dumps({'error': 'Usuario existente', 'code': 400}), 400

    user = User.create_user(req['name'], req['email'], req['password'])
    expiration_date, token = generateToken(user)
    app.logger.debug("User: %s", user)
    return json.dumps(
        {'name': user.name, 'token': token.decode('utf-8'), 'expire_utc': int(expiration_date.timestamp() * 1000)}), 200


@app.route("/api/login", methods=['POST'])
@cross_origin()
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

@app.route('/api/password/reset_with_token/', methods=['POST'])
def reset_with_token():
    token = request.args.get('token')
    try:
        email = ts.loads(token, salt="recover-key", max_age=86400)
        req = request.get_json(force=True)
        password = req["password"]

        user = User.query.filter_by(email=email).first()
        user.password = password
        db.session.commit()
        return json.dumps({"status": "ok", "name": user.name})
    except:
        return "Expired token", 404

@app.route('/api/password/reset/', methods=["POST"])
def reset():
    req = request.get_json(force=True)
    email = req["email"]

    user = User.query.filter_by(email=email).first()
    if not user:
        return "User not found", 404

    subject = "SocialCAT - Reestablecer clave"
    token = ts.dumps(email, salt='recover-key')
    if request.environ['HTTP_ORIGIN'] is not None:
        recover_url = request.environ['HTTP_ORIGIN'] + '/password/reset_with_token/?token=' + token
        html = render_template(
            'recover_password.html',
            recover_url=recover_url)

        ResetPasswordMailer.send_email(user.email, subject, html)
        response = {"status": "ok"}
    else:
        response = {"status": "error"}
    return json.dumps(response)

def generateToken(user):
    expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=EXPIRATION_HOURS)
    token = jwt.encode({'user_id': user.id, 'exp': expiration_date}, app.secret_key, algorithm='HS256')
    return expiration_date, token


@app.route("/api/topics", methods=["GET"])
def get_topics():
    token, error = validate_token(request.headers)
    if error:
        return error
    app.logger.debug("Token: %s", token)
    topics = Topic.query.filter_by(user_id=token['user_id']).all()
    return json.dumps([topic.to_dict() for topic in topics])


@app.route("/api/topics", methods=["POST"])
def create_topic():
    token, error = validate_token(request.headers)
    if error:
        return error
    req = request.get_json(force=True)
    app.logger.debug("Token: %s, request: %s", token, req)
    req['deadline'] = datetime.datetime.strptime(req['deadline'], "%d-%m-%Y").date()
    topic = Topic.create(token['user_id'], req['name'], req['deadline'])
    return json.dumps(topic.to_dict())


@app.route("/api/topics/<topic_id>/results", methods=['GET'])
def get_results(topic_id):
    token, error = validate_token(request.headers)
    if error:
        return error
    app.logger.debug("Topic: %s", topic_id)
    # TODO
    return str(f"Results {topic_id}")


def validate_token(headers):
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
    app.run(debug=True, host='0.0.0.0', threaded=True)
