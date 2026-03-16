-- creates all four tables 

USE digital_hunter_db;

-- entities - written by intel_service, read+updated by all three services
CREATE TABLE IF NOT EXISTS entities (
    entity_id    VARCHAR(50)  PRIMARY KEY,
    time_last    VARCHAR(50),
    last_lat     FLOAT,
    last_lon     FLOAT,
    dist_last    FLOAT        DEFAULT 0.0,
    attacked     BOOLEAN      DEFAULT FALSE,
    damage_state VARCHAR(50)  DEFAULT NULL
);

-- intel - written by intel_service only
CREATE TABLE IF NOT EXISTS intel (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    signal_id      VARCHAR(100) UNIQUE,
    timestamp      VARCHAR(50),
    entity_id      VARCHAR(50),
    reported_lat   FLOAT,
    reported_lon   FLOAT,
    signal_type    VARCHAR(50),
    priority_level INT,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

-- attacks - written by attack_service only
CREATE TABLE IF NOT EXISTS attack (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    attack_id   VARCHAR(100) UNIQUE,
    timestamp   VARCHAR(50),
    entity_id   VARCHAR(50),
    weapon_type VARCHAR(100),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

-- damage - written by dammage_service only
CREATE TABLE IF NOT EXISTS damage (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    timestamp VARCHAR(50),
    attack_id VARCHAR(100),
    entity_id VARCHAR(50),
    result    VARCHAR(50),
    FOREIGN KEY (attack_id) REFERENCES attack(attack_id)
);
