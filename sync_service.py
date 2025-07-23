import logging
import os
from datetime import datetime
from json import JSONDecodeError
from os import path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, json, jsonify, Response, request, render_template_string
from flask_httpauth import HTTPBasicAuth

from creatio.creatio_api import get_api_connector
from creatio_users import create_user_from_ldap_and_contacts, get_licenses_count_info, get_licenses_info
from ldap_integration import sync_ldap_records_and_contacts, sync_ldap_records

logging.basicConfig(level=logging.INFO, filename="py_log.log",filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")


def setup_logger(name, level=logging.INFO, log_file_path='logging.log',format='%(asctime)s %(levelname)s %(message)s'):
    handler = logging.FileHandler(log_file_path)
    handler.setLevel(level)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger_file_handler = logging.FileHandler(log_file_path)
    logger_file_handler.setLevel(logging.DEBUG)
    logger_file_handler.setFormatter(logging.Formatter(format))
    logger.addHandler(logger_file_handler)
    return logger

logs_path = '/opt/logs/'


user_info_logger = setup_logger('UserInfo', log_file_path=os.path.join(logs_path, 'UserInfo.log'))
ldap_info_logger = setup_logger('LDAPInfo', log_file_path=os.path.join(logs_path, 'LdapInfo.log'))
success_user_logger = setup_logger("User", log_file_path=os.path.join(logs_path, 'sync.log'))
success_ldap_logger = setup_logger("Ldap", log_file_path=os.path.join(logs_path, 'operation.log'))
general_logger = setup_logger("GENERAL", log_file_path=os.path.join(logs_path, 'general.log'))


app = Flask(__name__)
auth = HTTPBasicAuth()
scheduler = BackgroundScheduler()

global creatio_api

auth_data = {
    'web_username': 'admin',
    'web_password': 'admin',
}




@app.route('/license_count', methods=['GET'])
@auth.login_required
def license_count():
    try:
        return  get_licenses_count_info(config)
    except Exception as ex:
        return jsonify({"error": str(ex)})

@app.route('/licenses', methods=['GET'])
@auth.login_required
def license_info():
    try:
        return  get_licenses_info(config)
    except Exception as ex:
        return jsonify({"error": str(ex)})


@auth.verify_password
def verify_password(username, password):
    if config.get('debug_mode', False):
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


@app.route('/ldap_sync_log')
@auth.login_required
def ldap_sync_log():
    return read_file_human(logs_path+'operation.log')


@app.route('/logs')
@auth.login_required
def general_logs():
    return read_file_human(logs_path+'general.log')

@app.route('/user_operations_info')
@auth.login_required
def user_import_info():
    return read_file_human(logs_path+'UserInfo.log')


@app.route('/ldap_operations_info')
@auth.login_required
def ldap_import_info():
    return read_file_human(logs_path+'LdapInfo.log')


@app.route('/contact_sync_log')
@auth.login_required
def contact_sync_log():
    return read_file_human(logs_path+'sync.log')


@app.route('/ldaps')
@auth.login_required
def ldaps():
    return read_json((os.path.join(logs_path,'ldap_entries.json')))


@app.route('/users')
@auth.login_required
def users():
    return read_json(os.path.join(logs_path,'creatio_users.json'))


@app.route('/get_last_ldaps')
@auth.login_required
def ldaps_templated():
    return read_json_human((os.path.join(logs_path,'ldap_entries.json')))


@app.route('/get_last_users')
@auth.login_required
def users_templated():
    return read_json_human(os.path.join(logs_path,'creatio_users.json'))

@app.route('/get_ldap_entries')
@auth.login_required
def get_ldap_entries():
    if creatio_api.login():
        return jsonify(creatio_api.get_ldap_info())
    else:
        return {"ERROR": 'login creatio api failed!'}

@app.route('/config')
@auth.login_required
def get_config():
    return jsonify(json.dumps(config))


@app.route('/contacts')
@auth.login_required
def get_contacts():
    filter_param = request.args.get('filter')
    return jsonify(get_contacts(config, filter_param))


@app.route('/get_creatio_users')
@auth.login_required
def get_creatio_users():
    if creatio_api.login():
        return jsonify(creatio_api.get_short_users())
    else:
        return {"ERROR": 'login creatio api failed!'}


@app.route('/health')
def health():
    current_time =datetime.now().timestamp()
    users_sync = (current_time - last_users_sync) < update_interval
    ldap_sync = (current_time - last_ldap_sync) < update_interval
    rights_sync = (current_time - last_access_rights_check) < update_interval
    heartbeat_status = (current_time - heartbeat) < 60
    status = users_sync and ldap_sync
    return jsonify({"status": "ok" if status else "failed",
            "sync_ldap_entries":"ok" if ldap_sync else "failed",
            "sync_users": "ok" if users_sync else "failed",
            "rights_sync": "ok" if rights_sync else "failed",
            "heartbeat_status": "ok" if heartbeat_status else "failed",
            "current_time": datetime.now().astimezone().strftime("%d-%m-%Y %H:%M:%S"),
            "last_user_sync:": datetime.fromtimestamp(last_users_sync).astimezone().strftime("%d-%m-%Y %H:%M:%S"),
            "last_ldap_sync:": datetime.fromtimestamp(last_ldap_sync).astimezone().strftime("%d-%m-%Y %H:%M:%S"),
            "last_user_access_rights_sync": datetime.fromtimestamp(last_access_rights_check).astimezone().strftime("%d-%m-%Y %H:%M:%S"),
            "sync_user_stat":{
                "created_users": new_user_record,
                "ldap_entries_in_db": ldap_records_count,
                "contacts_records_in_db": contacts_records_count,
                "full_created_record": full_created_record,
                "user_records_in_db": user_records_count,
            },
            "rights_sync_stat":{
                "updated_users": new_user_record,
            },
                    "ldap_sync_stat":{
                        "ldap_record_created":ldap_record_created, 
                        "ldap_record_updated":ldap_record_updated, 
                        "no_contact_ldap_records":ldap_record_skiped, 
                        "total_ad_user_processed":ad_users_processed
                    }
                    })

@app.route('/stat')
def health_human():
    # Виклик внутрішнього ендпоінту
    with app.test_client() as client:
        response = client.get('/health')
        data = response.get_json()

    # HTML-шаблон
    html_template = """
    <h1>📊 Стан системи</h1>
    <p><strong>Загальний статус:</strong> <span style="color: {{ 'green' if data['status'] == 'ok' else 'red' }}">{{ data['status'].upper() }}</span></p>
    <p><strong>Час сервера:</strong> {{ data['current_time'] }}</p>

    <h2>🟢 Перевірки синхронізації</h2>
    <ul>
        <li><strong>LDAP Sync:</strong> {{ data['sync_ldap_entries'] }} (останній: {{ data['last_ldap_sync:'] }})</li>
        <li><strong>Users Sync:</strong> {{ data['sync_users'] }} (останній: {{ data['last_user_sync:'] }})</li>
        <li><strong>Access Rights Sync:</strong> {{ data['rights_sync'] }} (останній: {{ data['last_user_access_rights_sync'] }})</li>
        <li><strong>Heartbeat:</strong> {{ data['heartbeat_status'] }}</li>
    </ul>

    <h2>👤 Статистика користувачів</h2>
    <ul>
        <li>Створено користувачів: {{ data['sync_user_stat']['created_users'] }}</li>
        <li>Користувачів у БД: {{ data['sync_user_stat']['user_records_in_db'] }}</li>
        <li>Контактів у БД: {{ data['sync_user_stat']['contacts_records_in_db'] }}</li>
        <li>LDAP-записів у БД: {{ data['sync_user_stat']['ldap_entries_in_db'] }}</li>
        <li>Повністю створено записів: {{ data['sync_user_stat']['full_created_record'] }}</li>
    </ul>

    <h2>🔐 Синхронізація прав доступу</h2>
    <ul>
        <li>Оновлено користувачів: {{ data['rights_sync_stat']['updated_users'] }}</li>
    </ul>

    <h2>🧬 LDAP Статистика</h2>
    <ul>
        <li>Створено LDAP записів: {{ data['ldap_sync_stat']['ldap_record_created'] }}</li>
        <li>Оновлено LDAP записів: {{ data['ldap_sync_stat']['ldap_record_updated'] }}</li>
        <li>Пропущено (немає контактів): {{ data['ldap_sync_stat']['no_contact_ldap_records'] }}</li>
        <li>Усього AD користувачів опрацьовано: {{ data['ldap_sync_stat']['total_ad_user_processed'] }}</li>
    </ul>
    """

    return render_template_string(html_template, data=data)



@app.route('/ldap_entries')
@auth.login_required
def get_ldap_entries_human():
    if not creatio_api.login():
        return "Login to Creatio API failed!", 500

    entries = creatio_api.get_ldap_info()

    html_template = """
    <h1>LDAP Entries</h1>
    <table border="1" cellpadding="5" cellspacing="0">
        <thead>
            <tr>
                <th>Name</th>
                <th>Full Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Company</th>
                <th>Job Title</th>
                <th>Active</th>
                <th>Modified On</th>
            </tr>
        </thead>
        <tbody>
        {% for key, entry in entries.items() %}
            <tr>
                <td>{{ entry.get("Name", "") }}</td>
                <td>{{ entry.get("FullName", "") }}</td>
                <td>{{ entry.get("Email", "") }}</td>
                <td>{{ entry.get("Phone", "") }}</td>
                <td>{{ entry.get("Company", "") }}</td>
                <td>{{ entry.get("JobTitle", "") }}</td>
                <td>{{ "✅" if entry.get("IsActive") else "❌" }}</td>
                <td>{{ entry.get("ModifiedOn", "") }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
    """

    return render_template_string(html_template, entries=entries)



def heartbeat_job():
    global heartbeat
    heartbeat = datetime.now().timestamp()


def read_file(file_name):
    if path.exists(file_name):
        with open(file_name, 'r') as f:
            return Response(f"FILE: {file_name} CONTAIN:\n{f.read()}", mimetype='text/plain; charset=utf-8')
    else:
        return Response(f"{file_name} does not exist!", mimetype='text/plain; charset=utf-8')

def read_json(file_name):
    if path.exists(file_name):
        
        with open(file_name, 'r') as f:
            content = json.load(f)
            pretty = json.dumps(content, indent=2, ensure_ascii=False)  # для красивого виводу
            return Response(pretty, mimetype="application/json; charset=utf-8")
    else:
        return Response(f"{file_name} does not exist!", mimetype='text/plain; charset=utf-8')

def read_file_human(file_name):
    if path.exists(file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            content = f.read()

        html_template = """
        <h1>File: {{ file_name }}</h1>
        <pre style="background:#f5f5f5;padding:10px;border:1px solid #ccc;">{{ content }}</pre>
        """
        return render_template_string(html_template, file_name=file_name, content=content)
    else:
        return f"<h1>❌ File '{file_name}' does not exist!</h1>", 404

def read_json_human(file_name):
    if not path.exists(file_name):
        return f"<h1>❌ File '{file_name}' does not exist!</h1>", 404

    with open(file_name, 'r', encoding='utf-8') as f:
        try:
            content = json.load(f)
        except JSONDecodeError as e:
            return f"<h1>❌ JSON decode error:</h1><pre>{str(e)}</pre>", 400

    def render_table(data):
        if isinstance(data, dict):
            rows = "".join(
                f"<tr><th>{key}</th><td>{render_table(value)}</td></tr>"
                for key, value in data.items()
            )
            return f"<table border='1' cellpadding='5' cellspacing='0'>{rows}</table>"
        elif isinstance(data, list):
            if all(isinstance(i, dict) for i in data):
                headers = sorted({k for d in data for k in d})
                rows = [
                    "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
                ]
                for item in data:
                    row = "".join(f"<td>{item.get(h, '')}</td>" for h in headers)
                    rows.append(f"<tr>{row}</tr>")
                return "<table border='1' cellpadding='5' cellspacing='0'>" + "".join(rows) + "</table>"
            else:
                return "<ul>" + "".join(f"<li>{render_table(i)}</li>" for i in data) + "</ul>"
        else:
            return str(data)

    html_content = render_table(content)
    html_template = """
    <h1>JSON File: {{ file_name }}</h1>
    {{ table_content|safe }}
    """
    return render_template_string(html_template, file_name=file_name, table_content=html_content)



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
    general_logger.info("READ SECRETS")
    for secret, update_secret in update_secrets.items():
        if update_secrets:
            general_logger.info(f"check path {base_path + secret}")
            if path.exists(base_path + secret):
                with open(base_path + secret, 'r') as f:
                    value = f.read()
                general_logger.info(f"read secret: {value}")
            else:
                value = os.environ.get(secret, None)
                general_logger.info(f"secret file not found. read env: {value}")
        else:
            update_secrets = secret
        general_logger.info(f"update config")
        if value is not None:
            items = update_secret.split('.')
            update_path = items[:-1]
            update_key = items[-1]
            part_config_for_update = config
            for update_element in update_path:
                part_config_for_update = part_config_for_update.get(update_element, None)
                if part_config_for_update is None:
                    break
            if part_config_for_update is not None:
                if update_key in part_config_for_update:
                    part_config_for_update[update_key] = value
                else:
                    general_logger.warning(f"NO CONFIG KEY {update_key}")
            else:
                general_logger.warning(f"incorrect {update_secret} path")
        else:
            general_logger.warning(f"NO VALUE FOR: {secret}:{update_secret}")


update_interval = 24 * 60 * 60
last_ldap_sync = 0
last_access_rights_check = 0
last_users_sync = 0
heartbeat = 0
new_user_record=0
user_records_count =0 
ldap_records_count=0
contacts_records_count=0 
full_created_record =0
user_rights_changed = 0

ldap_record_created =0
ldap_record_updated =0
ldap_record_skiped =0
ad_users_processed =0

def users_sync_function(config):
    global last_users_sync, new_user_record, user_records_count, ldap_records_count, contacts_records_count, full_created_record
    try:
        general_logger.info(f"user sync started")
        result = create_user_from_ldap_and_contacts(config, user_info_logger, success_user_logger, logs_path)
        (new_user_record, user_records_count, ldap_records_count, contacts_records_count, full_created_record) = result
        last_users_sync = datetime.now().timestamp()
        general_logger.info(f"user sync finished")
    except Exception as e:
        user_info_logger.error(e)





def ldap_sync_function(config):
    global last_ldap_sync, ldap_record_created, ldap_record_updated, ldap_record_skiped, ad_users_processed    
    try:
        general_logger.info(f"ldap sync started")
        ldap_record_created, ldap_record_updated, ldap_record_skiped, ad_users_processed = sync_ldap_records(config, ldap_info_logger, success_ldap_logger, logs_path)
        last_ldap_sync = datetime.now().timestamp()
        general_logger.info(f"ldap sync finished")
    except Exception as e:
        ldap_info_logger.error(e)


def user_access_right_check(config):
    global last_access_rights_check, user_rights_changed
    try:
        general_logger.info(f"update user access rights started")
        user_rights_changed = sync_ldap_records(config, ldap_info_logger, success_ldap_logger, logs_path)
        last_access_rights_check = datetime.now().timestamp()
        general_logger.info(f"update user access rights finished")
    except Exception as e:
        ldap_info_logger.error(e)


def init_app():
    global config, creatio_api, update_interval
    
    config_path = '/opt/config/import.config'
    print("START SERVICE")
    print(f'check config path: {config_path}')
    if os.path.exists(config_path):
        print(f"Use config path: {config_path}")
        with open(config_path) as f:
            config = json.load(f)
    else:
        config_path = 'import.config'
        print(f'check config path: {config_path}')
        if os.path.exists(config_path):
            print(f"Use config path: {config_path}")
            with open(config_path) as f:
                config = json.load(f)
        else:
            print("no config file! use empty config")
            config = {}
    update_config_secrets(config)
    update_config_secrets(auth_data, update_secrets={
        'web_username': 'admin',
        'web_password': 'admin',
    })

    general_logger.debug("config: " + str(config))
    general_logger.debug("auth_data: " + str(auth_data))

    if config.get('debug_mode', False):
        general_logger.setLevel(logging.DEBUG)
        success_ldap_logger.setLevel(logging.DEBUG)
        success_user_logger.setLevel(logging.DEBUG)
        #logs_path = ''
    if 'api' in config:
        creatio_api = get_api_connector(config['api'])
    update_interval = config.get('update_interval', 60*60*24)
    general_logger.info("update interval: " + str(update_interval))
    general_logger.info("setup process jobs")
    scheduler.add_job(heartbeat_job, 'interval', seconds=60)
    scheduler.add_job(ldap_sync_function, 'interval',
                      next_run_time=datetime.now(),
                      seconds=update_interval, args=[config])    
    scheduler.add_job(users_sync_function, 'interval',
                      next_run_time=datetime.now(),
                      seconds=user_access_right_check, args=[config])    
    scheduler.add_job(users_sync_function, 'interval',
                      next_run_time=datetime.now(),
                      seconds=update_interval, args=[config])
    scheduler.start()
    general_logger.info("scheduler started")


if __name__ == '__main__':
    print("Main app running")
    with app.app_context():
        init_app()
    app.run(host="0.0.0.0", port=5000)
    scheduler.shutdown()
else:
    init_app()
