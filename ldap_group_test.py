import json

import ldap

from ldap_access.ldap_data_access import get_ad_domain_groups, add_ad_domain_user_to_group, \
    remove_ad_domain_user_from_group, ad_group_members, ad_group_members_dn

if __name__ == '__main__':
    with open('import.config') as f:
        config = json.load(f)
    global_user_data = config.get("domain_user", {'login': 'admin', 'password': '<PASSWORD>'})
    debug_mode = config.get("debug_mode", False)
    config_ldap = {"ldap_server":"ldap://dcbs0201.bs.local.erc", "dn":"DC=bs,DC=local,DC=erc"}
    #config_ldap = {"ldap_server": "ldap://dc01.local.erc", "dn":"OU=Prog W7,OU=DomainUsers,DC=local,DC=erc"}
    print(get_ad_domain_groups(config_ldap, global_user_data, "sAMAccountName=Erc_web_users"))

    print(ad_group_members(config_ldap, global_user_data, 'Erc_web_users'))
    # add_ad_domain_user_to_group(config_ldap, global_user_data, 'Erc_web_users', 'msy')
    # print(ad_group_members(config_ldap, global_user_data, 'Erc_web_users'))
    # remove_ad_domain_user_from_group(config_ldap, global_user_data, 'Erc_web_users', 'msy')
    # print(ad_group_members(config_ldap, global_user_data, 'Erc_web_users'))

    print(ad_group_members_dn(config_ldap, global_user_data, 'ERC_RDS_RDCD'))
