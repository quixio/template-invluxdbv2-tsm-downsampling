# import Utility modules
import os
import ast
from datetime import datetime
import logging
from time import time

# import vendor-specific modules
from quixstreams import Application, State
from quixstreams import message_context

from influxdb_client import InfluxDBClient, Point

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# read the consumer group from config
consumer_group_name = os.environ.get("CONSUMER_GROUP_NAME", "influxdb-data-writer")

# read the timestamp column from config
timestamp_column = os.environ.get("TIMESTAMP_COLUMN", "")

# Create a Quix platform-specific application instead
app = Application(consumer_group=consumer_group_name, auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.getenv("input", "input-data"))

# Read the environment variable and convert it to a dictionary
tag_keys = ast.literal_eval(os.getenv("INFLUXDB_TAG_KEYS", "[]"))
field_keys = ast.literal_eval(os.getenv("INFLUXDB_FIELD_KEYS", "[]"))

# Read the environment variables for connecting to Influx
influx_bucket = os.getenv("INFLUXDB_BUCKET", "")
influx_org = os.getenv("INFLUXDB_ORG", "")
influx_host = os.getenv("INFLUXDB_HOST", "")
influx_token = os.getenv("INFLUXDB_TOKEN", "")

# check for some common potential startup issues
if influx_bucket == "" or influx_org == "" or influx_host == "" or influx_token == "":
    raise Exception("Incorrect InfluxDB v2 configuration")
if influx_host.startswith("http") or "http" in influx_host:
    raise Exception("Incorrect InfluxDB v2 HOST should be specified without the protocol. (https)")

# Initialize InfluxDB v2 client
influx2_client = InfluxDBClient(url=influx_host,
                                token=influx_token,
                                org=influx_org)

# Get the measurement name to write data to
measurement_name = os.environ.get("INFLUXDB_MEASUREMENT_NAME", "measurement1")

# Initialize a buffer for batching points and a timestamp for the last write
points_buffer = []
service_start_state = True
last_write_time_ns = int(time() * 1e9)  # Convert current time from seconds to nanoseconds

def send_data_to_influx(message: dict, state: State):
    global last_write_time_ns, points_buffer, service_start_state

    if timestamp_column == "":
        message_time_ns = (message_context().timestamp).milliseconds * 1000 * 1000
    else:
        message_time_ns = message[timestamp_column]

    try:
        # if the service just started, check for any state values to load.
        if service_start_state:
            # we only need this check on startup.
            service_start_state = False
            # load the points buffer from state right into the variable or supply a default.
            points_buffer = state.get("points_buffer", [])
            logger.info("Points buffer loaded from state.")

        # Initialize the tags and fields dictionaries
        tags = {}
        fields = {}

        # Iterate over the tag_dict and field_dict to populate tags and fields
        for tag_key in tag_keys:
            if tag_key in message:
                if message[tag_key] is not None:  # skip None values
                    tags[tag_key] = message[tag_key]

        for field_key in field_keys:
            if field_key in message:
                if message[field_key] is not None:  # skip None values
                    fields[field_key] = message[field_key]

        logger.debug(f"Using tag keys: {', '.join(tags.keys())}")
        logger.debug(f"Using field keys: {', '.join(fields.keys())}")

        # Check if fields dictionary is not empty
        if not fields and not tags:
            logger.debug("Fields and Tags are empty: No data to write to InfluxDB.")
            return  # Skip writing to InfluxDB
        
        # Create a new Point and add it to the buffer
        point = Point(measurement_name).time(message_time_ns)
        for tag_key, tag_value in tags.items():
            point.tag(tag_key, tag_value)
        for field_key, field_value in fields.items():
            point.field(field_key, field_value)
        points_buffer.append(point.to_line_protocol())

        # Check if it's time to write the batch
        if len(points_buffer) >= 10000 or int(time() * 1e9) - last_write_time_ns >= 15e9:  # 10k records have accumulated or 15 seconds have passed
            with influx2_client.write_api() as write_api:
                logger.info(f"Writing batch of {len(points_buffer)} points written to InfluxDB.")
                write_api.write(influx_bucket, influx_org, points_buffer)

            # Clear the buffer and update the last write time
            points_buffer = []
            last_write_time_ns = int(time() * 1e9)
        
        if len(points_buffer) > 0:
            # if there is anything in the buffer, store it to state.
            state.set("points_buffer", points_buffer)
        else:
            # if we just wrote to InfluxDb and the buffer is empty, delete the state.
            state.delete("points_buffer")

    except Exception as e:
        logger.info(f"{str(datetime.utcnow())}: Write failed")
        logger.info(e)

sdf = app.dataframe(input_topic)
sdf = sdf.update(send_data_to_influx, stateful=True)

if __name__ == "__main__":
    logger.info("Starting application")
    app.run(sdf)