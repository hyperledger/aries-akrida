import os
import random

from locust import between

min_wait = float(os.getenv("LOCUST_MIN_WAIT", 0.1))
max_wait = float(os.getenv("LOCUST_MAX_WAIT", 1))

standard_wait = between(min_wait, max_wait)


# Equivalent to locust.between
def deviation_wait() -> float:
    return random.uniform(min_wait, max_wait)
