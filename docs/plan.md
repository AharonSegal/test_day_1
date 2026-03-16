# the data 

## the data used to generate the intel 

### Target bank — known entities with initial positions and metadata
TARGET_BANK: list[dict[str, Any]]
{
    "entity_id": "TGT-001",         UNIQUE ID
    "name": "Convoy Alpha",         PROBABLY UNIQUE
    "type": "mobile_vehicle",       I SEE 4 OPTIONS -> "mobile_vehicle","infrastructure","human_squad","launcher"
    "lat": 31.52,                   float/cor
    "lon": 34.45,                   float/cor
    "priority_level": 1,            int 1-4
    "status": "active"              str - probably 2 states 
}

### signal type - the origin of the target intel
SIGNAL_TYPES: list[str] = ["SIGINT", "VISINT", "HUMINT"]

### the type of weapon used to neutralize the target by the airstrike
WEAPON_TYPES: list[str] = [
    "AGM-114 Hellfire",
    "GBU-39 SDB",
    "Delilah Missile",
    "SPICE-250",
    "Popeye AGM",
    "Griffin LGM",
]

### the airstrike result
DAMAGE_RESULTS: list[str] = ["destroyed", "damaged", "no_damage"]

## the format of the generated intel
{
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "signal_id": str(uuid.uuid4()),
    "entity_id": entity_id,
    "reported_lat": round(new_lat, 6),
    "reported_lon": round(new_lon, 6),
    "signal_type": random.choice(SIGNAL_TYPES),
    "priority_level": target["priority_level"],
    }
## the format of the generated attack message
{
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "attack_id": attack_id,
    "entity_id": target["entity_id"],
    "weapon_type": random.choice(WEAPON_TYPES),
    }
## the format of the generated damage message
{
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "attack_id": attack_id,
    "entity_id": entity_id,
    "result": result,
    }
## the error intel
the simulator script is set to enter several types of invalid intel and raises logger WARNING
1- Return malformed JSON bytes
    variants = [
        b'{"timestamp": "2025-01-01T00:00:00Z", "signal_id": "abc", "entity_id"',
        b'not json at all!!!',
        b'{"half": "message"',
        b'{{{bad json}}}',
        b'',
    ]
    logger.warning("INJECTING broken JSON: %s", chosen[:60])

2- Return a message with critical fields missing - *or for the attack services and damage services to check that there exists a relational existace of entity_id or for the damage - attack_id in the db*
    missing either
        for intel message
            "signal_id"
            "entity_id"
            "reported_lat"
            "reported_lon"
        for attack and damage message
            "attack_id"
            "entity_id"
    logger.warning("INJECTING missing-fields message on topic '%s': %s", topic, msg)

3- Damage assessment for an attack_id that was never produced (damage always refers to an attack - in this case the damage referred to no attacks)
    damage intel will have a random "attack_id"
    logger.warning("INJECTING damage for non-existent attack: %s", fake_attack_id)

4 -Intel signal for an unknown entity near a priority-1 target (simulates a meeting)
line 234 in simulation
def inject_intel_unknown_near_priority() -> dict[str, Any]:
if a unknown entity in proximity of known probably an error

??? i think this is the meaning of this 

# tech stack

## Databases
### Mysql
choice of db - since its all based around the entity
                so this calls for a relational db 
                main table is the entities table
                    entities (
                        entity_id    VARCHAR(50)  PRIMARY KEY,
                        time_last    VARCHAR(50),
                        last_lat     FLOAT,
                        last_lon     FLOAT,
                        dist_last    FLOAT        DEFAULT 0.0,
                        attacked     BOOLEAN      DEFAULT FALSE, still not shure???
                        damage_state VARCHAR(50)  DEFAULT NULL
                    )
                intel table -
                    intel (
                        id             INT AUTO_INCREMENT PRIMARY KEY,
                        signal_id      VARCHAR(100) UNIQUE,
                        timestamp      VARCHAR(50),
                        entity_id      VARCHAR(50),
                        reported_lat   FLOAT,
                        reported_lon   FLOAT,
                        signal_type    VARCHAR(50),
                        priority_level INT,
                        FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
                    )
                attack table- 
                    attack (
                        id          INT AUTO_INCREMENT PRIMARY KEY,
                        attack_id   VARCHAR(100) UNIQUE,
                        timestamp   VARCHAR(50),
                        entity_id   VARCHAR(50),
                        weapon_type VARCHAR(100) DEFAULT NULL ??? i think here aswel,
                        FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
                    )
                damage table -
                    damage (
                        id        INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp VARCHAR(50),
                        attack_id VARCHAR(100),
                        entity_id VARCHAR(50),
                        result    VARCHAR(50),
                        FOREIGN KEY (attack_id) REFERENCES attack(attack_id)
                    )

#### COLLECTIONS 
    dataBank -> stores the messages
    entities -> stores the metadata of the entities (for example the distance between last encounters)

### elasticSearch for logs

### KafkaProducer for the kafka server 

no need for separate groups since only one is reading from each topic

## kafka topics
### 1- intel 
    producer: simulator.py -> raw intel message
    consumer: intel_processor 

  
### 2- attack 
    producer: simulator.py -> raw attack message
    consumer: attack_processor 

### 3- damage 
    producer: simulator.py -> raw damage message
    consumer: damage_processor 

### 4- intel_signals_dlq - not part of the main flow, 
        producer: all 3 services produce the errored messages here
        purpose: to get raw messages + the error


# services
    intel_processor 

    attack_processor 

    damage_processor 

# flow

## THE DATA STARTING POINT - PRODUCER
1. simulation.py injects messages to one of the topics 
TOPIC_WEIGHTS = {
    "intel": 0.60,
    "attack": 0.25,
    "damage": 0.15,
}

## AT THIS POINT IS THE SERVICES ARE THE SAME

2. all 3 services
    intel_processor 
    attack_processor 
    damage_processor 
get the massages fom their topics


3. there will be the function to validate the massage 
    each service is a producer for the intel_signals_dlq topic 
    and will send the non-valid + error message

4. if this is the first time dealing with this "entity_id"
   its priority is overwritten on this first encounter to 99

## AT THIS POINT IS THE SERVICES DIVERGE

### intel_processor

GOAL: saves the sightings of an entity
DB_INTERACTS : with the entity table only 

if the entity has been seen then calculate the distance since last seen
USING haversine.py

send lon,lat of both entities
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float

in the entity table
we will store : dist_last = the calculated distance
and update the fields for the current last entity last fields

### attack service

GOAL: saves the attacks - updates the entity
DB_INTERACTS : saves new attack to attack table
               updates entity table

sees the current entity_id
if it exists in entity table
updates the entity table
attacked = true 
saves the attack message  in attack table

### damage service

GOAL: saves to damage table - updates the entity
DB_INTERACTS : saves new damage to damage table
               updates entity table

sees the current attack_id
if it exists in attack table
updates the entity table to the level of damage 
["destroyed", "damaged", "no_damage"]
damage_state = the str that is in the damage message
saves the damage message in damage table

moved connections out 

