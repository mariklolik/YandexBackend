import datetime
import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID

import uuid
from .db_session import SqlAlchemyBase


class Category(SqlAlchemyBase):
    __tablename__ = 'data'
    numericid = sqlalchemy.Column('numericid', sqlalchemy.Integer, primary_key=True, autoincrement=True)
    id = sqlalchemy.Column('id', sqlalchemy.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=False)
    parentId = sqlalchemy.Column('parentId', sqlalchemy.Text(length=36), default=None,
                                 primary_key=False)

    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    price = sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=0)
    date  = sqlalchemy.Column(sqlalchemy.DateTime)
    latest = sqlalchemy.Column(sqlalchemy.Boolean, default=True)
    type = sqlalchemy.Column(sqlalchemy.String, nullable=False)
