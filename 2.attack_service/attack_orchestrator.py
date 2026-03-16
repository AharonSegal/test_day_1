"""
consumes attack messages from kafka, validates them, stores to mysql, and marks entity as attacked
gets: raw bytes from kafka topic 'attack'
gives: validated attack records to mysql attack table, entity attacked flag updated in entities table,
       invalid messages to kafka topic intel_signals_dlq
"""

"""
flow:
    1. subscribe to the kafka 'attack' topic and start the consumer loop
    2. get_raw_message() returns raw bytes
    3. parse_message() tries json.loads - failure sends to dlq and continues
    4. validate all 3 required fields are present - missing field sends to dlq
    5. look up entity_id in the entities table:
         - not found:  no intel on this entity - send to dlq
         - destroyed:  already destroyed - send to dlq
         - active:     insert attack record, mark entity attacked = TRUE
    6. log success
"""
print("starting attack service")

import json
from attack_config import AttackConfig
from connections.kafka_consumer import KafkaConsumerClient
from connections.kafka_publisher import KafkaPublisher
from connections.mysql_connection import MySQLClient
from connections.logger import log_event


REQUIRED_FIELDS = [
    "attack_id", "entity_id", "weapon_type"
]


class AttackOrchestrator:

    def __init__(self, kafka_consumer, dlq_publisher, mysql, attack_topic):
        self.kafka_consumer = kafka_consumer
        self.dlq_publisher  = dlq_publisher
        self.mysql          = mysql
        self.attack_topic   = attack_topic

    # the function that publishes the errors
    def send_to_dlq(self, raw_bytes, error):
        self.dlq_publisher.publish({
            "source_topic": self.dlq_publisher.topic_name,
            "raw":          raw_bytes.decode("utf-8", errors="replace"),
            "error":        error
        })
        log_event("ERROR", "attack message rejected", {"error": error})
        print("error logged : ", error)

    def get_entity(self, entity_id):
        # returns entity row as dict or None if not found
        row = self.mysql.fetch_one(
            "SELECT entity_id, damage_state "
            "FROM entities WHERE entity_id = %s",
            (entity_id,)
        )
        if row is None:
            return None
        return {"entity_id": row[0], "damage_state": row[1]}

    def insert_attack(self, message):
        # stores the processed attack record
        self.mysql.execute(
            "INSERT INTO attack (attack_id, timestamp, entity_id, weapon_type) "
            "VALUES (%s, %s, %s, %s)",
            (
                message["attack_id"],
                message["timestamp"],
                message["entity_id"],
                message["weapon_type"],
            )
        )

    def mark_entity_attacked(self, entity_id):
        # flags the entity as having been attacked
        self.mysql.execute(
            "UPDATE entities SET attacked = TRUE WHERE entity_id = %s",
            (entity_id,)
        )

    def process(self, message):
        print("-- START MESSAGE -> : ", message, " <- : END MESSAGE---")
        entity_id = message["entity_id"]

        existing = self.get_entity(entity_id)

        if existing is None:
            # no intel on this entity - cannot attack unknown target
            return f"entity {entity_id} not found in intel"

        elif existing["damage_state"] == "destroyed":
            # already destroyed - ghost attack order
            return f"entity {entity_id} is already destroyed"

        # known active entity - record the attack
        self.insert_attack(message)
        self.mark_entity_attacked(entity_id)
        log_event("INFO", "attack recorded", {
            "entity_id":   entity_id,
            "weapon_type": message["weapon_type"],
        })
        return None

    def start(self):
        print("++++++++ starting the loop ++++++++")
        self.kafka_consumer.subscribe(self.attack_topic)
        log_event("INFO", "attack_service started, waiting for messages")

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

config = AttackConfig()

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

orchestrator = AttackOrchestrator(kafka_consumer, dlq_publisher, mysql, config.KAFKA_ATTACK_TOPIC)
