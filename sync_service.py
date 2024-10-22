import os
from datetime import datetime
from os import path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, json
from flask_httpauth import HTTPBasicAuth

from creatio.creatio_api import get_api_connector
from creatio_users import create_user_from_ldap_and_contacts
from ldap_integration import sync_ldap_records_and_contacts

app = Flask(__name__)
auth = HTTPBasicAuth()
scheduler = BackgroundScheduler()

global creatio_api

auth_data = {
    'web_username': 'admin',
    'web_password': 'admin',
}

if __debug__:
    logs_path = ''
else:
    logs_path = '/opt/logs/'

@auth.verify_password
def verify_password(username, password):
    if __debug__:
        return username
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
    return read_file(logs_path+'operation.log')


@app.route('/combine_logs')
@auth.login_required
def combine_logs():
    return read_file(logs_path+'sync.log')


@app.route('/ldaps')
@auth.login_required
def ldaps():
    return read_file(logs_path+'ldap_entries.json')


@app.route('/users')
@auth.login_required
def users():
    return read_file(logs_path+'creatio_users.json')


@app.route('/get_ldap_entries')
@auth.login_required
def get_ldap_entries():
    global creatio_api
    if creatio_api.login():
        return creatio_api.get_ldap_info()
    else:
        return {"ERROR": 'login creatio api failed!'}

@app.route('/get_creatio_users')
@auth.login_required
def get_creatio_users():
    global creatio_api
    if creatio_api.login():
        return creatio_api.get_short_users()
    else:
        return {"ERROR": 'login creatio api failed!'}


@app.route('/health')
def health():
    global last_users_sync
    global last_ldap_sync
    global heartbeat
    current_time =datetime.now().timestamp()
    users_sync = (current_time - last_users_sync) < update_interval
    ldap_sync = (current_time - last_ldap_sync) < update_interval
    heartbeat_status = (current_time - heartbeat) < 60
    status = users_sync and ldap_sync
    return {"status": "ok" if status else "failed",
            "sync_ldap_entries":"ok" if ldap_sync else "failed",
            "sync_users": "ok" if users_sync else "failed",
            "heartbeat_status": "ok" if heartbeat_status else "failed",
            "current_time": datetime.now().isoformat()}


def heartbeat_job():
    global heartbeat
    heartbeat = datetime.now().timestamp()


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


update_interval = 24 * 60 * 60
last_ldap_sync = 0
last_users_sync = 0
heartbeat = 0

def users_sync_function(config):
    global last_users_sync
    last_users_sync = datetime.now().timestamp()
    create_user_from_ldap_and_contacts(config, logs_path)



def ldap_sync_function(config):
    global last_ldap_sync
    last_ldap_sync = datetime.now().timestamp()
    sync_ldap_records_and_contacts(config, logs_path)


with app.app_context():
    global creatio_api
    global config

    if __debug__:
        config_path = 'import.config'
    else:
        config_path = '/opt/config/import.config'
    print(f"Use config path: {config_path}")
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
    if config.get('debug_mode', False):
        print(f"Loaded config: {config}")
    if 'api' in config:
        creatio_api = get_api_connector(config['api'])
    update_interval = config.get('update_interval', 60*60*24)
    scheduler.add_job(heartbeat_job, 'interval', seconds=60)
    scheduler.add_job(ldap_sync_function, 'interval', seconds=update_interval, args=[config])
    scheduler.add_job(users_sync_function, 'interval', seconds=update_interval, args=[config])
    scheduler.start()


if __name__ == '__main__':
    app.run()
    scheduler.shutdown()
