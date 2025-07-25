import logging
from sqlite3.dbapi2 import paramstyle

import pyodbc


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

def update_user_activity(cursor, logger):
    try:

        update_sql = """
                     UPDATE u
                     SET u.Active = CASE
                                        WHEN c.MscActivity = 1 AND (c.MscReasonForTemporaryAbsence IS NULL OR c.MscReasonForTemporaryAbsence = '') THEN 1
                                        ELSE 0
                         END
                         FROM dbo.SysAdminUnit AS u
                     LEFT JOIN dbo.Contact AS c ON u.ContactId = c.Id
                     WHERE (u.LDAPEntryId IS NOT NULL AND u.LDAPEntryId <> '' AND MscActivity IS NOT NULL) AND u.Active <> CASE
                         WHEN c.MscActivity = 1 AND (c.MscReasonForTemporaryAbsence IS NULL OR c.MscReasonForTemporaryAbsence = '') THEN 1
                         ELSE 0
                     END; \
                     """
    
        cursor.execute(update_sql)
        affected_rows = cursor.rowcount
        logger.info(f"🔄 Оновлено записів: {affected_rows}")
        cursor.commit()
        return affected_rows
    except pyodbc.Error as e:
        logger.error("❌ Database error:", e)
        return -1
        
def need_update(cursor, logger):
    try:

        sql = """
                     SELECT u.[Name], u.Active, c.MscActivity, c.MscReasonForTemporaryAbsence
                     FROM dbo.SysAdminUnit AS u
                     LEFT JOIN dbo.Contact AS c ON u.ContactId = c.Id
                     WHERE (u.LDAPEntryId IS NOT NULL AND u.LDAPEntryId <> '' AND MscActivity IS NOT NULL) AND u.Active <> CASE
                         WHEN c.MscActivity = 1 AND (c.MscReasonForTemporaryAbsence IS NULL OR c.MscReasonForTemporaryAbsence = '') THEN 1
                         ELSE 0
                     END; \
                     """

        cursor.execute(sql)
        return return_records_simple(cursor, sql)
    except pyodbc.Error as e:
        logger.error("❌ Database error:", e)
        return []


def insert_user_record_with_log(logger, cursor, name, contact_id, ldap_record,
                       creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                       sysculture_id='A5420246-0A8E-E111-84A3-00155D054C03',      
                                parent_role_id=None,connection_type:int=1
                                ):
    cursor.execute(f"SELECT COUNT(name) from dbo.SysAdminUnit WHERE name = '{name}'")
    if cursor.fetchall()[0][0] == 0:
        ldap_id = ldap_record['Id']
        ldap_name = ldap_record['Name']
        ldap_dn = ldap_record['LDAPEntryDN']
        ldap_entry_code = ldap_record['LDAPEntryId']
        sql = (
            f'DECLARE @InsertedIds TABLE (Id UNIQUEIDENTIFIER); '
            f'INSERT INTO  dbo.SysAdminUnit(name, ContactId, LDAPEntryId, LDAPEntry,LDAPElementId,'
            f'LDAPEntryDN, SysAdminUnitTypeValue, Active,'
            f'SynchronizeWithLDAP,CreatedById, ModifiedById,IsDirectoryEntry,SysCultureId,ConnectionType,ParentRoleId) '
            f'OUTPUT INSERTED.Id INTO @InsertedIds'
            f" VALUES(?, ?, ?, ?, ?, ?, 4, 1, 1, ?, ?, 0, ?, ?, ?);"
            f" SELECT Id FROM @InsertedIds;")
        
        logger.info(f'Inserting SysAdminUnit record {name}')
        logger.debug(sql)
        try:
            params = (name, contact_id, ldap_entry_code, ldap_name, ldap_id, ldap_dn,
                        creator_id, creator_id, sysculture_id,connection_type, parent_role_id)
            cursor.execute(sql , params)
            while True:
                if cursor.description:
                    break
                if not cursor.nextset():
                    raise Exception("No result set returned from SQL")
            
            # Тепер можна отримати дані
            row = cursor.fetchone()
            if row is None:
                raise Exception("SELECT from @InsertedIds returned no rows")
            
            recordid = row[0]
            #cursor.execute('SELECT @@Identity AS ID')
            print(f'Record SysAdminUnit({name}) with record ID {recordid} created with {parent_role_id}.')
            logger.debug(f'Record SysAdminUnit({name}) with record ID {recordid} created.')
            cursor.commit()
            return recordid
        except Exception as e:
            logger.error(e)
            logger.error(sql)
            cursor.rollback()



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
            cursor.commit()
            return True
        except Exception as e:
            print(sql)
            print(e)
            return False

