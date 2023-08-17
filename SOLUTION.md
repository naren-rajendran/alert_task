# Solution - Video events management task

There are 3 tasks to be completed (refer [README.md](https://github.com/naren-rajendran/alert_task/blob/develop/README.md) for the description of the tasks),

- Ingestion
- Aggregation
- Alerts

## Ingestion

### Assumptions:
- Detection data for the ingestion will be ordered by time, arrives from the oldest to the newest data point.
- Detections may be sent every 30 seconds.
- Detection data may contain more than one data point (a batch)
- For the given task, assume that data comes from a single source.

### Solution:
Since it is assumed that detection data may contain more than one data point, it is efficient to store data in batches rather than saving one data point at a time.

The `detections` table schema (pseudo schema),

```
id PRIMARY KEY bigint NOT NULL,
detection_type VARCHAR NOT NULL INDEXED,
detection_group VARCHAT NOT NULL INDEXED,
detection_time TIMESTAMP NOT NULL INDEXED,
created_on TIMESTAMP NOT NULL
```
Detection types are of the following, `"pedestrian", "bicycle", "car", "truck", "van"`

and are grouped as,

`people = ["pedestrian", "bicyle"]`

`vehicles = ["car", "truck", "van"]`

Based on the description of the task, it is assumed that the system is going to be read heavy and so the group information is stored with every data point and it is not normalized to aid faster reads and joins.

## Aggregation

### Assumptions:
- Every data ingestion should be followed by aggregation of data points.
- Aggregation should include historical data and the new data points.
- Should be handled at the database level.

### Solution:

Aggregation should include historical data points and the new data points, which may be significantly large based on the age of data collection. Raw sql is preferred over ORM queries for performance reasons.

The aggregation should result in data grouped by detection group (people or vehicles) with detection times combined into 1 minute intervals. The query uses joins on the same table to combine data points to have a start and end time spanning no more than 60 seconds. The query used can be referred here, [query.txt](https://github.com/naren-rajendran/alert_task/blob/develop/src/query.txt)

Indexes are added to detection group and detection time to aid read performance.

The aggregation result from the database is transformed at the backend to the format expected.

### Alternatives and considerations
- A column to hold the `start_time` per record (detection data point) at the database table was considered. The value would be a timestamp from an earlier detection that is at most a minute (60 seconds) apart. This could be very efficient for reads (we could avoid table joins) but may be inefficient for writes to database, because write has to be performed on every data point individually, not by batches. Another potential problem with this approach is that if in the future interval has to be changed to say 5 minutes apart, entire table has to be updated.
- Views could be a way to handle this but it is not persisted and it would be similar to the raw sql performance that is implemented currently. Materialized view could be solution but it has to be refreshed at regular intervals to get the most recent data.
- Instead of aggregating historical data and new data on every ingestion, we could aggregate only once or twice a day or at a set interval. Or we could archive past data, say archive anything that is older than 30 or 60 days, which would make the query run much faster. Another idea would be to filter data points to include only the days data and only those will be aggregated upon every ingestion. The reference query (check above) attached shows how data can be filtered.

## Alerts

### Assumptions:
- Checks to raise alerts has to be performed every time data point(s) are ingested.
- This simulates real time alerts and may not need database access to check.
- Raise alert only when the detection type is of group `people`

### Solution:

A simple global queue of fixed length (q) is maintained matching the number of consecutive occurrence (n) to be checked, and upon detection data point arrival (ingestion), the queue is populated. We simply check if
the queue is full and has the same type (we assume data points arrive in order by time) upon a data point arrival and raise the alert. We only alert when the group type is `people` (I assumed it is people because the requirement stated `person`, the closest I could match it to is either `pedestrian` (the type of detection) or `people`(the group), I chose `people` as it had the closest meaning).

## Note:

- Run the solution using `./run.sh`.
- Basic `print` is used to log results and information to the standard ouptut. No logging library/module is used.
- The solution simulates detection point(s) arrival at various times separated by atleast few minutes and hard stops after 10 instances of data ingestion.

