import pymongo
import config
import sys
import okta
import preempt
import logging

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

db_client = pymongo.MongoClient(config.db_connection)
db = db_client.get_database()
preempt_users = db[config.db_preempt_collection]
okta_users = db[config.db_okta_collection]

pipeline = [{
    "$match": {
        "status": "ACTIVE"  # We aren't going to update the riskScore for STAGED or PROVISIONED users
    }
}, {
    "$lookup": { # Join on the collection of preempt users
        "from": "preempt_users",
        "localField": "profile.login",
        "foreignField": "_id",
        "as": "preempt_data"
    }
}, {
    "$addFields": {
        "risk_score_from_preempt": {
            "$arrayElemAt": ["$preempt_data.riskScore", 0]
        }
    }
}, {
    "$project": {
        "preempt_data": 0
    }
}, {
    "$project": {
        "_id": 1,
        "profile": 1,
        "risk_score_from_preempt": 1,
        "diff": {
            "$subtract": ["$risk_score_from_preempt", "$profile.riskScore"] # use to determine if the riskScore has changed
        }
    }
}, {
    "$match": {
        "diff": {
            "$ne": 0
        }
    }
}, {
    "$match": {
        "risk_score_from_preempt": {
            "$exists": True
        }
    }
}]

while(True):
    preempt.refresh()
    okta.refresh()
    users_to_update = list(okta_users.aggregate(pipeline))
    logging.info("Updating the riskScore for " + str(len(users_to_update)) + " users.") 
    okta.update_users(users_to_update)
    logging.info("Finished updating riskScores.")