def insert_user_sysrole_record(cursor, user_id, role_id,
                            creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                            debug=False):
    cursor.execute(f"SELECT COUNT(SysAdminUnitId) from dbo.SysAdminUnitInRole WHERE SysAdminUnitId='{user_id}' AND SysAdminUnitRoleId='{role_id}'")
    if cursor.fetchall()[0][0] == 0:
        sql_role = (
            f'INSERT INTO  dbo.SysAdminUnitInRole(SysAdminUnitId, SysAdminUnitRoleId, ProcessListeners, CreatedById, ModifiedById, Source) '
            f" VALUES('{user_id}','{role_id}', 0, '{creator_id}','{creator_id}', 18)")
        sql_self = (
            f'INSERT INTO  dbo.SysAdminUnitInRole(SysAdminUnitId, SysAdminUnitRoleId, ProcessListeners, CreatedById, ModifiedById, Source) '
            f" VALUES('{user_id}','{role_id}', 0, '{creator_id}','{creator_id}', 2)")
        
        if debug:
            print(sql_role)
            print(sql_self)
        try:
            cursor.execute(sql_role)
            cursor.execute(sql_self)
            cursor.commit()
            return True
        except Exception as e:
            print(sql_role)
            print(sql_self)
            print(e)
            return False

def insert_user_sysrole_record(cursor, user_id, role_id,
                               creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                               debug=False):
    cursor.execute(f"SELECT COUNT(SysAdminUnitId) from dbo.SysAdminUnitInRole WHERE SysAdminUnitId='{user_id}' AND SysAdminUnitRoleId='{role_id}'")
    if cursor.fetchall()[0][0] == 0:
        sql_role = (
            f'INSERT INTO  dbo.SysAdminUnitInRole(SysAdminUnitId, SysAdminUnitRoleId, ProcessListeners, CreatedById, ModifiedById, Source) '
            f" VALUES('{user_id}','{role_id}', 0, '{creator_id}','{creator_id}', 18)")
        if debug:
            print(sql_role)
        try:
            cursor.execute(sql_role)
            cursor.commit()
            return True
        except Exception as e:
            print(sql_role)
            print(e)
            return False


def insert_user_self_role_record(cursor, user_id, creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                               debug=False):
    cursor.execute(f"SELECT COUNT(SysAdminUnitId) from dbo.SysAdminUnitInRole WHERE SysAdminUnitId='{user_id}' AND SysAdminUnitRoleId='{user_id}'")
    if cursor.fetchall()[0][0] == 0:
        sql_self = (
            f'INSERT INTO  dbo.SysAdminUnitInRole(SysAdminUnitId, SysAdminUnitRoleId, ProcessListeners, CreatedById, ModifiedById, Source) '
            f" VALUES('{user_id}','{user_id}', 0, '{creator_id}','{creator_id}', 1)")

        if debug:
            print(sql_self)
        try:
            cursor.execute(sql_self)
            cursor.commit()
            return True
        except Exception as e:
            print(sql_self)
            print(e)
            return False


def insert_license_record(cursor, user_id, license_id,
                               creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                               debug=False):
    cursor.execute(f"SELECT COUNT(SysUserId) from dbo.SysLicUser WHERE SysUserId='{user_id}' AND SysLicPackageId='{license_id}'")
    if cursor.fetchall()[0][0] == 0:
        sql_role = (
            f'INSERT INTO  dbo.SysLicUser(SysUserId, SysLicPackageId, ProcessListeners, CreatedById, ModifiedById, Source, Active) '
            f" VALUES('{user_id}','{license_id}', 0, '{creator_id}','{creator_id}', 1, 1)")
        if debug:
            print(sql_role)
        try:
            cursor.execute(sql_role)
            cursor.commit()
            return True
        except Exception as e:
            print(sql_role)
            print(e)
            return False


def get_license_id(cursor, name,
                          debug=False):
    sql = f"SELECT Id from dbo.SysLicPackage WHERE Name='{name}'"
    print(sql)
    cursor.execute(sql)
    data = cursor.fetchall()[0] 
    if data:
        return data[0]
    return None
        


