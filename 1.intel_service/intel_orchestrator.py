"""
consumes intel signals from kafka, validates them, adds movement distance, and stores to mysql
gets: raw message from kafka topic 'intel'
gives: validated intel records to mysql intel table, 
       entity state updates to entities table,
       invalid messages to kafka topic intel_signals_dlq
"""
