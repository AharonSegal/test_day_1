from confluent_kafka import Consumer
from logger import log_event


class KafkaConsumerClient:

    def __init__(self, bootstrap_servers):
        self.consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "auto.offset.reset": "earliest"
        })
        self.log_event = log_event

    def subscribe(self, topics):
        if isinstance(topics, str):
            topics = [topics]
        self.consumer.subscribe(topics)
        self.log_event("INFO", "subscribed to kafka topics", {"topics": topics})

    def get_raw_message(self):
        # returns raw message bytes 
        while True:
            kafka_message = self.consumer.poll(5)
            if kafka_message is None:
                continue
            if kafka_message.error():
                self.log_event("ERROR", "kafka poll error", {"error": str(kafka_message.error())})
                continue
            raw_bytes = kafka_message.value()
            if not raw_bytes:
                continue
            return raw_bytes

    def close(self):
        self.consumer.close()
