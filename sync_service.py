from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, json
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()
scheduler = BackgroundScheduler()

@auth.verify_password
def verify_password(username, password):
    return username
@app.route('/')
@auth.login_required
def index():
    print("connected")
    return "Hello, {}!".format(auth.current_user())


@app.route('/health')
def health():
    return {"status": "ok", "current_time": datetime.now().isoformat()}



def job():
    print("Scheduled job executed")

if __name__ == '__main__':
    scheduler.add_job(job, 'interval', seconds=60)
    scheduler.start()
    app.run()
    scheduler.shutdown()