import config
import time
import logging 

logging.basicConfig(format='%(asctime)s %(process)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', level=config.log_level, filename=config.log_file)

RATE_LIMIT_FLOOR = config.preempt_rate_limit_floor if hasattr(config,'preempt_rate_limit_floor') else 90
rate_limit_limit = -1
rate_limit_remaining = -1

# Decorator to respect rate limiting header values
def rate_limit(func):
    logging.debug("rate_limit decorator called "+func.__name__)
    def wrapper_rate_limit(*args, **kwargs):
        logging.debug("wrapper_rate_limit called. "+func.__name__+" with "+str(args)+" and "+str(kwargs))
        wait_if_cant_proceed()
        val = func(*args, **kwargs)
        if (val is not None and hasattr(val,"headers")):
            set_rate_limit_data(val.headers)
        logging.debug("leaving wrapper_rate_limit")
        return val
    return wrapper_rate_limit


# Set the rate limit data based on the response headers.
def set_rate_limit_data(headers):
    global rate_limit_limit, rate_limit_remaining
    logging.debug(headers)
    rate_limit_limit = int(headers['X-RateLimit-Limit']) if 'X-RateLimit-Limit' in headers else -1
    rate_limit_remaining = int(headers['X-RateLimit-Remaining']) if 'X-RateLimit-Remaining' in headers else -1
    logging.debug("rate_limit_limit: "+str(rate_limit_limit)+", rate_limit_remaining: "+str(rate_limit_remaining))

# Oddly, Preempt does not supply an X-RateLimit-Reset header, however manual
# testing shows that it resets every 60 seconds.
def wait_until_reset():
    time.sleep(60)

# Wait if we have <= the lower bounds(floor) of requests remaining.
def wait_if_cant_proceed():
    logging.debug("rate_limit_limit: "+str(rate_limit_limit))
    if (rate_limit_limit != -1):
        warning_percent = ((100 - RATE_LIMIT_FLOOR)/100)
        logging.debug("warning_percent: "+str(warning_percent))
        lower_bounds = warning_percent * int(rate_limit_limit)
        logging.debug("lower_bounds: "+str(lower_bounds))
        logging.debug("rate_limit_remaining: "+str(rate_limit_remaining))

        if (rate_limit_remaining <= lower_bounds):
            wait_until_reset()


