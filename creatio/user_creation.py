def insert_user_record(cursor, name, contact_id, ldap_record,
                       creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                       sysculture_id='A5420246-0A8E-E111-84A3-00155D054C03',
                       debug=False):
    cursor.execute(f"SELECT COUNT(name) from dbo.SysAdminUnit WHERE name = '{name}'")
    if cursor.fetchall()[0][0] == 0:
        ldap_id = ldap_record['Id']
        ldap_name = ldap_record['Name']
        ldap_dn = ldap_record['LDAPEntryDN']
        ldap_entry_code = ldap_record['LDAPEntryId']
        sql = (
            f'INSERT INTO  dbo.SysAdminUnit(name, ContactId, LDAPEntryId, LDAPEntry,LDAPElementId,'
            f'LDAPEntryDN, SysAdminUnitTypeValue, Active,'
            f'SynchronizeWithLDAP,CreatedById, ModifiedById,IsDirectoryEntry,SysCultureId,ConnectionType) '
            f" VALUES('{name}','{contact_id}','{ldap_entry_code}','{ldap_name}','{ldap_id}','{ldap_dn}', "
            f" 4,1, 1,'{creator_id}','{creator_id}',0, '{sysculture_id}', 0)")
        if debug:
            print(sql)
        try:
            cursor.execute(sql)
        except Exception as e:
            print(sql)
            print(e)
        cursor.commit()


def insert_user_role_record(cursor, user_id, role_id,
                       creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                       debug=False):
    cursor.execute(f"SELECT COUNT(SysUserId) from dbo.SysUserInRole WHERE SysUserId='{user_id}' AND SysRoleId='{role_id}'")
    if cursor.fetchall()[0][0] == 0:
        sql = (
            f'INSERT INTO  dbo.SysUserInRole(SysUserId, SysRoleId, ProcessListeners, CreatedById, ModifiedById) '
            f" VALUES('{user_id}','{role_id}', 0, '{creator_id}','{creator_id}')")
        if debug:
            print(sql)
        try:
            cursor.execute(sql)
        except Exception as e:
            print(sql)
            print(e)
        cursor.commit()



def combine_role(cursor, creatio_api,role_name:str = 'All employees',
                 creator_id:str='410006e1-ca4e-4502-a9ec-e54d922d2c00'):

        role = creatio_api.get_user_roles_by_name(role_name)
        if role:
            role_id = role['Id']
            users = creatio_api.get_short_users()
            for user_name,user in users.items():
                # user_roles = creatio_api.get_user_roles(user['Id'])
                # if not role_name in user_roles:
                #     print(f'User {user_name} has no role: {role_name}')
                insert_user_role_record(cursor, user['Id'], role_id, creator_id)
        print(f'Role {role_name} don`t exist')


def combine_users_records(cursor, creatio_api,
                          creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                          sysculture_id='A5420246-0A8E-E111-84A3-00155D054C03',
                          debug=False, log_records: list = None
                          ):
    if log_records is None:
        log_records = []
    users_name, users_login, domain_login_sets = creatio_api.get_user_names_set()
    ldap_record_dict = creatio_api.get_ldap_by_domain_login()
    if debug:
        print(users_name)
        print(users_login)
        print(ldap_record_dict.keys())
    contact_set = creatio_api.get_contacts_set()[1:]
    for contact in contact_set:
        contact_id = contact['Id']
        contact_name = contact['Name']
        contact_login = contact['UsrERCLogin']
        if contact_login not in users_login and contact_login not in domain_login_sets:
            if contact_login in ldap_record_dict:
                print(f"Need create user for login {contact_login}")
                ldap_record = ldap_record_dict[contact_login]

                simple_login_name = contact_login.split('\\')[1]
                try:
                    insert_user_record(cursor, simple_login_name, contact_id, ldap_record, creator_id, sysculture_id, debug)
                except Exception as e:
                    log_records.append(f"ERROR CREATE USER: {e}")
            else:
                log_records.append('User name: {} - not exists, but ldap login {}- does not exist! '.format(contact_name,
                                                                                               contact_login))
        else:
            log_records.append('User name: {} login:{} - exists'.format(contact_name, contact_login))
    return log_records
