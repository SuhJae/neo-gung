# Dockerfile
FROM docker.elastic.co/elasticsearch/elasticsearch:8.11.1

# Install the Nori plugin for Korean
RUN bin/elasticsearch-plugin install analysis-nori

# Install the Kuromoji plugin for Japanese
RUN bin/elasticsearch-plugin install analysis-kuromoji

# Install the Smart Chinese Analysis plugin for Chinese
RUN bin/elasticsearch-plugin install analysis-smartcn