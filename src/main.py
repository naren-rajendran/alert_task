from sqlalchemy import Column, BigInteger, String, DateTime, create_engine, text, Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import URL
from datetime import datetime
from collections import deque
from helper import generate_detections

import time

DETECTION_GROUP_INTERVAL = 60
CONSECUTIVE_DETECTIONS_ALERT = 5

DETECTION_TYPES = ["pedestrian", "bicycle", "car", "truck", "van"]
GROUP_PEOPLE = ["pedestrian", "bicycle"]
GROUP_VEHICLES = ["car", "truck", "van"]

Base = declarative_base()
Detection_Queue = deque([], maxlen=CONSECUTIVE_DETECTIONS_ALERT)

def get_engine() -> Engine:
    url = URL.create(
        drivername="postgresql",
        username="postgres",
        password="postgres",
        host="postgres",
        port="5432",
        database="postgres"
    )

    engine = create_engine(url)
    return engine

def get_db_session(engine: Engine) -> str:
    Session = sessionmaker(bind=engine)
    session = Session()
    return session

def get_detection_group(detection_type: str) -> str:
    if detection_type in GROUP_PEOPLE:
        return "people"
    else:
        return "vehicles"

class Detection(Base):
    __tablename__ = 'detections'

    id = Column(BigInteger(), primary_key=True)
    detection_type = Column(String(100), index=True, nullable=False)
    detection_group = Column(String(100), index=True, nullable=False)
    detection_time = Column(DateTime(timezone=True), index=True, nullable=False)
    created_on = Column(DateTime(timezone=True), default=datetime.now)


def ingest_data(session, detections: list[tuple[str, str]]) -> None:
    if detections is None:
        return
    
    try:
        session.bulk_insert_mappings(
            Detection,
            [
                dict(detection_type=n, detection_time=t,
                    detection_group=get_detection_group(n))
                for n, t in detections
            ]
        )
    except:
        session.rollback()
        print(f'ERROR writing detections to database {datetime.now().isoformat()}\n')
    else:
        session.commit()
    finally:
        # closing session because in real life scenario, ingestion data arrives every 30 seconds
        # we do not want to hold the session for a long time
        session.close()


def transform_aggregated_row(result: dict, row: dict) -> dict:
    grp = row["detection_group"]
    start_time = row["start_time"].isoformat()
    end_time = row["end_time"].isoformat()
    if grp not in result.keys():
        result[grp] = list()
    result[grp].append((start_time, end_time))

    return result


def aggregate_detections(engine: Engine) -> dict[str, list[tuple[str, str]]]:
    aggregated = dict()

    with engine.connect() as conn:
        with conn.execution_options(stream_results=True, max_row_buffer=100).execute(
            text("""
                    with t AS
                        (select l.detection_group, min(r.detection_time) as start_time, l.detection_time as end_time
                        from detections l 
                        left join detections r on l.detection_group = r.detection_group
                        where EXTRACT(EPOCH FROM (l.detection_time::timestamp - r.detection_time::timestamp)) between 0 and
                        """ + str(DETECTION_GROUP_INTERVAL) + """
                        group by l.detection_group, l.detection_time) 

                        select t.detection_group, t.start_time, max(t.end_time) as end_time from t where t.start_time is not null
                        group by t.detection_group, t.start_time
                        order by t.detection_group, t.start_time
                """)
        ) as result:
            for row in result:
                d = row._asdict()
                transform_aggregated_row(aggregated, d)

    return aggregated

def alert_consecutive_detections(detections: list[tuple[str, str]]) -> None:
    if detections is None:
        return
    
    max_occurence = CONSECUTIVE_DETECTIONS_ALERT
    
    for type, timestamp in detections:
        Detection_Queue.append(type)
        # alert only if the type is 'people'
        if Detection_Queue.count(type) == max_occurence and type in GROUP_PEOPLE:
            print(f'Alert {type} was detected {max_occurence} times consecutively, last detected {timestamp}\n')
            Detection_Queue.clear()


def main():
    simulation_counter = 10

    # init db
    engine = get_engine()
    Base.metadata.create_all(engine)

    # simple simulator - simulates data feed arrival from different points in time separated by,
    # 60 seconds on each iteration and the processing stops after 10 data ingestion since this is
    # a simulation
    while simulation_counter > 0:
        print(f'ingesting data {datetime.now().isoformat()}\n')

        # ingest_date
        session = get_db_session(engine)
        forward_secs = 60 * simulation_counter
        detections = generate_detections(DETECTION_TYPES, forward_secs)
        ingest_data(session, detections)

        # aggregate_detections
        agg_result = aggregate_detections(engine)
        print(f'aggregated result\n{agg_result}')

        # alert
        alert_consecutive_detections(detections)

        simulation_counter -= 1


if __name__ == "__main__":
    main()
