#!/bin/bash

# This is a script to load data from backups into the docker container
# It looks for backups in the backup/ folder and asks the user to choose one if multiple are found

# Path to the backup directory
BACKUP_DIR="backup"

# Check if the backup directory exists and is not empty
if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR)" ]; then
    echo "Found the following backups:"

    # Create an array to hold the backup files
    declare -a BACKUP_FILES

    # List backup files and add them to the array
    i=0
    for entry in "$BACKUP_DIR"/*
    do
        if [[ $entry == *".tar.gz" ]]; then
            BACKUP_FILES[i]=$entry
            echo "$i: $(basename "$entry")"
            ((i++))
        fi
    done

    # Check if there are multiple backups
    if [ ${#BACKUP_FILES[@]} -gt 1 ]; then
        # Ask the user to choose a backup
        echo "Enter the number of the backup you want to restore: "
        read -r choice

        # Check if the choice is a number and within the range of available backups
        # shellcheck disable=SC2086
        if ! [[ $choice =~ ^[0-9]+$ ]] || [ "$choice" -lt 0 ] || [ $choice -ge ${#BACKUP_FILES[@]} ]; then
            echo "Invalid choice. Exiting."
            exit 1
        fi
    else
        choice=0
    fi

    # Extract and restore the chosen backup
    SELECTED_BACKUP=${BACKUP_FILES[choice]}

    echo "Restoring from $SELECTED_BACKUP..."

    # Restore MongoDB data
    if [[ $SELECTED_BACKUP == *"mongodb"* ]]; then
        # shellcheck disable=SC2046
        docker run --rm -v neo-gung_mongo-db:/data/db -v $(pwd)/$BACKUP_DIR:/backup ubuntu tar xzvf /backup/$(basename "$SELECTED_BACKUP") -C /
    fi

    # Restore Elasticsearch data
    if [[ $SELECTED_BACKUP == *"elasticsearch"* ]]; then
        # shellcheck disable=SC2046
        docker run --rm -v neo-gung_es-db:/usr/share/elasticsearch/data -v $(pwd)/$BACKUP_DIR:/backup ubuntu tar xzvf /backup/$(basename "$SELECTED_BACKUP") -C /
    fi

    echo "Restore complete."
else
    echo "No backups found in $BACKUP_DIR."
fi
