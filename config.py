import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-key')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'mysql+pymysql://root:@127.0.0.1:3306/camera_detection_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434/api/chat')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma3:1b')
