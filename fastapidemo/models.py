from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import *

from settings import settings

db = create_engine(settings.db, echo=False)
AutoBase = automap_base()
INITFLAG = False


class Detect(AutoBase):
    __tablename__ = "dungeon_detect"
    ship = relationship("Ship", back_populates="detect_collection", lazy="selectin")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.ship_id}>"


class Ship(AutoBase):
    __tablename__ = "dungeon_ship"
    detect_collection = relationship("Detect", back_populates="ship", lazy="selectin")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.token_id} {self.name}>"


if not INITFLAG:
    AutoBase.prepare(autoload_with=db)
    INITFLAG = True
