import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG      = os.environ.get('DEBUG', 'False').lower() == 'true'
