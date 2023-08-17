import random
from datetime import datetime, timedelta

MAX_DETECTIONS_SIZE = 10


def get_datetime(s: int) -> str:
    d = datetime.now().replace(microsecond=0) + timedelta(seconds=s)
    return d.isoformat()


def get_random_value(my_list: list) -> str:
    if len(my_list) > 0:
        return random.choice(my_list)
    else:
        return ""


def generate_detections(detection_types: list, forward_in_secs: int) -> list[tuple[str, str]]:
    detections = list()
    if len(detection_types) > 0:
        max = random.randint(1, MAX_DETECTIONS_SIZE)
        for x in range(0, max):
            increase_seconds_by = x + forward_in_secs
            detection_type = get_random_value(detection_types)
            detection_time = get_datetime(increase_seconds_by)
            d = (detection_type, detection_time)
            detections.append(d)

    return detections
