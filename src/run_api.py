import os

from routes import app

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(host='0.0.0.0', threaded=False, port=5555, processes=50)
