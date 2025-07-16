# pyinstaller --noconfirm --onefile --console  C:\Users\User\PycharmProjects\ldap_creatio_integration\simple_ldap.py
import ldap

from ldap_access.ldap_data_access import get_ad_domain_users, get_users

if __name__ == '__main__':
    ldap_client = ldap.initialize('ldap://dcbs0001.bs.local.erc')
    ldap_client.protocol_version =  ldap.VERSION3
    ldap_client.set_option(ldap.OPT_REFERRALS, 0)
    ldap_client.simple_bind('','')

    users = get_users(ldap_client)
    for user in users:
        print(user)
    ldap_client.unbind_s()
