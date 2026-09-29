import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from projectg.infrastructure.persistence.sqlite.base import Base
from projectg.infrastructure.persistence.sqlite import models  # noqa: F401 - register ORM tables before create_all


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def good_json():
    return {
        "format": "GOOD",
        "version": 1,
        "dbVersion": 60,
        "characters": [
            {
                "key": "RaidenShogun",
                "level": 80,
                "ascension": 5,
                "constellation": 2,
                "talent": {"auto": 8, "skill": 9, "burst": 10},
            },
            {
                "key": "Fischl",
                "level": 70,
                "ascension": 4,
                "constellation": 6,
                "talent": {"auto": 8, "skill": 8, "burst": 8},
            },
        ],
        "weapons": [
            {
                "id": "w1",
                "key": "EngulfingLightning",
                "level": 90,
                "ascension": 6,
                "refinement": 1,
                "location": "RaidenShogun",
            },
            {
                "id": "w2",
                "key": "TheCatch",
                "level": 80,
                "ascension": 5,
                "refinement": 5,
                "location": "RaidenShogun",
            },
            {
                "id": "w3",
                "key": "Stringless",
                "level": 70,
                "ascension": 4,
                "refinement": 2,
                "location": "Fischl",
            },
        ],
        "artifacts": [
            {
                "id": "a1",
                "setKey": "EmblemOfSeveredFate",
                "slotKey": "flower",
                "rarity": 5,
                "level": 20,
                "mainStatKey": "hp",
                "substats": [{"key": "critRate", "value": 10}],
                "location": "RaidenShogun",
            },
            {
                "id": "a2",
                "setKey": "GildedDreams",
                "slotKey": "flower",
                "rarity": 5,
                "level": 20,
                "mainStatKey": "hp",
                "substats": [],
                "location": "Fischl",
            },
            {
                "id": "a3",
                "setKey": "unused",
                "slotKey": "flower",
                "rarity": 5,
                "level": 0,
                "mainStatKey": "hp",
                "substats": [],
                "location": "",
            },
        ],
        "teams": [
            {
                "id": "t1",
                "name": "Overload",
                "members": ["RaidenShogun", "Fischl"],
                "config": {"conditional": True},
            }
        ],
    }
