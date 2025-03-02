from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker
import subprocess, json, time, random
import win32api, win32gui, win32con
from typing import List, Dict, Set
from datetime import datetime
import uiautomation as auto
from database import db
import hashlib, re

Session = sessionmaker(bind=db.engine)
session = Session()

glc={
    'id':None,
    'wxid':None,
    'nick_name':None,
    'contact':None,
    'postDuplicate':False
}

import wechat.utils.ut as utils
import wechat.chat.ct as chat
import wechat.contact.ctt as contact
import wechat.post.pt as post
import wechat.search.sc as search
import wechat.init.user as init