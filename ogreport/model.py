from datetime import datetime
from sqlalchemy import Column, Unicode, Float
from sqlalchemy import DateTime, Integer, UnicodeText
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
import geoalchemy as geo


maker = sessionmaker(autoflush=True, autocommit=False,
                     extension=ZopeTransactionExtension())


DBSession = scoped_session(maker)
DeclarativeBase = declarative_base()
metadata = DeclarativeBase.metadata


class Spot(DeclarativeBase):
    __tablename__ = 'spots'
    id = Column(Integer, primary_key=True)
    name = Column(Unicode, nullable=True)
    text = Column(UnicodeText, nullable=True)
    image_path = Column(Unicode, nullable=True)
    altitude = Column(Float)
    accuracy = Column(Float)
    alt_accuracy = Column(Float)
    heading = Column(Integer)
    speed = Column(Float)
    created = Column(DateTime, default=datetime.now())
    geom = geo.GeometryColumn(geo.Point(2))


geo.GeometryDDL(Spot.__table__)


def init_model(engine):
    """Call me before using any of the tables or classes in the model."""

    DBSession.configure(bind=engine)
