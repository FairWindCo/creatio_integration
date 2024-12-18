import json

from creatio.creatio_api import get_api_connector
from creatio.db import get_db_connection, get_contact_id
from creatio.user_creation import combine_users_records, combine_role, insert_user_record_with_log
from ldap_integration import save_data_to_json_file


def create_user_from_ldap_and_contacts(config, logger, succes_logger):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    try:
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        creator_name = config.get("creator_name", "Supervisor")
        default_role = config.get("default_role_name", "All employees")
        user_id = get_contact_id(cursor, creator_name)

        api = get_api_connector(config['api'])
        api.debug = debug_mode

        if user_id:
            if api.login():
                logger.debug("Login successful")
                insert_user_record_with_log(logger, cursor, api, user_id, debug=debug_mode)
                #api.check_user_have_role(role_name=default_role)
                combine_role(cursor, api,creator_id=user_id)
            else:
                logger.error('Creatio API login failed')
        else:
            logger.debug(f'no "{creator_name}" - user found')


if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    save_data_to_json_file(config)
