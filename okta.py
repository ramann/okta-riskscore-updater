import json
import requests
import pymongo
import config
import time
import logging 
import okta_auth
import sys
import test_util
import okta_rate_limit_util
import okta_handle_response_util

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

db_client = pymongo.MongoClient(config.db_connection)
db = db_client.get_database()
okta_users = db[config.db_okta_collection]

# Returns true if there is a next 'link' header.
def okta_has_more(r):
    for link in r.headers['link'].split(','):
        if (link.endswith(' rel="next"')):
            return True

    return False

# Return text with prefix removed.
def remove_prefix(text, prefix):
    ret = text
    if text.startswith(prefix):
        ret = text[len(prefix):]
    return ret

# Return text with suffix removed.
def remove_suffix(text, suffix):
    ret = text
    if text.endswith(suffix):
        ret = text[:-len(suffix)]
    return ret

# Returns the link to the next Okta page
def okta_get_next_link(r):
    for link in r.headers['link'].split(','):
        link = link.strip()
        if (link.endswith(' rel="next"')):
            return remove_suffix(remove_prefix(link, '<'),'>; rel="next"')

def get_headers():
    return {'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization':'Bearer ' + okta_auth.get_access_token()['access_token'] }

# Make a request to update the given user's riskScore.
#@handle_response
@okta_rate_limit_util.rate_limit
@okta_handle_response_util.handle_response
@test_util.mock_network_server_failures
def update_user(user):
    logging.debug("entered update_user()")
    okta_risk_score = user['profile']['riskScore'] if 'riskScore' in user['profile'] else 'not set'
    preempt_risk_score = user['risk_score_from_preempt']
    logging.info("Updating user: '"+user['profile']['login']+"'`s riskScore ("+str(okta_risk_score)+" in Okta) with "+str(preempt_risk_score)+" from Preempt.")
    logging.debug("Updating user: "+str(user))
    user_profile={"profile":
                    {"riskScore": preempt_risk_score}
                }

    r = requests.post('https://'+config.okta_hostname+'/api/v1/users/'+user['_id'], headers=get_headers(), json=user_profile)
    logging.debug("exiting update_user()")
    return r

# Loop through users, make a call to update each one.
def update_users(users):
    for user in users:
        update_user(user)

# Make a request to Okta
@okta_rate_limit_util.rate_limit
@okta_handle_response_util.handle_response
@test_util.mock_network_server_failures
def get_okta_page(url_path):
    logging.debug("entered get_okta_page("+url_path+")")

    r = requests.get(url_path, headers=get_headers())

    logging.debug("leaving get_okta_page("+url_path+")")
    return r

# Parse a response and insert the users into the db.
def insert_page_of_okta_users(r):
    logging.debug("Inserting page of "+str(len(r.text))+" users.")
    for user in json.loads(r.text):
        user['_id'] = user['id']
        user.pop('id')
        try:
            okta_users.insert_one(user)
        except pymongo.errors.DuplicateKeyError:
            logging.error(f'Duplicate key('+user['_id']+') found when attempting to insert.')

# Insert all of the Okta users (no filter).
def insert_okta_users():
    r = get_okta_page('https://'+config.okta_hostname+'/api/v1/users')
    if (r is not None):
        insert_page_of_okta_users(r)

    while(okta_has_more(r)):
        r = get_okta_page(okta_get_next_link(r))
        if (r is not None):
            insert_page_of_okta_users(r)

# Drop the collection.
def drop_collection():
    okta_users.drop()

# Drop the collection and recreate with the most recent data.
def refresh():
    logging.info("Refreshing collection of Okta users.")
    drop_collection()
    insert_okta_users()
    logging.info("Finished refreshing collection of Okta users.")

