import json

from creatio.creatio_api import get_api_connector
from creatio.db import get_db_connection, get_contact_id
from creatio.user_creation import combine_users_records

if __name__ == '__main__':
    print("test")
    with open('import.config') as f:
        config = json.load(f)
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    connect = get_db_connection(config.get("database", {
        "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
    cursor = connect.cursor()
    domains = config.get("domains", [])
    creator_name = config.get("creator_name", "Supervisor")
    user_id = get_contact_id(cursor, creator_name)

    overwrite_mode = config.get("overwrite_mode", True)

    api = get_api_connector(config['api'])
    api.debug = debug_mode

    if user_id:
        if api.login():
            if debug_mode:
                print("Login successful")
            combine_users_records(cursor, api, user_id, debug=debug_mode)
    else:
        print(f'no "{creator_name}" - user found')
