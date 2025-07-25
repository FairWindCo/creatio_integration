import json
import logging
from ssl import create_default_context

from creatio.creatio_api import get_api_connector
from creatio.db import get_db_connection, get_contact_id
from creatio.user_creation import combine_users_records, combine_role, insert_user_record_with_log, \
    insert_user_role_record, insert_user_sysrole_record, insert_user_self_role_record, insert_license_record, \
    get_license_id, get_licenses, get_license_count, search_contacts, update_user_activity, need_update
from ldap_integration import save_data_to_json_file


def get_licenses_info(config):
    logger = logging.getLogger()
    try:        
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        return get_licenses(cursor)
    else:
        return []

def get_users(config, search):
    logger = logging.getLogger()
    try:
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        return search_contacts(cursor, search)
    else:
        return []

def get_users_for_update(config, search):
    logger = logging.getLogger()
    try:
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        return need_update(cursor, search)
    else:
        return []


def get_licenses_count_info(config):
    logger = logging.getLogger()
    try:
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        return get_license_count(cursor)
    else:
        return []


def update_user_activity_flag(config):
    logger = logging.getLogger()
    try:
        logger.debug("Connecting to DB...")
        connect = get_db_connection(config.get("database", {
            "SERVER": '127.0.0.1', "DATABASE": "<DB>", "UID": "<UID>", "PWD": "<PWD>", }))
        cursor = connect.cursor()
    except Exception as e:
        cursor = None
        logger.error(f'DB Connection Error: {e}')

    if cursor is not None:
        return update_user_activity(cursor, logger)
    else:
        return -1



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
        #default_role = config.get("default_role_name", "All employees")
        default_role = config.get("default_role_name", "All external users")
        default_lic_package_name = config.get("default_lic_package_name", "studio creatio self-service portal on-site")
        manual_license_apply = config.get("manual_license_apply", True)
        created_user_id = get_contact_id(cursor, creator_name)

        api = get_api_connector(config['api'])
        api.debug = debug_mode
        contacts_records = 0
        ldap_records = 0
        user_records = 0
        new_user_record = 0
        full_created_record = 0
        if created_user_id:
            if api.login():
                logger.debug("Login successful")
                role = api.get_user_roles_by_name(default_role)
                lic_package = api.get_lic_package_by_name(default_lic_package_name)
                if role:
                    role_id = role['Id']
                else:
                    logger.error(f'Role {default_role} not found')
                    role_id = None
                if lic_package:
                    #lic_package_id = api.get_lic_package_by_name(lic_package_name)
                    lic_package_id = lic_package['Id']
                else:
                    lic_package_id = None
                    logger.error(f'Lic package {default_lic_package_name} not found')
                print(f"default role {default_role} is {role_id}")
                print(f"default lic {default_lic_package_name} is {lic_package_id}")
                ldap_entries = api.get_ldap_info()
                api_users = api.get_short_users()
                api_logins = api.get_users_with_domain_login()
                api_contacts = api.get_contacts_set_id()
                contacts_records = len(api_contacts)
                ldap_records = len(api_users)
                user_records = len(api_users)
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
                                                        ldap_entry, created_user_id, parent_role_id=role_id)
                            if userid:
                                new_user_record += 1
                                succes_logger.info(f'INFO: User {domain_login} created')
                                setup_attribute_record = True
                                if role_id:
                                    if insert_user_role_record(cursor, userid, role_id, created_user_id):
                                        succes_logger.info(f'Add {default_role} to user {domain_login}')
                                    else:
                                        logger.error(f'Role {default_role} not added to User {domain_login}')
                                        setup_attribute_record = False
                                    if insert_user_sysrole_record(cursor, userid, role_id, created_user_id):
                                        succes_logger.info(f'Add SYSROLE {default_role} to user {domain_login}')
                                    else:
                                        logger.error(f'SysRole {default_role} not added to User {domain_login}')
                                        setup_attribute_record = False
                                        
                                        
                                    if insert_user_self_role_record(cursor, userid, created_user_id):
                                        succes_logger.info(f'Add SELF ROLE to user {domain_login}')
                                    else:
                                        logger.error(f'SELF Rolenot added to User {domain_login}')
                                        setup_attribute_record = False
                                if lic_package_id and manual_license_apply:
                                    if insert_license_record(cursor, userid, lic_package_id, created_user_id):
                                        succes_logger.info(f'Add License {default_lic_package_name} to user {domain_login}')
                                    else:
                                        succes_logger.info(f'ERROR ADD License {default_lic_package_name} to user {domain_login}')
                                        setup_attribute_record = False
                                if setup_attribute_record:
                                    full_created_record += 1
                            else:
                                logger.error(f'User {domain_login} not created')
                        else:
                            logger.warning(f'Contact for {domain_login} does not exist')
                    #api.check_user_have_role(role_name=default_role)
                #combine_role(cursor, api,creator_id=created_user_id,role_name=default_role)
            else:
                logger.error('Creatio API login failed')
        else:
            logger.debug(f'no "{creator_name}" - user found')
        return (new_user_record, user_records, ldap_records, contacts_records, full_created_record)


if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    logger = logging.getLogger()
    #create_user_from_ldap_and_contacts(config, logger, logger, log_path='')
    print(get_users(config, 'Man'))
    #save_data_to_json_file(config)
