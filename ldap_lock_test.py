import json

from ldap_access.ldap_data_access import get_ad_domain_users

if __name__ == '__main__':
    with open('blocktests.config') as f:
        config = json.load(f)
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    servers = config.get("servers", [])
    filter = "(&(objectClass=user)(userAccountControl:1.2.840.113556.1.4.803:=2)(objectClass=person)(!(objectClass=computer))(!(isDeleted=TRUE))(cn=*))"

    locked_users = {}
    process_servers = 0
    for server in servers:
        print(server['ldap_server'])
        users = get_ad_domain_users(server, global_user_data, filter)
        if users:
            process_servers += 1
            for user in users:
                user_data = locked_users.setdefault(user["sAMAccountName"], user)
                user_data.setdefault('lock_servers', []).append(server['ldap_server'])

    for key, value in locked_users.items():
        locked_users = value['lock_servers']
        if len(locked_users) < process_servers:
            print(f"account '{key}' {value["cn"]} locked on  [{process_servers}] servers {value['dn']}")
