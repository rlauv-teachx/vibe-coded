import os

APP_FOLDER = os.path.dirname(__file__)
UPLOADS_FOLDER = os.path.join(APP_FOLDER, 'uploads')
T_FOLDER = os.path.join(APP_FOLDER, 'translations')

if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)

if not os.path.exists(T_FOLDER):
    os.makedirs(T_FOLDER)

