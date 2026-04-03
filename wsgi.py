"""
WSGI entry point for production deployment.
Use with Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""

from app import app

if __name__ == "__main__":
    pass
