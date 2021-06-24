import config
import time
import logging

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

RATE_LIMIT_WARNING_THRESHOLD = config.okta_rate_limit_warning if hasattr(config, 'okta_rate_limit_warning') else 90
RATE_LIMIT_BUFFER = config.okta_rate_limit_buffer if hasattr(config, 'okta_rate_limit_buffer') else 2

# These correspond to the three rate limit response headers.
okta_rate_limit = -1
okta_rate_limit_remaining = -1
okta_rate_limit_reset = -1

# Decorator to respect rate limiting header values
def rate_limit(func):
    logging.debug("rate_limit decorator called "+func.__name__)
    def wrapper_rate_limit(*args, **kwargs):
        logging.debug("wrapper_rate_limit called. "+func.__name__+" with "+str(args)+" and "+str(kwargs))
        wait_if_cant_proceed()
        val = func(*args, **kwargs)
        logging.debug("finished calling function from within rate_limit decorator :"+str(val))
        if (val is not None):
            set_okta_rate_limit_data(val.headers)
        logging.debug("leaving wrapper_rate_limit")
        return val
    return wrapper_rate_limit

# Stay in function until the rate limit reset time has been reached.
def wait_until_reset():
    now = time.time()
    while (now < okta_rate_limit_reset):
        logging.debug("current time: "+str(now)+
                ", okta_rate_limit_reset: "+str(okta_rate_limit_reset))
        time.sleep(1)
        now = time.time()


def wait_if_cant_proceed():
    logging.debug("okta_rate_limit: "+str(okta_rate_limit))
    if (okta_rate_limit != -1):
        warning_percent = ((100 - RATE_LIMIT_WARNING_THRESHOLD + RATE_LIMIT_BUFFER)/100)
        lower_bounds = warning_percent * int(okta_rate_limit)
        logging.debug("warning_percent: "+str(warning_percent)+
                ", lower_bounds: "+str(lower_bounds)+
                ", okta_rate_limit_remaining: "+str(okta_rate_limit_remaining))

        if (okta_rate_limit_remaining <= lower_bounds):
            wait_until_reset()

# Set the rate limit variables based on applicable header values.
def set_okta_rate_limit_data(headers):
    global okta_rate_limit, okta_rate_limit_remaining, okta_rate_limit_reset
    okta_rate_limit = int(headers['X-Rate-Limit-Limit'])
    okta_rate_limit_remaining = int(headers['X-Rate-Limit-Remaining'])
    okta_rate_limit_reset = int(headers['X-Rate-Limit-Reset'])
    logging.debug("okta_rate_limit: "+str(okta_rate_limit)+
            ", okta_rate_limit_remaining: "+str(okta_rate_limit_remaining)+
            ", okta_rate_limit_reset: "+str(okta_rate_limit_reset))
