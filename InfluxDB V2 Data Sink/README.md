# InfluxDB v2 Sink
A service that continuously listens to an Kafka topic and writes new data to your chosen InfluxDB v2 bucket while only including your chosen tags and fields.

The **InfluxDB v2 Sink** service requires the following environment variables to be set:

| Variable   |      Description      |  Example |
|----------|---------------------------------------|------|
| `input`          |  The input topic from which to pull the InfluxDB V2 data.  | `influxv2-data` |
| `INFLUXDB_ORG`   |  The configured organization in the InfluxDB v2 instance.  | `AcmeInc` |
| `INFLUXDB_HOST`  | The address of the InfluxDB v2 Serverless Cloud instance.  | `us-east-1-2.aws.cloud2.influxdata.com` |
| `INFLUXDB_BUCKET`| The name of the InfluxDB bucket to store the migrated data. |  `machine-telemetry-v2` |
| `INFLUXDB_TOKEN` | The influxDB access token (defined as a secret in Quix).  |   `Rm3545345357qnv-gOX54346346EHr-g1YSB79T29w_5VdwEuXWK6gg535g34232yDX_VAYfA33RFd4Xw==` |
| `INFLUXDB_TAG_KEYS` | A list of tags to look for in the migrated data (all others will be ignored). |  `['machineID','barcode','provider']` |
| `INFLUXDB_FIELD_KEYS` | A list of fields to look for in the migrated data (all others will be ignored).  |  `['temperature','load','power','vibration']` |
| `CONSUMER_GROUP_NAME` | The name of the Kafka consumer group (usually only needs to be changed when testing) | `influxv2-reader` |
