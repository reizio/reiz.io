from reiz.config import config
from reiz.web.api import app

if __name__ == "__main__":
    app.run(
        host=config.web.host, port=config.web.port, workers=config.web.workers
    )
