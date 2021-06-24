# Okta RiskScore Updater

## Purpose
This software is intended to update a user's "riskScore" in Okta with the value pulled from Preempt. 

## Technologies
 - This software was implemented with Python 3 and MongoDB - the latest versions of each which were available in the Amazon Linux 2 package repos as of May 2021.
 - API calls are made via Python's requests library to both Preempt and Okta.
    - Auth to Preempt uses an API token (which is all that Preempt has available).
    - Auth to Okta is done using scoped OAuth 2.0 access tokens with the Client Credentials grant flow.

## Flow
The flow of this program is pretty simple:
 1. Get the users from Preempt and stick them in a Mongo collection.
 2. Get the users from Okta and stick them in an other Mongo collection.
 3. Join the two collections
    - On the Preempt side, use the 'upn' value
    - On the Okta side, use the user profile's 'login' value
 4. Find the users with a difference in their riskScore between the two collections, and update these users in Okta.
 5. Repeat

## Configuration
 - This program requires a config.py file containing key=value pairs for the following keys:
   - db_connection - the MongoDB connection string
   - db_preempt_collection - name of the Mongo collection of Preempt user
   - db_okta_collection - name of the Mongo collection of Okta users
   - preempt_hostname
   - okta_hostname
   - okta_client_id
   - okta_jwk_pem - path to the JWK pem file
   - preempt_key 
   - log_file
   - log_level ("DEBUG", "INFO", etc)

 - The following keys are optional
   - mock_network_failures (defaults to False)
   - mock_server_failures (defaults to False)
   - okta_rate_limit_warning (the percentage of API calls at which Okta warns about rate limiting; defaults to 90)
   - okta_rate_limit_buffer (the percentage of API calls that we want to have as a buffer before the okta_rate_limit_warning is reached; defaults to 2, which effectively means the program will back off at 88%)
   - preempt_rate_limit_floor (the percentage of API calls at which the program backs off; defaults to 90)

## Implementation Notes
 - Preempt's API uses GraphQL, however the Python 'gql' library does not support rate limiting, so the API calls were implemented using the 'requests' library.
 - The Preempt query
 - Preempt's documentation does not mention rate limiting, though they do include a couple rate-limiting response headers. Oddly, they don't include a reset header, however, testing shows the limit is 6000 requests every 60 seconds.
 - Okta has a Python SDK available, however their rate limiting strategy is simply to retry on a 429 response. There is no taking into account the rate limit warning setting. Additionally, they use the "PUT" method to update a user, which requires the all user info to be sent. So, the calls to Okta were also implemented using the 'requests' library.
 - The only case where the rate limit could be reached (for either Okta or Preempt) would be if there were other clients making requests and caused the rate limit remaining value to go to zero. This is why there is a configurable buffer value for the Okta API (implement this in Preempt!).
 - Both the Preempt and Okta API calls are performed synchronously because the cursor value must be used from the previous request for pagination to work. It might be possible to pull the data from both Preempt and Okta simultaneously, however this is probably not worth it.
 - Decorators are used for rate limiting, response handling, and testing resiliency when encountering network or server errors.

### Notes on the Preempt query
 - It is possible for a user account to have "archived:true" and "enabled:true". It is also possible for a user account to have "archived:false" and "enabled:false". So, we only return those who have "enabled:true" and "archived:false". 
 - We have to allow "ProgrammaticUserAccountRole" to include some human accounts. Unfortunately this also returns service accounts.

### File descriptions
 - main.py - the main loop, also joins Preempt and Okta datasets to determine which Okta user riskScore need to be updated
 - config.py - module containing different config options (see "Configuration" above)
 - preempt.py - responsible for making requests to the Preempt API endpoint to get all applicable users and storing the data locally
 - okta.py - responsible for making requests to the Okta API endpoint to get all users, storing the data locally, and making the requests to update users riskScores
 - okta_auth.py - responsible for getting a new Okta access token and storing in a global variable
 - okta_handle_response_util.py - handles the response for calls to Okta, stops the program on 400 response, gets a new token on 401 response, waits 60 seconds and trys again on server/network problems
 - preempt_handle_response_util.py - handles the response for calls to Okta, stops the program on 400 response, waits 60 seconds and trys again on server/network problems
 - okta_rate_limit_util.py - handles Okta's rate limit headers and applicable config options
 - preempt_rate_limit_util.py - handles Preempt's rate limit headers and applicable config options
 - test_util.py - test random network/server problems 

## TODO
 - Align with style guide standards, PEP-8
 - I feel like the logging statements at the top of each file _might_ be able to be consolidated, not sure how decorators affect this. Will want to do this before implementing logic for a default log_level value.

