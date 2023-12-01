#!/bin/bash

# This is a script to save the data from all docker volumes to the host
# It will save the data into the backup/<date> folder

# Get the current date
DATE=$(date +%Y%m%d)

# Create a date-stamped backup directory
BACKUP_DIR="backup/$DATE"
mkdir -p "$BACKUP_DIR"

# Function to backup a docker volume
backup_volume() {
    local container_name=$1
    local volume_path=$2
    local backup_name=$3

    echo "Backing up volume from $container_name..."
    docker run --rm --volumes-from "$container_name" -v "$(pwd)/$BACKUP_DIR":/backup ubuntu tar czvf "/backup/$backup_name-$DATE.tar.gz" "$volume_path"
}

# Backup MongoDB container
backup_volume "neo-gung_mongo-db" "/data/db" "mongodb"

# Backup Elasticsearch container
backup_volume "neo-gung_es-db" "/usr/share/elasticsearch/data" "elasticsearch"

echo "Backup completed."
