import json
import requests
import pymongo
import config
import sys
import logging
import time
import sys
import datetime
import test_util
import preempt_rate_limit_util
import preempt_handle_response_util

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

db_client = pymongo.MongoClient(config.db_connection)
db = db_client.get_database()
preempt_users = db[config.db_preempt_collection]

# Get the Preempt query for a given cursor.
def get_preempt_query(cursor=None):
    part_one = '''
{
  entities(domains: "example.com",
    types: [USER]
    first: 1000
    '''
    part_two = '' if cursor is None else 'after: "'+cursor+'"'
    part_three = '''
    sortKey:RISK_SCORE
    sortOrder: DESCENDING
    enabled:true
    archived:false
    roles: [HumanUserAccountRole, ProgrammaticUserAccountRole]
  ){
    edges {
      cursor
      node {
        primaryDisplayName
        secondaryDisplayName
        riskScore
        archived
        roles {
          type
          fullPath
        }
        entityId
        accounts {
          ... on ActiveDirectoryAccountDescriptor {
            upn
            servicePrincipalNames
            objectSid
            objectGuid
            creationTime
            lastUpdateTime
            dataSource
            expirationTime
            lockoutTime
            description
            enabled
            mostRecentActivity
            title
          }
        }
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
'''
    return part_one + part_two + part_three

# Get the last cursor from the Preempt response data. 
def get_last_cursor(result):
    edges = result['entities']['edges']
    last_edge = edges[-1]
    last_cursor = last_edge['cursor']
    return last_cursor

# Get the hasNextPage value from the Preempt response data.
def has_more(result):
    return result['entities']['pageInfo']['hasNextPage']

# Loop through the Preempt response data (JSON), and insert each record
# using the UPN as the _id.
def insert_page_of_preempt_users(result):
    for i in result['entities']['edges']:
        risk_score = i['node']['riskScore']
        primary_display_name = i['node']['primaryDisplayName']
        secondary_display_name = i['node']['secondaryDisplayName']
        for j in i['node']['accounts']:
            if 'upn' in j and j['upn'] is not None:
                email = j['upn']
                new_doc = { "_id": email,
                            "riskScore":i['node']['riskScore'],
                            "primary_display_name": primary_display_name,
                            "secondary_display_name": secondary_display_name,
                            "insert_time": datetime.datetime.utcnow().strftime("%m/%d/%Y, %H:%M:%S"),
                            "full_node": i['node']}

                try:
                    preempt_users.insert_one(new_doc)

                # Occasionally, a duplicate will occur while in the middle of downloading the Preempt user info.
                # This occurs if a user's 'mostRecentActivity' field has recently  been updated in Preempt.
                # The correct thing to do is to simply replace the previous record with the new one.
                # These log statement could probably be changed to DEBUG but this happens rarely so 
                # I'd like to keep them an INFO for now.
                except pymongo.errors.DuplicateKeyError:
                    logging.info(f'Duplicate key(email) found.')
                    logging.info(json.dumps(i['node']))
                    logging.info(json.dumps(preempt_users.find_one({"_id":email})))
                    preempt_users.replace_one({"_id": email}, new_doc)
                except:
                    logging.exception("An error occurred when attempting to save info about a Preempt user.") #Prints stack trace.

# Get each page of Preempt users and call another function to insert them.
def insert_preempt_users():
    query = get_preempt_query()
    result = get_page_of_preempt_users(query).text
    data = json.loads(result)["data"]
    insert_page_of_preempt_users(data)

    while (has_more(data)):
        last_cursor = get_last_cursor(data)
        query = get_preempt_query(last_cursor) 
        result = get_page_of_preempt_users(query).text
        data = json.loads(result)["data"]
        insert_page_of_preempt_users(data)

# Make a request to get Preempt users, and return
@preempt_rate_limit_util.rate_limit
@preempt_handle_response_util.handle_response
@test_util.mock_network_server_failures
def get_page_of_preempt_users(query):
    headers = {'Content-Type':'application/json',
               'Authorization':'Bearer '+config.preempt_key}

    data = {"query": query}
    data_str = str(data).replace("\"","\\\"").replace("\'","\"") # Python uses single quotes in when converting a dict to string. We have to escape the existing double quotes, and replace the single quotes with double quotes for graphql

    r = requests.post('https://'+config.preempt_hostname+'/api/public/graphql', headers=headers, verify='/etc/pki/ca-trust/source/anchors/', data=data_str)

    return r

def drop_collection():
    preempt_users.drop()

# Drop the collection and recreate with the most recent data.
def refresh():
    logging.info("Refreshing collection of Preempt users.")
    drop_collection()
    insert_preempt_users()
    logging.info("Finished refreshing collection of Preempt users.")

