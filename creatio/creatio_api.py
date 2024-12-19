from urllib.parse import urlencode

import requests
import urllib3

urllib3.disable_warnings()


class Creatio:
    def __init__(self, username, password,
                 use_barrier=False,
                 service_url="https://sd.bs.local.erc/",
                 ident_service_url="https://ident.sd.bs.local.erc:8093/",
                 debug_mode=False):
        self.username = username
        self.password = password
        self.service_url = service_url
        self.ident_service_url = ident_service_url
        self.use_barrier = use_barrier
        self.session = requests.Session()
        self.barrier = None
        self.logged_in = False
        self.debug = debug_mode
        self.verify = False

    def login(self) -> bool:
        if self.use_barrier:
            barrier_url = self.ident_service_url + "connect/token"
            id_data = {
                'client_id': self.username,
                'client_secret': self.password,
                'grant_type': 'client_credentials'
            }
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            print(barrier_url)
            res = requests.post(barrier_url, headers=headers, data=id_data, verify=self.verify)
            if res.status_code == 200:
                data = res.json()
                if data.get('access_token', None) is not None:
                    if self.debug:
                        print(data['access_token'])
                    self.barrier = data['access_token']
                    self.session.headers['Authorization'] = 'Bearer ' + self.barrier
                    self.logged_in = True
                    return True
            elif self.debug:
                print(f"LOGIN ERROR [{res.status_code}]:{res.text}")
            return False
        else:
            login_url = self.service_url + 'ServiceModel/AuthService.svc/Login'
            res = self.session.post(login_url,
                                    json={'UserName': self.username, 'UserPassword': self.password},
                                    verify=self.verify
                                    )
            if res.status_code == 200:
                if res.json().get('Code', -1) == 0:
                    self.logged_in = True
                    self.session.headers['BPMCSRF'] = res.cookies.get('BPMCSRF')
                    return True
            elif self.debug:
                print(f"LOGIN ERROR [{res.status_code}]:{res.text}")
            return False

    def form_url_params(self, **params) -> str:
        query_params = {}
        for key, value in params.items():
            if value is not None:
                if isinstance(value, list):
                    query_params['$' + key] = ','.join(value)
                else:
                    query_params['$' + key] = value
        if query_params:
            return '?' + urlencode(query_params)
        return ''

    def form_collection_url(self, object_name: str, **params) -> str:
        url = f'{self.service_url}0/odata/{object_name}{self.form_url_params(**params)}'
        if self.debug:
            print(url)
        return url

    def form_object_url(self, object_name: str, object_id: str, **params) -> str:
        url = f'{self.service_url}0/odata/{object_name}({object_id}){self.form_url_params(**params)}'
        if self.debug:
            print(url)
        return url

    def form_object_field_url(self, object_name: str, object_id: str, field_name: str, **params) -> str:
        url = f'{self.service_url}0/odata/{object_name}({object_id})/{field_name}{self.form_url_params(**params)}'
        if self.debug:
            print(url)
        return url

    def send_get_request(self, url: str) -> dict:
        if self.logged_in:
            try:
                res = self.session.get(url, verify=self.verify)
                if res.status_code == 200:
                    data = res.json()
                    return data
                else:
                    if self.debug:
                        print(f"ERROR [{res.status_code}]: {res.text}")
            except Exception as e:
                if self.debug:
                    print("EXCEPTION: ", e)
        return {}

    def get_objects(self, catalog_name: str, skip: int = None, stop: int = None, fields: list = None,
                    filter: str = None, sort: str = None, expand: str = None) -> list:
        url = self.form_collection_url(catalog_name, skip=skip, top=stop, select=fields,
                                       filter=filter, orderby=sort, expand=expand)
        data = self.send_get_request(url)
        if "value" in data:
            return data["value"]
        else:
            if self.debug:
                print("incorrect data", data)
        return []

    def clear_metadata(self, response_dict: dict) -> dict:
        for key in list(response_dict.keys()):
            if key.startswith('@'):
                del response_dict[key]
        return response_dict

    def get_object(self, catalog_name: str, object_id: str, fields: list = None) -> dict:
        url = self.form_object_url(catalog_name, object_id)
        return self.clear_metadata(self.send_get_request(url))

    def get_object_field(self, catalog_name: str, object_id: str, field_name: str) -> str | None:
        url = self.form_object_field_url(catalog_name, object_id, field_name)
        data = self.send_get_request(url)
        if "value" in data:
            return data["value"]
        else:
            if self.debug:
                print("incorrect data", data)
        return None

    def get_object_field_value(self, catalog_name: str, object_id: str, field_name: str) -> str | None:
        if self.logged_in:
            try:
                url = self.form_object_field_url(catalog_name, object_id, field_name) + '/%24value'
                res = self.session.get(url, verify=self.verify)
                if res.status_code == 200:
                    return res.text
            except Exception as e:
                if self.debug:
                    print("EXCEPTION: ", e)
        return None

    def update_object(self, catalog_name: str, object_id: str, data: dict) -> bool:
        if self.logged_in:
            try:
                # url = self.form_object_url(catalog_name, object_id)
                url = f'{self.service_url}0/odata/{catalog_name}/{object_id}'
                if self.debug:
                    print(url)
                res = self.session.patch(url, json=data, verify=self.verify)
                if res.status_code == 204:
                    return True
                if self.debug:
                    print(f"ERROR [{res.status_code}]: {res.text}")
            except Exception as e:
                if self.debug:
                    print("EXCEPTION: ", e)
        return False

    def create_object(self, catalog_name: str, data: dict) -> dict | None:
        if self.logged_in:
            try:
                url = self.form_collection_url(catalog_name)
                res = self.session.post(url, json=data, verify=self.verify)
                if res.status_code == 201:
                    return self.clear_metadata(res.json())
                if self.debug:
                    print(f"ERROR [{res.status_code}]: {res.text}")
            except Exception as e:
                if self.debug:
                    print("EXCEPTION: ", e)
        return None

    def delete_object(self, catalog_name: str, object_id: str) -> bool:
        if self.logged_in:
            try:
                url = self.form_object_url(catalog_name, object_id)
                res = self.session.delete(url, verify=self.verify)
                if res.status_code == 204:
                    return True
                if self.debug:
                    print(f"ERROR [{res.status_code}]: {res.text}")
            except Exception as e:
                if self.debug:
                    print("EXCEPTION: ", e)
        return False


