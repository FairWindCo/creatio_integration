import os
from datetime import datetime
from os import path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, json
from flask_httpauth import HTTPBasicAuth

from creatio.creatio_api import get_api_connector

app = Flask(__name__)
auth = HTTPBasicAuth()
scheduler = BackgroundScheduler()

auth_data = {
    'web_username': 'admin',
    'web_password': 'admin',
}


@auth.verify_password
def verify_password(username, password):
    if username == auth_data['web_username'] and password == auth_data['web_password']:
        return username
    else:
        return None


@app.route('/')
@auth.login_required
def index():
    print("connected")
    return "Hello, {}!".format(auth.current_user())


@app.route('/import_logs')
@auth.login_required
def import_logs():
    return read_file('/opt/logs/operation.log')


@app.route('/combine_logs')
@auth.login_required
def combine_logs():
    return read_file('/opt/logs/sync.log')


@app.route('/ldaps')
@auth.login_required
def ldaps():
    return read_file('/opt/logs/ldap_entries.json')


@app.route('/users')
@auth.login_required
def users():
    return read_file('/opt/logs/creatio_users.json')


@app.route('/get_ldap_entries')
@auth.login_required
def get_ldap_entries():
    if creatio_api.login():
        return creatio_api.get_ldap_info()
    else:
        return {"ERROR": 'login creatio api failed!'}

@app.route('/get_creatio_users')
@auth.login_required
def get_creatio_users():
    if creatio_api.login():
        return creatio_api.get_short_users()
    else:
        return {"ERROR": 'login creatio api failed!'}


@app.route('/health')
def health():
    current_time =datetime.now().timestamp()
    users_sync = last_users_sync is not None and (current_time - last_users_sync) < update_interval
    ldap_sync = last_ldap_sync is not None and (current_time - last_ldap_sync) < update_interval
    status = users_sync and ldap_sync
    return {"status": "ok" if status else "failed",
            "sync_ldap_entries":"ok" if ldap_sync else "failed",
            "sync_users": "ok" if users_sync else "failed",
            "current_time": datetime.now().isoformat()}


def job():
    print("Scheduled job executed")


def read_file(file_name):
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            return f"FILE: {file_name} CONTAIN:\n{f.read()}"
    else:
        return f"{file_name} does not exist!"


def update_config_secrets(config: dict, base_path: str = '/opt/secrets/', update_secrets=None):
    if update_secrets is None:
        update_secrets = {
            'db_username': 'database.UID',
            'db_password': 'database.PWD',
            'ldap_username': 'domain_user.login',
            'ldap_password': 'domain_user.password',
            'creatio_username': 'api.userid',
            'creatio_password': 'api.password',
        }
    for secret, update_secret in update_secrets.items():
        if update_secrets:
            if path.exists(base_path + secret):
                with open(base_path + secret, 'r') as f:
                    value = f.read()
            else:
                value = os.environ.get(secret, None)
        else:
            update_secrets = secret
        if value is not None:
            items = update_secret.split('.')
            update_path = items[:-1]
            update_key = items[-1]
            part_config_for_update = config
            for update_element in update_path:
                part_config_for_update = part_config_for_update.get(update_element, None)
                if config is None:
                    break
            if config is None:
                if update_key in part_config_for_update:
                    part_config_for_update[update_key] = value
                else:
                    print(f"NO CONFIG KEY {update_key}")
        else:
            print(f"NO VALUE FOR: {secret}:{update_secret}")


creatio_api = None
update_interval = 24 * 60 * 60
last_ldap_sync = None
last_users_sync = None

with app.app_context():
    config_path = '/opt/config/import.config'
    if os.path.exists(config_path):
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}
    update_config_secrets(config)
    update_config_secrets(auth_data, update_secrets={
        'web_username': '',
        'web_password': '',
    })
    if 'api' in config:
        creatio_api = get_api_connector(config['api'])
    update_interval = config.get('update_interval', 60*60*24)
    scheduler.add_job(job, 'interval', seconds=update_interval)
    scheduler.start()


if __name__ == '__main__':
    app.run()
    scheduler.shutdown()
