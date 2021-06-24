import config
import logging
import requests

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

# Decorator to handle the response, and retrying the function (if needed).
def handle_response(func):
    logging.debug("handle_response decorator called "+func.__name__)
    def wrapper_handle_response(*args, **kwargs):
        logging.debug("wrapper_handle_response called "+func.__name__+" with "+str(args)+" and "+str(kwargs))
        logging.debug(func.__name__)
        try:
            r = func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            logging.exception("An exception occurred while running "+func.__name__+" with "+str(args)+" and "+str(kwargs)+" so we will wait 60 seconds and try again.")
            time.sleep(60)
            return wrapper_handle_response(*args, **kwargs)
        if (r.status_code - 400 >= 0):
            logging.error(str(r.status_code)+" response ("+r.reason+") when calling "+func.__name__+" with "+str(args)+" and "+str(kwargs))
            logging.error(r.text)
            logging.error(r.headers)
            if(r.status_code == 400):
                r.raise_for_status() # Stop the program if the request is bad, which should never happen.
            else:
                logging.error("We will wait 60 seconds and try again.")
                time.sleep(60)
                return wrapper_handle_response(*args, **kwargs)
        else:
            logging.debug("Good response when calling with "+str(args)+" and "+str(kwargs))
            return r

    return wrapper_handle_response
