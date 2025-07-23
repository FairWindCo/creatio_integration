# pyinstaller --noconfirm --onefile --console C:\Users\User\PycharmProjects\ldap\ldap_integration.py
import json
import logging
from datetime import datetime

from creatio.creatio_api import get_api_connector
from creatio.creatio_objects import ContactHolders
from creatio.db import get_db_connection
from ldap_access.ldap_data_access import get_ad_domain_users, print_users


def convert_ldap_to_ldap_entry_json(name_prefix, user: dict) -> dict:
    dn = user["DN"].replace("'", "''")
    title = user["title"].replace("'", "''")
    # sql = (
    #     f'INSERT INTO  dbo.LDAPElement(name, FullName, Phone, Email, JobTitle, Company, LDAPEntryId, LDAPEntryDN, Type, ProcessListeners, CreatedById, ModifiedById,IsActive) '
    #     f" VALUES('{user["sAMAccountName"]}','{name_prefix}{user["cn"]}','{user["telephoneNumber"]}','{user["mail"]}',"
    #     f"'{title}','{user["company"]}','{user["ldap_entry_id"]}','{dn}',"
    #     f"4, 0,'{creator_id}','{creator_id}',0)")

    return {
        'Name': user["sAMAccountName"],
        'FullName': f'{name_prefix}{user["cn"]}',
        'isActive': True,
        'Description': '',
        'LDAPEntryId': user["ldap_entry_id"],
        'LDAPEntryDN': dn,
        'Company': user["company"],
        'Email': user["mail"],
        'Phone': user["telephoneNumber"],
        'JobTitle': title,
        'Type': 4
    }


def save_data_to_json_file(data, file_name):
    with open(file_name, "w") as file:
        json.dump(data, file)


# def print_log(log_entries: list, record: str):
#     print(record)
#     log_entries.append(f"{datetime.now().strftime('%d.%m.%y %H:%M:%S')}: {record}")


def sync_ldap_records(config, logger, success_logger,):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", True)
    logs_record = []
    logger.debug("Syncing LDAP records from LDAP...")
    api = get_api_connector(config['api'])
    api.debug = debug_mode
    if api.login():
        logger.debug(logs_record, f"Login successful ==={datetime.now().strftime('%d%m%y %H%M%S')}===")
        ldap_entries = api.get_ldap_info()
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                logger.debug(logs_record, f"Domain {domain['name']} ignored ==={domain.get('ignore_domain', False)}")
                continue
            logger.debug(f"process AD domain: {domain['name']}")
            users = get_ad_domain_users(domain, global_user_data)
            if debug_mode:
                print_users(users)
            domain_preffix = domain.get("name", "")
            if domain_preffix and not domain_preffix.endswith("\\"):
                domain_preffix = domain_preffix + "\\"
            for user in users:
                ldap_record = convert_ldap_to_ldap_entry_json(domain_preffix, user)
                account_name = ldap_record['Name']
                if account_name in ldap_entries:
                    if overwrite_mode:
                        api.update_ldap_entry(ldap_entries[account_name]['Id'], ldap_record)
                        success_logger.info(f"AD user: {account_name} - updated")
                    else:
                        logger.debug(f"AD user: {account_name} - skipped")
                else:
                    new_record = api.create_ldap_entry(ldap_record)
                    ldap_entries[account_name] = new_record
                    success_logger.info(f"AD user: {account_name} - created")
    else:
        logger.error(logs_record, "ERROR: Login failed")


