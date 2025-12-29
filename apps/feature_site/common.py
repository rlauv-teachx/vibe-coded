from py4web import Session, Cache, Translator, DAL, Field
from py4web.utils.url_signer import URLSigner
from py4web.utils.dbstore import DBStore
from .settings import APP_FOLDER
import os

# Database
DB_FOLDER = os.path.join(APP_FOLDER, 'databases')
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

db = DAL('sqlite://storage.db', folder=DB_FOLDER) 

# Session
session = Session(secret='my_secret_key', storage=DBStore(db))

# Cache
cache = Cache(size=1000)

# URL Signer
url_signer = URLSigner(session)

