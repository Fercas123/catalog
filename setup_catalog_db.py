import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__='user'
    id= Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email= Column(String(250), nullable=False)
    picture = Column(String(250))

class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        #returns object data in easily serializable format
        return{
            'name': self.name,
            'id': self.id,
        }


class Project(Base):
    __tablename__ = 'project'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    howto = Column(String(500))
    complexity = Column(String(8))
    category_id = Column(Integer, ForeignKey('category.id'))
    category = relationship(Category)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        #returns object data in easily serializable format
        return{
            'name': self.name,
            'description':self.description,
            'id': self.id,
            'complexity': self.complexity,
        }


engine = create_engine('sqlite:///projectscategories.db')


Base.metadata.create_all(engine)