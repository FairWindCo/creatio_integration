import datetime
import hashlib
import re
from binascii import b2a_hex

import ldap


def filter_account(account_name):
    account_name = account_name.lower()
    # if account_name == b'dev_creatio':
    #     return False
    if account_name == b'administrator':
        return True
    if account_name.endswith(b'$'):
        return True
    if account_name.startswith(b'cwrk_'):
        return True
    if account_name.startswith(b'dev_'):
        return True
    if account_name.startswith(b'vakant'):
        return True
    if account_name.find(b'temp') >= 0:
        return True
    if account_name.find(b'test') >= 0:
        return True
    if account_name.find(b'sheduler') >= 0:
        return True
    if account_name.find(b'scheduler') >= 0:
        return True
    if account_name.find(b'account') >= 0:
        return True
    if account_name.find(b'audit') >= 0:
        return True
    if account_name.find(b'auth') >= 0:
        return True
    if re.match(b'.*[0-9]+.*', account_name):
        return True
    if account_name.find(b'user') >= 0:
        return True

    if account_name.find(b'agent') >= 0:
        return True
    return False


def sid_to_str(sid):
    try:
        # Python 3
        if str is not bytes:
            # revision
            revision = int(sid[0])
            # count of sub authorities
            sub_authorities = int(sid[1])
            # big endian
            identifier_authority = int.from_bytes(sid[2:8], byteorder='big')
            # If true then it is represented in hex
            if identifier_authority >= 2 ** 32:
                identifier_authority = hex(identifier_authority)

            # loop over the count of small endians
            sub_authority = '-' + '-'.join(
                [str(int.from_bytes(sid[8 + (i * 4): 12 + (i * 4)], byteorder='little')) for i in
                 range(sub_authorities)])
        # Python 2
        else:
            revision = int(b2a_hex(sid[0]))
            sub_authorities = int(b2a_hex(sid[1]))
            identifier_authority = int(b2a_hex(sid[2:8]), 16)
            if identifier_authority >= 2 ** 32:
                identifier_authority = hex(identifier_authority)

            sub_authority = '-' + '-'.join(
                [str(int(b2a_hex(sid[11 + (i * 4): 7 + (i * 4): -1]), 16)) for i in range(sub_authorities)])
        objectSid = 'S-' + str(revision) + '-' + str(identifier_authority) + sub_authority

        return objectSid
    except Exception:
        pass

    return sid


def convert_attribute(user, name):
    value = user[1].get(name, [b''])[0]
    if name.endswith('Sid'):
        # print(b2a_hex(value))
        # print(b2a_hex(hashlib.md5(value).digest()))
        return sid_to_str(value)
    if name == 'modifyTimeStamp':
        if value:
            modify_time = datetime.datetime.strptime(value.decode('utf-8'), '%Y%m%d%H%M%S.0Z')
            return modify_time
        else:
            return None
    if name == 'IsAccountLocked':
        if value == b'true':
            return True
        else:
            return False
    else:
        return value.decode('utf-8')


def get_ldap_entry_id(user):
    value = user[1].get('objectSid', [b''])[0]
    return b2a_hex(hashlib.md5(value).digest()).decode()


def form_user_data(user, attribute_list):
    user_data = {
        name: convert_attribute(user, name) for name in attribute_list
    }
    user_data['DN'] = user[0]
    user_data['ldap_entry_id'] = get_ldap_entry_id(user)
    return user_data


def get_users(ldap_client, base_dn='DC=bs,DC=local,DC=erc', filterexp=None, attrlist=None):
    # filterexp = "(&(objectClass=user)(objectClass=person)(!(objectClass=computer))(!(isDeleted=TRUE)))"
    if filterexp is None:
        filterexp = "(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2))(objectClass=person)(!(objectClass=computer))(!(isDeleted=TRUE))(cn=*))"
    if attrlist is None:
        attrlist = ["sAMAccountName", "mail", "objectSid", "cn", "telephoneNumber", "title", "company", "uid",
                    'modifyTimeStamp', "IsAccountLocked"]
    result = ldap_client.search_s(base_dn, ldap.SCOPE_SUBTREE, filterexp, attrlist)
    print(f'found records: {len(result)}')
    user_for_next_processing = []

    for user in result:
        if user[0] is not None:
            account_name = user[1].get('sAMAccountName', ['---'])[0]
            if filter_account(account_name):
                continue
            user_for_next_processing.append(
                form_user_data(user, attrlist)
            )
    return user_for_next_processing


def get_users_from_ldap(login, password, server='ldap://dcbs0201.bs.local.erc',
                        basedn='DC=bs,DC=local,DC=erc', filterexp=None, attrlist=None):
    try:
        if not server.startswith("ldap://"):
            server = "ldap://" + server
        ldap_client = ldap.initialize(server)
        ldap_client.set_option(ldap.OPT_REFERRALS, 0)
        ldap_client.bind_s(login, password, ldap.AUTH_SIMPLE)

        user_for_next_processing = get_users(ldap_client, basedn, filterexp, attrlist)
        ldap_client.unbind_s()
        return user_for_next_processing
    except Exception as e:
        print(e)
        return []


def print_users(users):
    print(f'selected records: {len(users)}')
    for user in users:
        print(user)


def get_ad_domain_users(domain_config, user_data, filter=None):
    server_addr = domain_config['ldap_server']
    dn = domain_config['dn']
    login = domain_config.get('login', user_data.get('login', ''))
    password = domain_config.get('password', user_data.get('password', ''))
    return get_users_from_ldap(login, password, server=server_addr, basedn=dn, filterexp=filter)
