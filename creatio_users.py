import json
from ssl import create_default_context

from creatio.creatio_api import get_api_connector
from creatio.db import get_db_connection, get_contact_id
from creatio.user_creation import combine_users_records, combine_role, insert_user_record_with_log, \
    insert_user_role_record
from ldap_integration import save_data_to_json_file


def create_user_from_ldap_and_contacts(config, logger, succes_logger, log_path=''):
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
        created_user_id = get_contact_id(cursor, creator_name)

        api = get_api_connector(config['api'])
        api.debug = debug_mode

        if created_user_id:
            if api.login():
                logger.debug("Login successful")
                role = api.get_user_roles_by_name(default_role)
                if role:
                    role_id = role['Id']
                else:
                    logger.error(f'Role {default_role} not found')
                    role_id = None
                ldap_entries = api.get_ldap_info()
                api_users = api.get_short_users()
                api_logins = api.get_users_with_domain_login()
                api_contacts = api.get_contacts_set_id()
                save_data_to_json_file(api_users, log_path + 'creatio_users.json')
                for account_name,ldap_entry in ldap_entries.items():
                    account_name = ldap_entry['Name']
                    domain_preffix = ldap_entry['FullName'].split('\\')[0]
                    domain_login = domain_preffix + '\\' + account_name
                    logger.debug(f"process Domain login: {domain_login}")

                    if domain_login in api_logins or account_name in api_users:
                        logger.debug(f'INFO: User {domain_login} already exists')
                    else:
                        contact_id = api_contacts.get(domain_login, None)
                        if contact_id:
                            userid =insert_user_record_with_log(logger, cursor, account_name, contact_id,
                                                        ldap_entry, created_user_id)
                            if userid:
                                succes_logger.info(f'INFO: User {domain_login} created')
                                if role_id:
                                    if insert_user_role_record(cursor, userid, role_id, created_user_id):
                                        succes_logger.info(f'Add {default_role} to user {domain_login}')
                                    else:
                                        logger.error(f'Role {default_role} not added to User {domain_login}')
                            else:
                                logger.error(f'INFO: User {domain_login} not created')
                        else:
                            logger.warning(f'INFO: Contact for {domain_login} does not exist')
                    #api.check_user_have_role(role_name=default_role)
                #combine_role(cursor, api,creator_id=created_user_id,role_name=default_role)
            else:
                logger.error('Creatio API login failed')
        else:
            logger.debug(f'no "{creator_name}" - user found')


if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    save_data_to_json_file(config)
