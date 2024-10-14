# pyinstaller --noconfirm --onefile --console C:\Users\User\PycharmProjects\ldap\ldap_integration.py
import json

from creatio.creatio_api import get_api_connector
from creatio.creatio_objects import ContactHolders
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


if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    overwrite_mode = config.get("overwrite_mode", True)

    api = get_api_connector(config['api'])
    api.debug = debug_mode

    if api.login():
        if debug_mode:
            print("Login successful")
        ldap_entries = api.get_ldap_info()
        api_users = api.get_short_users()

        contacts_holder = ContactHolders(api)
        print(api_users)
        domains = config.get("domains", [])
        for domain in domains:
            if domain.get("ignore_domain", False):
                continue
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
                if account_name in ldap_entries and overwrite_mode:
                    api.update_ldap_entry(ldap_entries[account_name]['Id'], ldap_record)
                    current_ldap_entry_id = ldap_entries[account_name]['Id']
                else:
                    new_record = api.create_ldap_entry(ldap_record)
                    ldap_entries[account_name] = new_record
                    current_ldap_entry_id = new_record['Id']

                if account_name in api_users:
                    print(f'User {account_name} exists')
                else:
                    # contact_id = api.find_or_create_contact(user['cn'], domain_preffix, account_name, ldap_record,
                    #                     #                                         can_create_contact)
                    contact_id = contacts_holder.find_or_create_contact(user['cn'], domain_preffix, account_name, ldap_record,
                                                           can_create_contact)

                    if contact_id:
                        print(f'Use {contact_id} contact')
                        # user = api.create_user(account_name, current_ldap_entry_id, ldap_record, user["cn"])
                        # if user:
                        #     print(f'User {account_name} created {user["Id"]}')
                        # else:
                        #     print(f'Error: user {account_name} creation failed')

    else:
        print("Login failed")
