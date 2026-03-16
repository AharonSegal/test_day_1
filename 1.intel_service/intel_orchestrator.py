"""
consumes intel signals from kafka, validates them, enriches with movement distance, and stores to mysql
gets: raw bytes from kafka topic 'intel'
gives: validated intel records to mysql intel table, entity state updates to entities table,
       invalid messages to kafka topic intel_signals_dlq
"""

"""
flow:
    1. subscribe to the kafka 'intel' topic and start the consumer loop
    2. get_raw_message() returns raw bytes
    3. parse_message() tries json.loads - failure sends to dlq and continues
    4. validate all 4 required fields are present - missing field sends to dlq
    5. look up entity_id in the entities table:
         - not found:  first sighting - set priority_level = 99, distance = 0, insert entity row
         - destroyed:  ghost signal - send to dlq
         - active:     calculate haversine distance from last known position, update entity row
    6. insert intel signal into intel table
    7. log success
"""
print("starting intel service")

import json
from intel_config import IntelConfig
from connections.kafka_consumer import KafkaConsumerClient
from connections.kafka_publisher import KafkaPublisher
from connections.mysql_connection import MySQLClient
from connections.logger import log_event
from haversine import haversine_km


REQUIRED_FIELDS = [
    "signal_id", "entity_id",
    "reported_lat", "reported_lon"
]


class IntelOrchestrator:

    def __init__(self, kafka_consumer, dlq_publisher, mysql, intel_topic):
        self.kafka_consumer = kafka_consumer
        self.dlq_publisher  = dlq_publisher
        self.mysql          = mysql
        self.intel_topic    = intel_topic

    # the function that publishes the errors
    def send_to_dlq(self, raw_bytes, error):
        self.dlq_publisher.publish({
            "source_topic": self.dlq_publisher.topic_dlq,
            "raw":          raw_bytes.decode("utf-8", errors="replace"),
            "error":        error
        })
        log_event("ERROR", "intel message rejected", {"error": error})
        print("error logged : ", error)

    def get_entity(self, entity_id):
        # returns entity row as dict or None if not found
        row = self.mysql.fetch_one(
            "SELECT entity_id, last_lat, last_lon, damage_state "
            "FROM entities WHERE entity_id = %s",
            (entity_id,)
        )
        if row is None:
            return None
        return {"entity_id": row[0], "last_lat": row[1], "last_lon": row[2], "damage_state": row[3]}

    def insert_entity(self, entity_id, timestamp, lat, lon):
        # creates entity row on first sighting - dist_last is 0 on creation
        self.mysql.execute(
            "INSERT INTO entities (entity_id, time_last, last_lat, last_lon, dist_last) "
            "VALUES (%s, %s, %s, %s, 0.0)",
            (entity_id, timestamp, lat, lon)
        )

    def update_entity(self, entity_id, timestamp, lat, lon, distance_km):
        # updates position, timestamp, and movement distance for returning entity
        self.mysql.execute(
            "UPDATE entities SET time_last = %s, last_lat = %s, last_lon = %s, dist_last = %s "
            "WHERE entity_id = %s",
            (timestamp, lat, lon, distance_km, entity_id)
        )

    def insert_intel(self, message):
        # stores the processed intel signal
        self.mysql.execute(
            "INSERT INTO intel "
            "(signal_id, timestamp, entity_id, reported_lat, reported_lon, signal_type, priority_level) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                message["signal_id"],
                message["timestamp"],
                message["entity_id"],
                message["reported_lat"],
                message["reported_lon"],
                message["signal_type"],
                message["priority_level"],
            )
        )

    def process(self, message):
        print("-- START MESSAGE -> : ",message," <- : END MESSAGE---")
        entity_id    = message["entity_id"]
        reported_lat = message["reported_lat"]
        reported_lon = message["reported_lon"]

        existing = self.get_entity(entity_id)

        if existing is None:
            # first sighting - assign priority 99
            message["priority_level"] = 99
            self.insert_entity(entity_id, message["timestamp"], reported_lat, reported_lon)
            distance_km = 0.0

        elif existing["damage_state"] == "destroyed":
            # target already confirmed destroyed
            return f"entity {entity_id} is already destroyed"

        else:
            # known active entity - calculate movement since last sighting
            distance_km = round(
                haversine_km(existing["last_lat"], existing["last_lon"], reported_lat, reported_lon),
                4
            )
            self.update_entity(entity_id, message["timestamp"], reported_lat, reported_lon, distance_km)

        self.insert_intel(message)
        log_event("INFO", "intel signal processed", {
            "entity_id":   entity_id,
            "signal_type": message["signal_type"],
            "distance_km": distance_km
        })
        return None

    def start(self):
        print("++++++++ starting the loop ++++++++")
        self.kafka_consumer.subscribe(self.intel_topic)
        log_event("INFO", "intel_service started, waiting for messages")

        while True:
            raw_bytes = self.kafka_consumer.get_raw_message()

            # step 1: parse json
            error = None  
            try:
                message = json.loads(raw_bytes)
            except Exception:
                error = "broken json - could not parse message"
            if error:
                self.send_to_dlq(raw_bytes, error)
                continue

            # step 2: validate required fields
            missing = None  
            for field in REQUIRED_FIELDS:
                if field not in message:
                    missing = field
                    break
            if missing:
                self.send_to_dlq(raw_bytes, f"missing required field: {missing}")
                continue

            # step 3: process the validated message
            rejection_reason = self.process(message)
            if rejection_reason:
                self.send_to_dlq(raw_bytes, rejection_reason)


# ------------------------------------------------------------
# wiring - assembles all components
# ------------------------------------------------------------

config = IntelConfig()

kafka_consumer = KafkaConsumerClient(
    bootstrap_servers=config.KAFKA_BOOTSTRAP,
)

dlq_publisher = KafkaPublisher(
    bootstrap_servers=config.KAFKA_BOOTSTRAP,
    topic_name=config.KAFKA_DLQ_TOPIC,
)

mysql = MySQLClient(
    host=config.MYSQL_HOST,
    port=config.MYSQL_PORT,
    user=config.MYSQL_USER,
    password=config.MYSQL_PASSWORD,
    database=config.MYSQL_DATABASE
)

orchestrator = IntelOrchestrator(kafka_consumer, dlq_publisher, mysql, config.KAFKA_INTEL_TOPIC)
