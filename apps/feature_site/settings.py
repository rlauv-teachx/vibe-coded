import os

APP_FOLDER = os.path.dirname(__file__)
UPLOADS_FOLDER = os.path.join(APP_FOLDER, 'uploads')

if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)

