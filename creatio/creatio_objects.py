from creatio.creatio_api import CreatioAPI



class ContactHolders:
    def __init__(self, api: CreatioAPI, use_cache=True, fields=None):
        if use_cache:
            #by_name, by_login, by_full_name = api.get_short_contacts_dicts()
            by_name, by_login = api.get_short_contacts_dicts()
            self.by_name = by_name
            self.by_login = by_login
            #self.by_full_name = by_full_name
        else:
            self.by_name = {}
            self.by_login = {}
            #self.by_full_name = {}
        if fields is not None:
            self.fields = fields
        else:
            self.fields = []
        self.api = api
        self.use_cache = use_cache


    def get_by_login(self, login: str) -> dict | None:
        if self.use_cache:
            return self.by_login.get(login, None)
        return self.api.get_contact_by_ldap_login(login)

    def get_by_name(self, name: str) -> dict | None:
        if self.use_cache:
            return self.by_name.get(name, None)
        return self.api.get_contact_by_name(name)

    def get_by_full_name(self, full_name: str) -> dict | None:
        return self.by_full_name.get(full_name, None)

    def get_id_by_login(self, login: str) -> str | None:
        contact = self.get_by_login(login)
        if contact is None:
            return None
        return contact['Id']

    def get_id_by_name(self, name: str) -> str | None:
        contact = self.get_by_name(name)
        if contact is None:
            return None
        return contact['Id']

    def contact_by_name(self, name: str, domain_login_name: str, need_update=True) -> str | None:
        contact = self.get_by_name(name)
        if contact is None:
            return None
        contact_id = contact['Id']
        erc_login_name = contact['UsrERCLogin']
        if not erc_login_name and need_update:
            self.api.update_concat_login(contact_id, domain_login_name)
        return contact['Id']

    def get_id_by_full_name(self, full_name: str) -> str | None:
        contact = self.get_by_full_name(full_name)
        if contact is None:
            return None
        return contact['Id']

    def find_or_create_contact(self, contact_name: str, domain_perfix: str, login_name: str, ldap_entry: dict,
                               create_contact: bool = True, ) -> str:
        domain_login_name = f'{domain_perfix}{login_name}'
        contact = self.get_id_by_login(domain_login_name)
        if contact:
            return contact

        contact = self.get_id_by_login(login_name)
        if contact:
            return contact

        contact_id = self.contact_by_name(contact_name, domain_login_name)
        if contact_id:
            return contact_id

        clear_name = contact_name.replace('.', ' ')

        contact_id = self.contact_by_name(clear_name, domain_login_name)
        if contact_id:
            return contact_id

        if create_contact:
            contact = self.api.create_object('Contact', {
                'Name': contact_name,
                'Email': ldap_entry['Email'],
                'Phone': ldap_entry['Phone'],
                'JobTitle': ldap_entry['JobTitle'],
                'FullName': ldap_entry['cn'],
                'UsrERCLogin': domain_login_name,
            })
            if contact:
                if self.use_cache:
                    self.by_name[contact_name] = contact
                    self.by_login[domain_login_name] = contact
                    self.by_full_name[ldap_entry['cn']] = contact
                return contact['Id']
        return ''


class User:
    def __init__(self, name, email, password, description):
        self.name = name
        # self.full_name =
        self.description = description
        self.sysAdminUnitTypeValue = 1
        self.sysAdminUnitType = 0
        self.id = None
        # self.created_on =