class CreatioAPI(Creatio):
    def get_contact_id_by_ldap_login(self, login_name: str) -> str:
        res = self.get_objects('Contact', filter=f"UsrERCLogin eq '{login_name}'", fields=['Id'])
        if res:
            return res[0]["Id"]
        return ''

    def get_contact_by_name(self, contact_name: str) -> dict | None:
        res = self.get_objects('Contact', filter=f"Name eq '{contact_name}'")
        if res:
            return res[0]
        return None

    def get_contact_by_ldap_login(self, login_name: str) -> dict | None:
        res = self.get_objects('Contact', filter=f"UsrERCLogin eq '{login_name}'")
        if res:
            return res[0]
        return None

    def get_contact_id_by_name(self, contact_name: str) -> str:
        res = self.get_objects('Contact', filter=f"Name eq '{contact_name}'", fields=["Id"])
        if res:
            return res[0]['Id']
        return ''

    def get_contact_id_login_by_name(self, contact_name: str) -> (str, str):
        res = self.get_objects('Contact', filter=f"Name eq '{contact_name}'", fields=["Id", 'UsrERCLogin'])
        if res:
            return res[0]['Id'], res[0]['UsrERCLogin']
        return '', ''

    def get_ldap_by_fullnames(self):
        ldap_entries = self.get_objects('LDAPElement',
                                        fields=['Id', 'Name', 'FullName', 'isActive', 'Description',
                                                'LDAPEntryId', 'LDAPEntryDN', 'Company', 'Email', 'Phone', 'JobTitle',
                                                'ModifiedOn'],
                                        # expand='Type($select=Id,Name)'
                                        )
        return {ldap['FullName']: ldap for ldap in ldap_entries}

    def get_ldap_by_domain_login(self):
        ldap_entries = self.get_objects('LDAPElement',
                                        fields=['Id', 'Name', 'FullName', 'isActive', 'Description',
                                                'LDAPEntryId', 'LDAPEntryDN', 'Company', 'Email', 'Phone', 'JobTitle',
                                                'ModifiedOn'],
                                        # expand='Type($select=Id,Name)'
                                        )
        ldaps_by_domain = {}
        for ldap in ldap_entries:
            domain = ldap['FullName'].split('\\')[0]
            domain_login = '{}\\{}'.format(domain, ldap['Name'])
            ldaps_by_domain[domain_login] = ldap
        return ldaps_by_domain

    def get_ldap_info(self):
        ldap_entries = self.get_objects('LDAPElement',
                                        fields=['Id', 'Name', 'FullName', 'isActive', 'Description',
                                                'LDAPEntryId', 'LDAPEntryDN', 'Company', 'Email', 'Phone', 'JobTitle',
                                                'ModifiedOn'],
                                        # expand='Type($select=Id,Name)'
                                        )
        return {ldap['Name']: ldap for ldap in ldap_entries}

    def update_ldap_entry(self, ldap_entry_id: str, ldap_entry: dict) -> bool:
        return self.update_object('LDAPElement', ldap_entry_id, ldap_entry)

    def create_ldap_entry(self, ldap_entry: dict) -> dict | None:
        return self.create_object('LDAPElement', ldap_entry)

    def get_short_contacts(self, fields: list = None) -> list | None:
        if fields is None:
            fields = ['Id', 'Name', 'UsrERCLogin']
            # fields = ['Id', 'Name', 'FullName', 'UsrERCLogin']
        contacts = self.get_objects('Contact',
                                    fields=fields,
                                    )
        return contacts

    def get_short_contacts_dicts(self):
        contacts = self.get_short_contacts()
        by_name = dict()
        by_login = dict()
        # by_full_name = dict()
        if contacts:
            for contact in contacts:
                by_name[contact['Name']] = contact
                by_login[contact['UsrERCLogin']] = contact
                # by_full_name[contact['FullName']] = contact
        return by_name, by_login  # , by_full_name

    def get_short_users(self):
        users = self.get_objects('SysAdminUnit',
                                 # fields=['Id', 'Name', 'SysAdminUnitTypeValue', 'Active', 'Description',
                                 #         'LDAPEntryId', 'LDAPEntryDN', 'SynchronizeWithLDAP', 'Email', 'Phone'],
                                 fields=['Id', 'Name', 'SysAdminUnitTypeValue', 'Active',
                                         'LDAPEntryId', 'LDAPEntryDN', 'SynchronizeWithLDAP', 'LDAPElementId'],
                                 # expand='Type($select=Id,Name)',
                                 filter='SysAdminUnitTypeValue eq 4'
                                 )

        return {user['Name']: user for user in users}

    def get_user_roles_dict(self):
        users = self.get_objects('SysAdminUnit',
                                 fields=['Id', 'Name',],
                                 filter='SysAdminUnitTypeValue eq 0'
                                 )

        return {user['Name']: user for user in users}

    def get_user_roles_by_name(self, role_name):
        #https://sd.bs.local.erc/0/odata/SysAdminUnit?%24filter=Name%20eq%20%27All%20employees%27%20and%20SysAdminUnitTypeValue%20eq%200
        users = self.get_objects('SysAdminUnit',
                                 fields=['Id', 'Name',],
                                 filter=f"Name eq '{role_name}' and SysAdminUnitTypeValue eq 0"
                                 )
        if users:
            return users[0]
        return None

    def get_users_with_domain_login(self):
        users = self.get_objects('SysAdminUnit',
                                 # fields=['Id', 'Name', 'SysAdminUnitTypeValue', 'Active', 'Description',
                                 #         'LDAPEntryId', 'LDAPEntryDN', 'SynchronizeWithLDAP', 'Email', 'Phone'],
                                 fields=['Id', 'Name', 'SysAdminUnitTypeValue', 'Active',
                                         'LDAPEntryId', 'LDAPEntryDN', 'SynchronizeWithLDAP', 'LDAPElementId'],
                                 # expand='Type($select=Id,Name)'
                                 expand='Contact($select=UsrERCLogin)',
                                 filter='SysAdminUnitTypeValue eq 4'
                                 )

        return {user['Contact']['UsrERCLogin']: user for user in users}

    def get_user_names_set(self):
        users = self.get_objects('SysAdminUnit', fields=['Name'],
                                 expand="LDAPElement($select=Name),Contact($select=UsrERCLogin)")
        # users = self.get_objects('SysAdminUnit', fields=['Name'], expand="LDAPElement($select=Name)")

        name_sets = {user['Name'] for user in users}
        login_sets = {user['LDAPElement']['Name'] for user in users}
        domain_login_sets = {user['Contact']['UsrERCLogin'] for user in users}
        return name_sets, login_sets, domain_login_sets

        # return {user['LDAPElement']['Name'] if user['LDAPElement']['Name'] else user['Name']:
        #             {'name': user['Name'], 'login': user['LDAPElement']['Name']}
        #         for user in users}

    def get_contacts_set(self):
        contacts = self.get_objects('Contact', fields=['Id', 'Name', 'UsrERCLogin'])
        return contacts

    def get_contacts_set_id(self):
        contacts = self.get_objects('Contact', fields=['Id', 'Name', 'UsrERCLogin'])
        return {contact['UsrERCLogin']:contact['Id'] for contact in contacts}


    def get_users_roles(self):
        #https://sd.bs.local.erc/0/odata/SysUserInRole?%24expand=SysUser
        users_roles = self.get_objects('SysUserInRole', fields=['Id', 'SysRoleId', 'SysUserId'],
                                 expand='SysRole($select=Name),SysUser($select=Name)')
        return users_roles

    def get_user_roles(self, user_id:str):
        user_roles = self.get_objects('SysUserInRole', fields=['Id', ],
                                 expand='SysRole($select=Name)',
                                filter=f"SysUserId eq {user_id}")
        if user_roles:
            return {role['SysRole']['Name'] for role in user_roles}
        return {}

    def update_concat_login(self, contact_id: str, contact_login: str) -> bool:
        print(f'contact contact_id: {contact_id} set ERCLogin = {contact_login}')
        return self.update_object('Contact', contact_id, {
            'UsrERCLogin': contact_login,
        })

    def create_contact(self, contact_name: str, domain_login_name: str, ldap_entry: dict,
                       use_full_name: bool = False) -> str:
        contact_dict = {
            'Name': contact_name,
            'Email': ldap_entry['Email'],
            'Phone': ldap_entry['Phone'],
            'JobTitle': ldap_entry['JobTitle'],
            # 'FullName': ldap_entry['cn'],
            'UsrERCLogin': domain_login_name,
        }
        if use_full_name:
            contact_dict['FullName'] = ldap_entry['cn']
        elif not contact_name:
            contact_dict['Name'] = ldap_entry['cn']

        contact = self.create_object('Contact', contact_dict)
        if contact:
            return contact['Id']
        return ''

    def find_or_create_contact(self, contact_name: str, domain_perfix: str, login_name: str, ldap_entry: dict,
                               create_contact: bool = True) -> str:
        domain_login_name = f'{domain_perfix}{login_name}'
        contact = self.get_contact_id_by_ldap_login(domain_login_name)
        if contact:
            return contact

        contact = self.get_contact_id_by_ldap_login(login_name)
        if contact:
            return contact

        contact_id, erc_login_name = self.get_contact_id_login_by_name(contact_name)
        if contact_id:
            if not erc_login_name:
                self.update_concat_login(contact_id, domain_login_name)
            return contact_id

        clear_name = contact_name.replace('.', ' ')

        contact_id, erc_login_name = self.get_contact_id_login_by_name(clear_name)
        if contact_id:
            if not erc_login_name:
                if not erc_login_name:
                    self.update_concat_login(contact_id, domain_login_name)
            return contact_id

        if create_contact:
            contact = self.create_object('Contact', {
                'Name': contact_name,
                'Email': ldap_entry['Email'],
                'Phone': ldap_entry['Phone'],
                'JobTitle': ldap_entry['JobTitle'],
            })
            if contact:
                return contact['Id']
        return ''

    def create_user(self, name: str, ldap_entry_id: str, ldap_entry: dict, contact_name: str) -> dict | None:
        contact = self.create_object('Contact', {
            'Name': contact_name,
            'Email': ldap_entry['Email'],
            'Phone': ldap_entry['Phone'],
            'JobTitle': ldap_entry['JobTitle'],
        })
        if contact:
            return self.create_object('SysAdminUnit', {
                'Name': name,
                'LDAPElementId': ldap_entry_id,
                'Email': ldap_entry['Email'],
                'Phone': ldap_entry['Phone'],
                'LDAPEntryDN': ldap_entry['LDAPEntryDN'],
                'LDAPEntryId': ldap_entry['LDAPEntryId'],
                "SysAdminUnitTypeValue": 4,
                "ContactId": contact['Id'],
            })
        else:
            return None

    def check_user_have_role(self, role_name:str = 'All employees'):
        role = self.get_user_roles_by_name(role_name)
        if role:
            role_id = role['Id']
            users = self.get_short_users()
            for user_name,user in users.items():
                user_roles = self.get_user_roles(user['Id'])
                if not role_name in user_roles:
                    print(f'User {user_name} has no role: {role_name}')
                    self.create_object('SysUserInRole',{
                        'SysRoleId': role_id,
                        'SysUserId': user['Id']
                    })
        print(f'Role {role_name} don`t exist')


def get_api_connector(config: dict) -> CreatioAPI:
    user_id = config.get("userid")
    password = config.get("password")
    service_url = config.get("service_url", "https://sd.bs.local.erc/")
    ident_service_url = config.get("ident_service_url", "https://ident.sd.bs.local.erc:8093/")
    use_barrier = config.get("use_barrier", False)
    debug_mode = config.get('debug_mode',False)

    return CreatioAPI(user_id, password, use_barrier, service_url, ident_service_url, debug_mode=debug_mode)
