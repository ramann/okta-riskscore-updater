import config
import logging
import random
import requests

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

# This is used to mock network and server failures, to test that the program responds gracefully.
def mock_network_server_failures(func):
    logging.debug("mock_network_server_failures decorator called "+func.__name__)
    def wrapper_mock_network_server_failures(*args, **kwargs):
        logging.debug("wrapper_mock_network_server_failures called. "+func.__name__+" with "+str(args)+" and "+str(kwargs))
        mock_failure_occurred = False
        r = None
        # Use to test handling of random network failure
        if (config.mock_network_failures if hasattr(config,"mock_network_failures") else False):
            rand_int = random.randint(0,9)
            logging.debug("Testing random network failures. rand_int: "+str(rand_int))
            if (rand_int >= 7):
                mock_failure_occurred = True
                raise requests.exceptions.RequestException() from None

        # Use to test handling of random server-side errors
        if (config.mock_server_failures if hasattr(config,"mock_server_failures") else False):
            rand_int = random.randint(0,9)
            logging.debug("Testing random server failures. rand_int: "+str(rand_int))
            if(rand_int >= 7):
                mock_failure_occurred = True
                r = requests.Response()
                r.status_code=500
                r.reason="Testing Internal Server Error"
                r.headers={"test_header": "Testing server failure"}

        if (not mock_failure_occurred):
            r = func(*args, **kwargs)

        logging.debug("leaving wrapper_mock_network_server_failures")
        return r
    return wrapper_mock_network_server_failures

