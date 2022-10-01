import os
from src import ShowData
from flask import Flask, current_app
from flask_apscheduler import APScheduler


class Config(object):
    JOBS = [
        {
            'id': 'job1',
            'func': "main:updater",
            'trigger': 'interval',
            'hours': 23
        }
    ]
    SCHEDULER_API_ENABLED = True


def updater():
    show_data = ShowData()
    show_data.update_data()


app = Flask(__name__)
app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


@app.route('/')
def index():
    # check if html file doesn't exist get it
    if not os.path.isfile('static/index.html'):
        first_run = ShowData()
        first_run.update_data()
    return current_app.send_static_file('index.html')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