def sync_ldap_records_and_contacts(config, logger, success_logger, log_path=''):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", False)
    logger.debug("START LDAP AND CONTACT SYNC PROCESS")
    api = get_api_connector(config['api'])
    api.debug = debug_mode
    if api.login():
        logger.debug("Login successful")
        ldap_entries = api.get_ldap_info()
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                continue
            logger.debug(f"process AD domain: {domain['name']}")
            users = get_ad_domain_users(domain, global_user_data)
            if debug_mode:
                print_users(users)
            domain_preffix = domain.get("name", "")
            if domain_preffix and not domain_preffix.endswith("\\"):
                domain_preffix = domain_preffix + "\\"
            for user in users:
                ldap_record = convert_ldap_to_ldap_entry_json(domain_preffix, user)
                account_name = ldap_record['Name']

                logger.debug( f"process AD user: {account_name}")

                if account_name in ldap_entries:
                    if overwrite_mode:
                        res = api.update_ldap_entry(ldap_entries[account_name]['Id'], ldap_record)
                        if res:
                            current_ldap_entry_id = ldap_entries[account_name]['Id']
                            success_logger.info(f"LDAP record: {account_name} - updated {current_ldap_entry_id}")
                        else:
                            success_logger.info(f"LDAP record: {account_name} - UPDATE FAILED {current_ldap_entry_id}")
                    else:
                        logger.debug(f"LDAP record: {account_name} - skipped")
                else:
                    new_record = api.create_ldap_entry(ldap_record)
                    ldap_entries[account_name] = new_record
                    current_ldap_entry_id = new_record['Id']
                    success_logger.info(f"LDAP record: {account_name} - created as {current_ldap_entry_id}")


        save_data_to_json_file(ldap_entries, log_path+'ldap_entries.json')
    else:
        logger.error("ERROR: Login failed")


def sync_ldap_records(config, logger, success_logger, log_path=''):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", False)
    logger.debug("START LDAP SYNC PROCESS")
    api = get_api_connector(config['api'])
    api.debug = debug_mode
    ad_users_processed = 0
    ldap_record_created = 0
    ldap_record_updated = 0
    ldap_record_skiped = 0
    if api.login():
        logger.debug("Login successful")
        api_contacts = api.get_contacts_set_id()        
        ldap_entries = api.get_ldap_info()
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                continue
            logger.debug(f"process AD domain: {domain['name']}")
            users = get_ad_domain_users(domain, global_user_data)
            if debug_mode:
                print_users(users)
            domain_preffix = domain.get("name", "")
            if domain_preffix and not domain_preffix.endswith("\\"):
                domain_preffix = domain_preffix + "\\"
            for user in users:
                ad_users_processed += 1
                ldap_record = convert_ldap_to_ldap_entry_json(domain_preffix, user)
                account_name = ldap_record['Name']
                full_domain_name = domain_preffix + account_name
                print(full_domain_name, account_name)
                logger.debug( f"process AD user: {account_name}")
                
                if full_domain_name in api_contacts:                    
                    if account_name in ldap_entries:
                        if overwrite_mode:
                            res = api.update_ldap_entry(ldap_entries[account_name]['Id'], ldap_record)
                            if res:
                                current_ldap_entry_id = ldap_entries[account_name]['Id']
                                success_logger.info(f"LDAP record: {account_name} - updated {current_ldap_entry_id}")
                                ldap_record_updated += 1
                            else:
                                success_logger.info(f"LDAP record: {account_name} - UPDATE FAILED {current_ldap_entry_id}")
                        else:
                            logger.debug(f"LDAP record: {account_name} - skipped")
                    else:
                        new_record = api.create_ldap_entry(ldap_record)
                        ldap_record_created += 1
                        ldap_entries[account_name] = new_record
                        current_ldap_entry_id = new_record['Id']
                        success_logger.info(f"LDAP record: {account_name} - created as {current_ldap_entry_id}")
                else:
                    logger.debug(f"LDAP record: {full_domain_name} - skipped no contact for {account_name}")
                    ldap_record_skiped += 1

        save_data_to_json_file(ldap_entries, log_path+'ldap_entries.json')
    else:
        logger.error("ERROR: Login failed")
    return ldap_record_created, ldap_record_updated, ldap_record_skiped, ad_users_processed



if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    logger = logging.getLogger()
    #sync_ldap_records_and_contacts(config, logger, logger)
    sync_ldap_records(config, logger, logger)
