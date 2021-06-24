import json
import jwt
import datetime
import requests
import config
import okta_rate_limit_util
import okta_handle_response_util
import logging
import test_util

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

access_token = None

def set_access_token():
    global access_token
    access_token = json.loads(get_new_access_token().text)
    logging.debug('The access token has been set to: ' + str(access_token))

def get_access_token():
    global access_token
    if (access_token is None):
        set_access_token()
    logging.debug('Returning access token: ' + str(access_token))
    return access_token

# Create a new JWT that is immediatedly used to get a new access token
def get_jwt(filename):
    private_key_file = open(filename,'r')
    private_key = private_key_file.read()
    private_key_file.close()

    claims = { "aud": "https://"+config.okta_hostname+"/oauth2/v1/token", 
            "iss": config.okta_client_id, 
            "sub": config.okta_client_id, 
            "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=5) }

    encoded = jwt.encode(claims, private_key, algorithm="RS256")
    return encoded

# Returns the JSON access token from the OAuth token endpoint
@okta_rate_limit_util.rate_limit
@okta_handle_response_util.handle_response
@test_util.mock_network_server_failures
def get_new_access_token():
    jwt = get_jwt(config.okta_jwk_pem)

    headers = {'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded' }
    data = {'grant_type': 'client_credentials',
            'scope': 'okta.users.read okta.users.manage',
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': jwt}
    r = requests.post('https://'+config.okta_hostname+'/oauth2/v1/token', headers=headers, data=data)
    return r
