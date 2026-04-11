import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.db import Base, init_db


@pytest.fixture(scope="function")
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/test.db")
    init_db(eng)
    return eng


@pytest.fixture(scope="function")
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
