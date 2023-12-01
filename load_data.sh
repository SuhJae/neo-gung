#!/bin/bash

# This is a script to load data from backups into the docker container
# It looks for backups in the backup/ folder and asks the user to choose a date if multiple are found
# Then, it restores all volumes from the selected date

# Path to the backup directory
BACKUP_DIR="backup"

# Check if the backup directory exists and is not empty
if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR)" ]; then
    echo "Found backups from the following dates:"

    # Create an associative array to hold dates and their corresponding files
    declare -A BACKUP_DATES

    # List backup files and add them to the array
    for entry in "$BACKUP_DIR"/*.tar.gz
    do
        # Extract the date from the filename
        FILENAME=$(basename "$entry")
        DATE="${FILENAME##*-}"
        DATE="${DATE%%.*}"
        BACKUP_DATES[$DATE]+="$entry "
    done

    # Display the dates
    i=0
    declare -a DATE_KEYS
    for DATE in "${!BACKUP_DATES[@]}"
    do
        echo "$i: $DATE"
        DATE_KEYS[i]=$DATE
        ((i++))
    done

    # Ask the user to choose a date
    echo "Enter the number corresponding to the date you want to restore: "
    read -r choice

    # Validate the user's choice
    if ! [[ $choice =~ ^[0-9]+$ ]] || [ "$choice" -lt 0 ] || [ "$choice" -ge "$i" ]; then
        echo "Invalid choice. Exiting."
        exit 1
    fi

    SELECTED_DATE=${DATE_KEYS[choice]}
    echo "Restoring backups from date: $SELECTED_DATE"

    # Extract and restore the backups from the selected date
    IFS=' ' read -r -a BACKUP_FILES <<< "${BACKUP_DATES[$SELECTED_DATE]}"
    for BACKUP_FILE in "${BACKUP_FILES[@]}"
    do
        echo "Restoring from $BACKUP_FILE..."

        # Determine the type of backup (MongoDB or Elasticsearch) and restore accordingly
        if [[ $BACKUP_FILE == *"mongodb"* ]]; then
            docker run --rm -v neo-gung_mongo-db:/data/db -v "$(pwd)/$BACKUP_DIR:/backup" ubuntu tar xzvf "/backup/$(basename "$BACKUP_FILE")" -C /
        elif [[ $BACKUP_FILE == *"elasticsearch"* ]]; then
            docker run --rm -v neo-gung_es-db:/usr/share/elasticsearch/data -v "$(pwd)/$BACKUP_DIR:/backup" ubuntu tar xzvf "/backup/$(basename "$BACKUP_FILE")" -C /
        else
            echo "Unrecognized backup file format: $BACKUP_FILE"
        fi
    done

    echo "Restore complete."
else
    echo "No backups found in $BACKUP_DIR."
fi

# Restart all Docker containers
docker-compose restart