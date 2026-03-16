import os

class IntelConfig:

    def __init__(self):
        self.KAFKA_BOOTSTRAP   = os.getenv("KAFKA_BOOTSTRAP",   "localhost:9092")
        self.KAFKA_INTEL_TOPIC = os.getenv("KAFKA_INTEL_TOPIC", "intel")
        self.KAFKA_DLQ_TOPIC   = os.getenv("KAFKA_DLQ_TOPIC",   "dlq")
        self.MYSQL_HOST        = os.getenv("MYSQL_HOST",        "127.0.0.1")
        self.MYSQL_PORT        = int(os.getenv("MYSQL_PORT",    "3306"))
        self.MYSQL_USER        = os.getenv("MYSQL_USER",        "root")
        self.MYSQL_PASSWORD    = os.getenv("MYSQL_PASSWORD",    "root_pwd")
        self.MYSQL_DATABASE    = os.getenv("MYSQL_DATABASE",    "digital_hunter_db")
        self.LOG_INDEX         = os.getenv("LOG_INDEX",         "intel-logs")
