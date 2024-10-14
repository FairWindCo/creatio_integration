import urllib3

urllib3.disable_warnings()
import requests
from requests_ntlm import HttpNtlmAuth

if __name__ == '__main__':
    #auth = HttpNtlmAuth('bs\\dev_creatio', 'Zs2C!qIkv')

    ses = requests.session()
    res = ses.get('https://ident.sd.bs.local.erc:8093/.well-known/openid-configuration', verify=False)
    if res.status_code == 200:
        print("Check ident service")
        data = res.json()
        if data.get('token_endpoint', None) is not None:
            print("Token endpoint", data['token_endpoint'])
            res = ses.get('https://sd.bs.local.erc/0/api/OAuthHealthCheck', verify=False)
            if res.status_code == 200:
                data = res.json()
                if data.get('HasProblem', True):
                    print("Integration has Problem", data)
                else:
                    print("Integration has OK", data)
            else:
                print("INTEGRATION TEST FAIL:", res.status_code)
        else:
            print("IDENT SERVICE INCOREECT CONFIG:")
            print(res.text)
    else:
        print("IDENTERVICE FAIL:", res.status_code)
