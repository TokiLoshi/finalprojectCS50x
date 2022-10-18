# Database visualization 

Overview of Carbon Tracker

```mermaid
erDiagram
    USER ||--o{ FOOTPRINT : calculator
    USER ||--o{ TRACKERS : score_points
    USER {
        user_id INTEGER_PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
        name TEXT_NOT_NULL
        email TEXT_NOT_NULL
        leaderboardname TEXT_NOT_NULL
        hash TEXT_NOT_NULL
        datejoined TEXT_NOT_NULL
    }
    TRACKERS {
      id INTEGER_PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
      user_id INTEGER_NOT_NULL
      added_friends INTEGER
      planted_trees INTEGER
      helped_community INTEGER
      vintage_clothing INTEGER
      sustainable_clothing INTEGER
      saved_plastic INTEGER
      saved_money NUMERIC
      saved_energy NUMERIC
      bought_local INTEGER
      vacationed_local INTEGER
      less_beef INTEGER 
      less_chicken INTEGER
      less_pork INTEGER
      more_compost INTEGER 
      green_tariff TEXT 
      solar_panels TEXT
      saved_water NUMERIC
      less_waste NUMERIC
      more_recycling NUMERIC
      fewer_flights NUMERIC 
      fewer_hotels NUMERIC
      more_direct_flights NUMERIC
      miles_walk_bike NUMERIC
      carbon_offset NUMERIC
      carbon_savings NUMERIC
      total_score NUMERIC
    } 
    FOOTPRINT ||--|{ TRANSPORT_FOOTPRINT : part_2
    FOOTPRINT {
        id INTEGER_PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
        user_id INTEGER_NOT_NULL
        building TEXT_NOT_NULL
        building_impact TEXT_NOT_NULL
        state TEXT_NOT_NULL
        electricity TEXT_NOT_NULL
        electricity_impact TEXT_NOT_NULL
        household_occupants INTEGER_NOT_NULL
        waste_frequency INTEGER_NOT_NULL
        recycling NUMERIC_NOT_NULL
        landfill_impact TEXT_NOT_NULL
        recycling_impact TEXT_NOT_NULL
        drycleaning TEXT
        drycleaning_impact TEXT 
        total_footprint_general TEXT
    }
    TRANSPORT_FOOTPRINT ||--|{ CONSUMPTION_FOOTPRINT : part_3
    TRANSPORT_FOOTPRINT {
        id INTEGER_PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
        user_id INTEGER_NOT_NULL
        work_situation TEXT_NOT_NULL
        commuter_distance NUMERIC_NOT_NULL
        transport_mode TEXT_NOT_NULL
        transport_cost NUMERIC
        commuter_impact TEXT 
        short_haul INTEGER
        short_haul_impact TEXT
        medium_haul INTEGER
        medium_haul_impact TEXT 
        long_haul INTEGER
        long_haul_impact TEXT
        transport_footprint_total TEXT
    }
    CONSUMPTION_FOOTPRINT {
      id INTEGER_PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
      user_id INTEGER_NOT_NULL
      beef_consumption INTEGER_NOT_NULL
      beef_impact TEXT_NOT_NULL
      pork_consumption INTEGER_NOT_NULL
      pork_impact TEXT_NOT_NULL
      chicken_consumption INTEGER_NOT_NULL
      chicken_impact TEXT_NOT_NULL
      dietary_attitude TEXT_NOT_NULL
      new_clothes TEXT
      new_clothes_impact TEXT
      restaurants TEXT 
      restaurants_impact TEXT
      accessories TEXT 
      accessories_impact TEXT
      electronics TEXT 
      electronics_impact TEXT
      hotels TEXT
      hotels_impact TEXT
      consumption_footprint_total TEXT

    }
    TRACKERS ||--o{ LEADERBOARD : pull_top_ten
    LEADERBOARD {
      id PRIMARY_KEY_AUTOINCREMENT_NOT_NULL
      user_id INTEGER_NOT_NULL 
      leaderboardname TEXT_NOT_NULL 
      challenges NUMERIC 
      green_miles NUMERIC 
      carbon_saved NUMERIC
      plastic_saved NUMERIC 
      total_points NUMERIC
    }
  ```
