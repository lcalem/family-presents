import os

from routes import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', threaded=False, port=80, processes=50)