def combine_role(cursor, creatio_api,role_name:str = 'All employees',
                 creator_id:str='410006e1-ca4e-4502-a9ec-e54d922d2c00'):

        role = creatio_api.get_user_roles_by_name(role_name)
        if role:
            role_id = role['Id']
            users = creatio_api.get_short_users()
            for user_name,user in users.items():
                user_roles = creatio_api.get_user_roles(user['Id'])
                if not role_name in user_roles:
                #     print(f'User {user_name} has no role: {role_name}')
                    insert_user_role_record(cursor, user['Id'], role_id, creator_id)
            return True
        else:
            print(f'Role {role_name} don`t exist')
            return False

def return_records_simple(cursor, sql, *params):
    cur = cursor.execute(sql, *params)
    columns = [column[0] for column in cur.description]
    results = []
    for row in cur.fetchall():
        results.append(dict(zip(columns, row)))
    return results

def return_records(cursor, sql, *params, page=None, page_size=None, count_total=False):
    """
    Виконує SQL запит з підтримкою пагінації
    
    Args:
        cursor: курсор бази даних
        sql: SQL запит
        *params: параметри для SQL запиту
        page: номер сторінки (починається з 1)
        page_size: кількість записів на сторінці
        count_total: чи підраховувати загальну кількість записів
    
    Returns:
        dict з полями:
        - data: список записів у вигляді словників
        - page: поточна сторінка (якщо використовується пагінація)
        - page_size: розмір сторінки
        - total_records: загальна кількість записів (якщо count_total=True)
        - total_pages: загальна кількість сторінок (якщо count_total=True)
        - has_next: чи є наступна сторінка
        - has_prev: чи є попередня сторінка
    """

    # Якщо пагінація не використовується, повертаємо як раніше
    if page is None or page_size is None:
        cur = cursor.execute(sql, *params)
        columns = [column[0] for column in cur.description]
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))
        return results

    # Валідація параметрів пагінації
    if page < 1:
        raise ValueError("Номер сторінки повинен бути >= 1")
    if page_size < 1:
        raise ValueError("Розмір сторінки повинен бути >= 1")

    total_records = None
    total_pages = None

    # Підрахунок загальної кількості записів (якщо потрібно)
    if count_total:
        # Створюємо COUNT запит з оригінального SQL
        count_sql = f"SELECT COUNT(*) FROM ({sql}) AS count_query"
        count_cur = cursor.execute(count_sql, *params)
        total_records = count_cur.fetchone()[0]
        total_pages = (total_records + page_size - 1) // page_size  # Округлення вгору

    # Додаємо LIMIT і OFFSET до оригінального запиту
    offset = (page - 1) * page_size
    paginated_sql = f"{sql} LIMIT ? OFFSET ?"

    # Виконуємо запит з пагінацією
    cur = cursor.execute(paginated_sql, *params, page_size, offset)
    columns = [column[0] for column in cur.description]

    results = []
    for row in cur.fetchall():
        results.append(dict(zip(columns, row)))

    # Визначаємо наявність попередніх/наступних сторінок
    has_prev = page > 1
    has_next = len(results) == page_size  # Якщо отримали повну сторінку, можливо є ще

    # Якщо знаємо загальну кількість, точно визначаємо has_next
    if total_pages is not None:
        has_next = page < total_pages

    return {
        'data': results,
        'page': page,
        'page_size': page_size,
        'total_records': total_records,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev
    }


# Приклади використання:

# 1. Без пагінації (як раніше)
# records = return_records(cursor, "SELECT * FROM users WHERE active = ?", 1)

# 2. З пагінацією
# result = return_records(cursor, "SELECT * FROM users WHERE active = ?", 1, 
#                        page=1, page_size=10)
# print(f"Записи: {result['data']}")
# print(f"Сторінка {result['page']} з {result.get('total_pages', '?')}")

# 3. З підрахунком загальної кількості
# result = return_records(cursor, "SELECT * FROM users WHERE active = ?", 1,
#                        page=1, page_size=10, count_total=True)
# print(f"Показано {len(result['data'])} з {result['total_records']} записів")

# Альтернативний варіант з окремими методами:
def return_records_paginated(cursor, sql, *params, page=1, page_size=20, count_total=False):
    """Метод тільки для пагінації"""
    return return_records(cursor, sql, *params, page=page, page_size=page_size, count_total=count_total)



