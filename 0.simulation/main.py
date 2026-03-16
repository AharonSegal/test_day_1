import os
from simulator import run_simulator

bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

run_simulator(bootstrap_servers=bootstrap_servers)
