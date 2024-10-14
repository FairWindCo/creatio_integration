import pyodbc


def show_ldap_users(cursor):
    cursor.execute('SELECT * FROM dbo.LDAPElement')
    for row in cursor:
        print('row = %r' % (row,))


def get_contact_id(cursor, contact_name='Supervisor'):
    cursor.execute(f"SELECT id FROM dbo.Contact where Name = '{contact_name}'")
    result = cursor.fetchall()
    if result:
        return result[0][0]
    return None


def insert_ldap_entry(cursor, user, creator_id='410006e1-ca4e-4502-a9ec-e54d922d2c00', name_prefix='', debug=False):
    cursor.execute(f"SELECT COUNT(name) from dbo.LDAPElement WHERE name = '{user["sAMAccountName"]}'")
    if cursor.fetchall()[0][0] == 0:
        dn = user["DN"].replace("'", "''")
        title = user["title"].replace("'", "''")
        sql = (
            f'INSERT INTO  dbo.LDAPElement(name, FullName, Phone, Email, JobTitle, Company, LDAPEntryId, LDAPEntryDN, Type, ProcessListeners, CreatedById, ModifiedById,IsActive) '
            f" VALUES('{user["sAMAccountName"]}','{name_prefix}{user["cn"]}','{user["telephoneNumber"]}','{user["mail"]}',"
            f"'{title}','{user["company"]}','{user["ldap_entry_id"]}','{dn}',"
            f"4, 0,'{creator_id}','{creator_id}',0)")
        if debug:
            print(sql)
        try:
            cursor.execute(sql)
        except Exception as e:
            print(sql)
            print(e)
        cursor.commit()


def get_db_connection(config):
    return pyodbc.connect(f"Driver={{ODBC Driver 18 for SQL Server}};"
                          f"SERVER={config['SERVER']};"
                          f"DATABASE={config['DATABASE']};"
                          f"UID={config['UID']};"
                          f"PWD={config['PWD']};"
                          #                          "Encrypt=no;"
                          "Integrated Security=false;"
                          "TrustServerCertificate=yes;"
                          "Trusted_Connection=no;")