def search_contacts(cursor, search=None):
    sql = """
          SELECT contact.[Id]
               ,contact.[Name]
               ,contact.[JobTitle]
               ,contact.[UsrERCLogin]
               ,dev.[Name] as division
               ,sub.[Name] as subdivision
               ,sec.[Name] as section_l4
               ,dep.[Name] as department
               ,grp.[Name] as group_name
               ,distl5.[Name] as distl5
               ,contact.[MscActivity]
               ,contact.[MscEmployeeQR]
               ,contact.[MscCorpPhone]
               ,contact.[MscReasonForTemporaryAbsence]
               ,contact.[MscLogin]
               ,bos.[Name] as boss_name
               ,bos.JobTitle as boss_job_title
               ,bos.email as boss_email
               ,bos.MscCorpPhone as boss_phone
               ,bos.UsrERCLogin as boss_login
               ,bos.Phone as boss_personal_phone
          FROM [dbo].[Contact] as contact
              LEFT JOIN dbo.MscDivisionL3 as dev ON contact.MscDivisionL3Id = dev.Id
              LEFT JOIN dbo.MscSubdivision as sub ON contact.MscSubdivisionId = sub.Id
              LEFT JOIN dbo.MscSectionL4 as sec ON contact.MscSectionL4Id = sec.Id
              LEFT JOIN dbo.Department as dep ON contact.MscDepartmentId = dep.Id
              LEFT JOIN dbo.Contact as bos ON contact.MscImmediateBossId = bos.Id
              LEFT JOIN dbo.MscDistrictL5 as distl5 ON contact.MscDistrictL5Id = distl5.Id
              LEFT JOIN dbo.MscGroup as grp ON contact.MscGroupId = grp.Id \
          """

    if search:
        pattern = f"%{search}%"
        sql += """
            WHERE (
                LOWER(LTRIM(RTRIM(contact.[UsrERCLogin]))) LIKE LOWER(?) OR
                LOWER(LTRIM(RTRIM(contact.[Name]))) COLLATE Cyrillic_General_CI_AS LIKE LOWER(?) OR
                LOWER(LTRIM(RTRIM(contact.JobTitle))) COLLATE Cyrillic_General_CI_AS LIKE LOWER(?)
            )
        """
        return return_records_simple(cursor, sql, pattern, pattern, pattern)

    return return_records_simple(cursor, sql)

    


def get_license_count(cursor):
    sql = """SELECT  lp.name, count(u.id) as used_licenses
FROM dbo.SysAdminUnit as u,
dbo.SysLicUser as l,
dbo.SysLicPackage as lp
where u.id = l.sysuserid and l.syslicpackageid=lp.id
group by lp.name"""
    return return_records_simple(cursor, sql)

def get_licenses(cursor):
    sql = """SELECT  u.Name, lp.name
             FROM dbo.SysAdminUnit as u,
                  dbo.SysLicUser as l,
                  dbo.SysLicPackage as lp
             where u.id = l.sysuserid and l.syslicpackageid=lp.id"""
    return return_records_simple(cursor, sql)

def combine_users_records(cursor, creatio_api,
                          creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00',
                          sysculture_id='A5420246-0A8E-E111-84A3-00155D054C03',
                          logger=None, success_logger=None
                          ):
    if logger is None:
        logger = logging.getLogger()
    if success_logger is None:
        success_logger = logging.getLogger()
    users_name, users_login, domain_login_sets = creatio_api.get_user_names_set()
    ldap_record_dict = creatio_api.get_ldap_by_domain_login()
    logger.debug(f"user name {users_name}")
    logger.debug(f"user login {users_login}")
    logger.debug(f"ldap records keys {ldap_record_dict.keys()}")
    contact_set = creatio_api.get_contacts_set()[1:]
    for contact in contact_set:
        contact_id = contact['Id']
        contact_name = contact['Name']
        contact_login = contact['UsrERCLogin']
        if contact_login not in users_login and contact_login not in domain_login_sets:
            if contact_login in ldap_record_dict:
                logger.debug(f"Need create user for login {contact_login}")
                ldap_record = ldap_record_dict[contact_login]

                simple_login_name = contact_login.split('\\')[1]
                try:
                    insert_user_record(cursor, simple_login_name, contact_id, ldap_record, creator_id, sysculture_id)
                except Exception as e:
                    logger.error(f"ERROR CREATE USER: {e}")
            else:
                logger.debug('User name: {} - not exists, but ldap login {}- does not exist! '.format(contact_name,
                                                                                               contact_login))
        else:
            logger.debug('User name: {} login:{} - exists'.format(contact_name, contact_login))

