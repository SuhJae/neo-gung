# This is a script to save the data from the docker container to the host
# It will save the data into the backup/ folder with the format of:
# mongodb-<date>.tar.gz and elasticsearch-<date>.tar.gz

# Get the current date
DATE=$(date +%Y%m%d)

# Create backup directory if it doesn't exist
mkdir -p backup

# Save the data from MongoDB container
# shellcheck disable=SC2046
docker run --rm --volumes-from neo-gung-mongo-1 -v $(pwd)/backup:/backup ubuntu tar czvf /backup/mongodb-"$DATE".tar.gz /data/db

# Save the data from Elasticsearch container
# shellcheck disable=SC2046
# shellcheck disable=SC2086
docker run --rm --volumes-from neo-gung-elasticsearch-1 -v $(pwd)/backup:/backup ubuntu tar czvf /backup/elasticsearch-$DATE.tar.gz /usr/share/elasticsearch/data
