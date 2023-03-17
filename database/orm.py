from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime, timezone
import pytz

from settings import db_settings
from .models import Base, User, BlockedUser

engine = create_engine(db_settings.URL, echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def add_user(tg_id, username):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user is None:
        new_user = User(tg_id=tg_id, username=username)
        session.add(new_user)
        session.commit()
        return 1
    else:
        return -1

def check_premium(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user.admin == True:
        return 1
    if user.premium == True:
        current_time_utc =  datetime.now(timezone.utc)
        end_date = user.premium_end_date
        if current_time_utc > pytz.timezone('UTC').localize(end_date):
            user.premium_start_date = None
            user.premium_end_date = None
            user.premium = False
            session.commit()
            return -1
        else:
            return 1
    else:
        return -1

def check_admin(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    if user.admin == True:
        return 1
    else:
        return -1

def get_all_users():
    session = Session()
    users = session.query(User).all()
    return users

def add_blocked(count):
    session = Session()
    number = session.query(BlockedUser).first()
    number.block_count = count
    session.commit()

def get_premium(tg_id, premium_start_date, premium_end_date):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    user.premium_start_date = premium_start_date
    user.premium_end_date = premium_end_date
    user.premium = True
    session.commit()

def get_admin(tg_id):
    session = Session()
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()
    user.admin = True
    session.commit()

def stat():
    session = Session()
    users = session.query(User).count()
    blocked = session.query(BlockedUser).count()
    return [users, blocked]