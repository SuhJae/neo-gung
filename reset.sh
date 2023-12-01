#!/bin/bash

# This script will either delete all local Docker containers and volumes,
# or just the containers, based on user choice.
# Then, it uses a docker-compose.yml file in the same path to spin up new containers.

# Function to show all Docker containers
show_all_containers() {
    echo "Current Docker containers:"
    docker ps -a
}

# Function to show all Docker volumes
show_all_volumes() {
    echo "Current Docker volumes:"
    docker volume ls
}

# Function to delete all Docker containers
delete_all_containers() {
    local containers
    containers=$(docker ps -a -q)
    if [ -n "$containers" ]; then
        echo "Deleting all Docker containers..."
        docker rm -f $containers
    else
        echo "No Docker containers to delete."
    fi
}

# Function to delete all Docker volumes
delete_all_volumes() {
    local volumes
    volumes=$(docker volume ls -q)
    if [ -n "$volumes" ]; then
        echo "Deleting all Docker volumes..."
        docker volume rm $volumes
    else
        echo "No Docker volumes to delete."
    fi
}

# Function to spin up new containers using docker-compose
spin_up_containers() {
    echo "Spinning up new containers using docker-compose..."
    docker-compose up -d
}

# Show all containers and volumes
show_all_containers
show_all_volumes

# Confirmation prompt for initial action
# shellcheck disable=SC2162
read -p "Are you sure you want to proceed with the operation? (yes/no) " confirm

if [ "$confirm" != "yes" ]; then
    echo "Operation cancelled."
    exit 0
fi

# Ask what operation to perform
echo "Options:"
echo "  full: Delete all Docker containers and volumes, and recreate them"
echo "  partial: Delete only Docker containers and recreate them"
read -p "Choose an option (full/partial): " option

# Execute based on user choice
case $option in
    full)
        # Stop and remove all containers
        delete_all_containers
        # Remove all volumes
        delete_all_volumes
        ;;
    partial)
        # Stop and remove only containers
        delete_all_containers
        ;;
    *)
        echo "Invalid option. Operation cancelled."
        exit 1
        ;;
esac

# Use docker-compose to spin up new containers
spin_up_containers

echo "Operation completed."
