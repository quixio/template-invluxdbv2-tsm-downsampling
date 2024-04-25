# import Utility modules
import os
import ast
import datetime
import logging

# import vendor-specific modules
from quixstreams import Application
from influxdb_client_3 import InfluxDBClient3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
consumer_group_name = os.environ.get('CONSUMER_GROUP_NAME', "influxdb-data-writer")

app = Application(consumer_group=consumer_group_name,
                       auto_offset_reset="earliest")

# Create the input topic object, this uses json serialization by default.
input_topic = app.topic(os.environ["input"])

# Read the environment variable and convert it to a dictionary
tag_keys = ast.literal_eval(os.environ.get('INFLUXDB_TAG_KEYS', "[]"))
field_keys = ast.literal_eval(os.environ.get('INFLUXDB_FIELD_KEYS', "[]"))

# Read the environment variable for the field(s) to get.
# For multiple fields, use a list "['field1','field2']"
                                           
influx3_client = InfluxDBClient3(token=os.environ["INFLUXDB_TOKEN"],
                         host=os.environ["INFLUXDB_HOST"],
                         org=os.environ["INFLUXDB_ORG"],
                         database=os.environ["INFLUXDB_DATABASE"])

def send_data_to_influx(message):
    logger.info(f"Processing message: {message}")
    try:
        # Uses the current time as the timestamp for writing to the sink
        # Adjust to use an alternative timestamp if necesssary,

        writetime = datetime.datetime.utcnow()
        writetime = writetime.isoformat(timespec='milliseconds') + 'Z'
        
        measurement_name = message['_measurement']

        # Initialize the tags and fields dictionaries
        tags = {}
        fields = {}

        # Iterate over the tag_dict and field_dict to populate tags and fields
        for tag_key in tag_keys:
            if tag_key in message:
                tags[tag_key] = message[tag_key]

        for field_key in field_keys:
            if field_key in message:
                fields[field_key] = message[field_key]

        logger.info(f"Using tag keys: {', '.join(tags.keys())}")
        logger.info(f"Using field keys: {', '.join(fields.keys())}")

        # Construct the points dictionary
        points = {
            "measurement": measurement_name,
            "tags": tags,
            "fields": fields,
            "time": writetime
        }

        influx3_client.write(record=points, write_precision="ms")
        
        print(f"{str(datetime.datetime.utcnow())}: Persisted ponts to influx: {points}")
    except Exception as e:
        print(f"{str(datetime.datetime.utcnow())}: Write failed")
        print(e)

sdf = app.dataframe(input_topic)
sdf = sdf.update(send_data_to_influx)

if __name__ == "__main__":
    print("Starting application")
    app.run(sdf)
