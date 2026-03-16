import json
from confluent_kafka import Producer
from connections.logger import log_event

print("in publisher")


class KafkaPublisher:

    def __init__(self, bootstrap_servers, topic_name):
        self.producer   = Producer({"bootstrap.servers": bootstrap_servers})
        self.topic_name = topic_name
        self.log_event  = log_event

    def publish(self, event):
        value = json.dumps(event).encode("utf-8")
        self.producer.produce(topic=self.topic_name, value=value)
        self.producer.flush()
        self.log_event("INFO", "published to kafka", {"topic": self.topic_name})
