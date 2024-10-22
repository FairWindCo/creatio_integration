# pyinstaller --noconfirm --onefile --console C:\Users\User\PycharmProjects\ldap\ldap_integration.py
import json
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


def print_log(log_entries: list, record: str):
    print(record)
    log_entries.append(f"{datetime.now().strftime('%d.%m.%y %H:%M:%S')}: {record}")


def sync_ldap_records(config, log_path=''):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", True)
    logs_record = []
    api = get_api_connector(config['api'])
    api.debug = debug_mode
    if api.login():
        if debug_mode:
            print_log(logs_record, f"Login successful ==={datetime.now().strftime('%d%m%y %H%M%S')}===")
        ldap_entries = api.get_ldap_info()
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                continue
            print_log(logs_record, f"process AD domain: {domain['name']}")
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
                        print_log(logs_record, f"AD user: {account_name} - updated")
                    else:
                        print_log(logs_record, f"AD user: {account_name} - skipped")
                else:
                    new_record = api.create_ldap_entry(ldap_record)
                    ldap_entries[account_name] = new_record
                    print_log(logs_record, f"AD user: {account_name} - created")
    else:
        print_log(logs_record, "ERROR: Login failed")
    with open(log_path+"operation.log", "w") as file:
        for log_record in logs_record:
            file.write(f"{log_record}\n")


def sync_ldap_records_and_contacts(config, log_path=''):
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", True)
    logs_record = []
    api = get_api_connector(config['api'])
    api.debug = debug_mode
    if api.login():
        if debug_mode:
            print_log(logs_record, "Login successful")
        ldap_entries = api.get_ldap_info()
        api_users = api.get_short_users()
        api_logins = api.get_users_with_domain_login()
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                continue
            print_log(logs_record, f"process AD domain: {domain['name']}")
            users = get_ad_domain_users(domain, global_user_data)
            can_create_contact = domain.get("can_create_contact", False)
            if debug_mode:
                print_users(users)
            domain_preffix = domain.get("name", "")
            if domain_preffix and not domain_preffix.endswith("\\"):
                domain_preffix = domain_preffix + "\\"
            for user in users:
                ldap_record = convert_ldap_to_ldap_entry_json(domain_preffix, user)
                account_name = ldap_record['Name']

                print_log(logs_record, f"process AD user: {account_name}")

                if account_name in ldap_entries and overwrite_mode:
                    api.update_ldap_entry(ldap_entries[account_name]['Id'], ldap_record)
                    current_ldap_entry_id = ldap_entries[account_name]['Id']
                else:
                    new_record = api.create_ldap_entry(ldap_record)
                    ldap_entries[account_name] = new_record
                    current_ldap_entry_id = new_record['Id']
                domain_login = domain_preffix + ldap_record['LDAPEntryDN']
                if domain_login in api_logins or account_name in api_users:
                    print_log(logs_record, f'INFO: User {account_name} already exists')
                else:
                    contact_id = api.find_or_create_contact(user['cn'], domain_preffix, account_name, ldap_record,
                                                             can_create_contact)
                    if contact_id:
                        print_log(logs_record,f'Use ID:{contact_id} for contact: {user["cn"]}')
                    else:
                        print_log(logs_record, f"WARNING: contact {user['cn']} - not found")

        save_data_to_json_file(ldap_entries, log_path+'ldap_entries.json')
        save_data_to_json_file(api_users, log_path+'creatio_users.json')
    else:
        print_log(logs_record, "ERROR: Login failed")
    with open(log_path+"operation.log", "w") as file:
        for log_record in logs_record:
            file.write(f"{log_record}\n")


if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    sync_ldap_records_and_contacts(config)
