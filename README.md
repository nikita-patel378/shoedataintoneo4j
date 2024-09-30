Shoe Mileage Tracker - Strava Data Migration to Neo4j
This repository contains the ETL (Extract, Transform, Load) script used to migrate Strava activity data into Neo4j for tracking shoe mileage and activities with my dogs. The script automates the process of fetching data from the Strava API, transforming it according to the data model, and loading it into a Neo4j database.

Project Overview
The goal of this project is to track the mileage of my shoes and analyze my activities (running, walking, hiking) with different dogs, such as my dog Laika and my brother’s dog, Cookie. Initially, the data was stored in PostgreSQL, but I migrated it to Neo4j for more intuitive querying and analysis of multi-dimensional relationships.

Features:
Fetches activity data from the Strava API and loads it into Neo4j.
Tracks mileage covered by each shoe.
Logs activities completed with my dog Laika, my brother's dog Cookie, or without any dogs.
Allows for querying complex relationships between shoes, activities, and dogs.
Data Model
In Neo4j, the following nodes and relationships are created:

Nodes:

Activity: Represents an activity (run, walk, or hike) with properties such as distance, time, and date.
Shoe: Represents the shoes used during an activity, with properties such as brand, model, color, and isRetired.
Dog: Represents dogs accompanying me on activities (e.g., Laika, Cookie).
Relationships:

Uses: Connects an Activity to a Shoe, showing which shoe was used for that activity.
Completed_With: Connects an Activity to a Dog, indicating which dog accompanied me on that activity.
