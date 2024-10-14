from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
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
    return "Hello, {}!".format(auth.current_user())


with app.app_context():
    scheduler.start()

@app.teardown_appcontext
def stop_scheduler(exception=None):
    scheduler.shutdown()

def job():
    print("Scheduled job executed")

if __name__ == '__main__':
    scheduler.add_job(job, 'interval', seconds=60)
    app.run()