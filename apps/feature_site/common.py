from py4web import Session, Cache, Translator, DAL, Field
from py4web.utils.url_signer import URLSigner
from .settings import APP_FOLDER
import os

# Database (optional, using sqlite in memory or file for session if needed)
# For this task, we don't strictly need a DB, but py4web session usually wants one or mem.
db = DAL('sqlite:memory') 

# Session
session = Session(secret='my_secret_key')

# Cache
cache = Cache(size=1000)

# Translator
T = Translator(os.path.join(APP_FOLDER, 'translations'))

# URL Signer
url_signer = URLSigner(session)

