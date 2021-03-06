from flask_sqlalchemy import SQLAlchemy
from settings import app
from passlib.hash import bcrypt

import datetime

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    confirmed = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, name, password, email):
        self.name = name
        self.password = bcrypt.encrypt(password)
        self.email = email

    @staticmethod
    def create_user(name, email, password):
        user = User(name=name, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        return user

    def activate(self):
        self.confirmed = True
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def validate_password(user, password):
        return bcrypt.verify(password, user.password)

    topics = db.relationship("Topic", back_populates="user", cascade="all,delete")

    def __repr__(self):
        return f"<User(name='{self.name}', email='{self.email}', password='{self.password}')>"


class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String)
    deadline = db.Column(db.Date)
    language = db.Column(db.String)

    user = db.relationship("User", back_populates="topics")
    general_result = db.relationship("GeneralResult", uselist=False, backref="topic", cascade="all,delete")
    evolution_results = db.relationship("EvolutionResult", back_populates="topic", cascade="all,delete")
    location_results = db.relationship("LocationResult", back_populates="topic", cascade="all,delete")
    source_results = db.relationship("SourceResult", back_populates="topic", cascade="all,delete")

    def __repr__(self):
        return f"<Topic(name='{self.name}', deadline='{self.deadline}', " \
               f"owner='{self.user_id}', language='{self.language})>"

    @staticmethod
    def create(user_id, name, deadline, lang):
        topic = Topic(user_id=user_id, name=name, deadline=deadline, language=lang)
        db.session.add(topic)
        db.session.commit()
        return topic

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'user_id': self.user_id,
                'deadline': self.deadline.strftime('%d-%m-%Y'), 'language': self.language}


class GeneralResult(db.Model):
    __tablename__ = "general_results"

    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), primary_key=True)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)
    neutral = db.Column(db.Integer)

    @staticmethod
    def create(topic_id):
        result = GeneralResult(topic_id=topic_id, positive=0, negative=0, neutral=0)
        db.session.add(result)
        db.session.commit()
        return result

    @staticmethod
    def is_in(topic_id):
        results = GeneralResult.query \
            .filter(GeneralResult.topic_id == topic_id) \
            .all()
        return len(results) > 0

    def __repr__(self):
        return f"<GeneralResult(topic='{self.topic}', positive='{self.positive}', " \
               f"negative='{self.negative}', neutral='{self.neutral}')>"

    def to_dict(self):
        return {
            'topic_id': self.topic_id,
            'positive': self.positive,
            'negative': self.negative,
            'neutral': self.neutral
        }


class EvolutionResult(db.Model):
    __tablename__ = "evolution_results"

    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), primary_key=True)
    day = db.Column(db.Date, primary_key=True)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)
    neutral = db.Column(db.Integer)

    topic = db.relationship("Topic", back_populates="evolution_results")

    @staticmethod
    def create(topic_id, day):
        d = datetime.datetime.strptime(day, "%a %b %d %X %z %Y").date()
        result = EvolutionResult(topic_id=topic_id, day=d, positive=0, negative=0, neutral=0)
        db.session.add(result)
        db.session.commit()
        return result

    @staticmethod
    def is_in(topic_id, day):
        results = EvolutionResult.query\
            .filter(EvolutionResult.topic_id == topic_id)\
            .filter(EvolutionResult.day == datetime.datetime.strptime(day, "%d-%m-%Y").date())\
            .all()
        return len(results) > 0

    def __repr__(self):
        return f"<EvolutionResult(topic='{self.topic}', positive='{self.positive}', " \
               f"negative='{self.negative}', neutral='{self.neutral}', day='{self.day}')>"

    def to_dict(self):
        return {
            'topic_id': self.topic_id,
            'positive': self.positive,
            'negative': self.negative,
            'neutral': self.neutral,
            'day': datetime.datetime.strftime(self.day, "%d-%m-%Y")
        }


class LocationResult(db.Model):
    __tablename__ = "location_results"

    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), primary_key=True)
    location = db.Column(db.String, primary_key=True)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)
    neutral = db.Column(db.Integer)

    topic = db.relationship("Topic", back_populates="location_results")

    @staticmethod
    def create(topic_id, location):
        result = LocationResult(topic_id=topic_id, location=location, positive=0, negative=0, neutral=0)
        db.session.add(result)
        db.session.commit()
        return result

    @staticmethod
    def is_in(topic_id, location):
        results = LocationResult.query \
            .filter(LocationResult.topic_id == topic_id) \
            .filter(LocationResult.location == location) \
            .all()
        return len(results) > 0

    def __repr__(self):
        return f"<LocationResult(topic='{self.topic}', positive='{self.positive}', " \
               f"negative='{self.negative}', neutral='{self.neutral}', location='{self.location}')>"

    def to_dict(self):
        return {
            'topic_id': self.topic_id,
            'positive': self.positive,
            'negative': self.negative,
            'neutral': self.neutral,
            'location': self.location
        }


class SourceResult(db.Model):
    __tablename__ = "source_results"

    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), primary_key=True)
    source = db.Column(db.String, primary_key=True)
    positive = db.Column(db.Integer)
    negative = db.Column(db.Integer)
    neutral = db.Column(db.Integer)

    topic = db.relationship("Topic", back_populates="source_results")

    @staticmethod
    def create(topic_id, source):
        result = SourceResult(topic_id=topic_id, source=source, positive=0, negative=0, neutral=0)
        db.session.add(result)
        db.session.commit()
        return result

    @staticmethod
    def is_in(topic_id, source):
        results = SourceResult.query\
            .filter(SourceResult.topic_id == topic_id)\
            .filter(SourceResult.source == source)\
            .all()
        return len(results) > 0

    def __repr__(self):
        return f"<SourceResult(topic='{self.topic}', positive='{self.positive}', " \
               f"negative='{self.negative}', neutral='{self.neutral}', source='{self.source}')>"

    def to_dict(self):
        return {
            'topic_id': self.topic_id,
            'positive': self.positive,
            'negative': self.negative,
            'neutral': self.neutral,
            'source': self.source
        }


# OAuth Models


class Client(db.Model):
    name = db.Column(db.String(40))
    description = db.Column(db.String(400))
    user_id = db.Column(db.ForeignKey('users.id'))
    user = db.relationship('User')

    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(db.String(55), unique=True, index=True,
                              nullable=False)

    is_confidential = db.Column(db.Boolean)
    _redirect_uris = db.Column(db.Text)
    _default_scopes = db.Column(db.Text)

    @property
    def client_type(self):
        if self.is_confidential:
            return 'confidential'
        return 'public'

    @property
    def redirect_uris(self):
        if self._redirect_uris:
            return self._redirect_uris.split()
        return []

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    @property
    def default_scopes(self):
        if self._default_scopes:
            return self._default_scopes.split()
        return []


class Grant(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')
    code = db.Column(db.String(255), index=True, nullable=False)
    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)
    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []


class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id')
    )
    user = db.relationship('User')
    token_type = db.Column(db.String(40))
    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    _scopes = db.Column(db.Text)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self

    @property
    def scopes(self):
        if self._scopes:
            return self._scopes.split()
        return []
