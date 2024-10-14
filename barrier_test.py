import requests
import urllib3

urllib3.disable_warnings()
if __name__ == '__main__':
    ses = requests.session()
    res = ses.get('https://ident.sd.bs.local.erc:8093/.well-known/openid-configuration', verify=False)
    if res.status_code == 200:
        data = res.json()
        if data.get('token_endpoint', None) is not None:
            token_endpoint = data.get('token_endpoint')
            print(data['token_endpoint'])
        else:
            print("NO TOKEN ENDPOINT")
            exit(1)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        id_data = {
            'client_id': 'ident-sd-service',
            'client_secret': '665b6f638c2da3ecc5d3a1868eb9352f6e01ee4a',
            'grant_type': 'client_credentials'
        }
        id_data2 = {
            'client_id': '68531165ED89F3C5C45DE5492C63EA11',
            'client_secret': '1B393CD51C854BD3F34234F63C1E587799F57407900158FC257AF51510387D21',
            'grant_type': 'client_credentials'
        }

        res = ses.post(token_endpoint, verify=False, data=id_data2,
                       headers=headers)
        if res.status_code == 200:
            data = res.json()
            if data.get('access_token', None) is not None:
                print(data['access_token'])
                # https://sd.bs.local.erc/0/odata/LDAPElement
                # https://sd.bs.local.erc/0/odata/SysAdminUnit
                # https://sd.bs.local.erc/0/odata/Contact

                res = ses.get('https://sd.bs.local.erc/0/odata/Contact',
                              headers={'Authorization': 'Bearer ' + data['access_token']}, verify=False)
                if res.status_code == 200:
                    # print(res.json())
                    data = res.json()
                    if "value" in data:
                        for obj in data['value']:
                            print(obj)
                            # print(obj['Id'], obj['Name'])

                else:
                    print("INVALID: ", res.status_code)
            else:
                print("invalid response: ", data)
        else:
            print(res.status_code)
            print(res.text)
    else:
        print(res.status_code)
        print(res)
