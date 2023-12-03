# Neo-Gung
The all-new backend worker for the [GungGungYouYou](https://gung.joseon.space) webservice.

## 1. Introduction
This is the repository for the total remake of the of the [GungGungYouYou](https://gung.joseon.space) webservice.
The original backend worker was written just in 2 days without considering the scalability and maintainability with huge issues like:
1. Hardcoded crawling logic, parameters, secrets, and more on over 20 files.
2. No proper logging system.
3. Full of boilerplate code; lack of encapsulation.

After half an year of the original release, the service has grown up to a level that the original schema and architecture cannot handle. 
So I decided to remake the backend worker from scratch, but this time with proper design and architecture driven from the principles of OOP and Clean Architecture.
Also I employed the docker so that the service can be deployed easily on any environment.

## 2. Structure
**[compose.yaml](compose.yaml)**:
The docker-compose file for the service. It contains the configuration for `mongodb`, `elastic search`, `nginx`, `backend`, and `neo-gung`.
Run `docker-compose up -d` to start the service.

**[reset.sh](reset.sh)**:
This is development script for quickly resetting the database and the elastic search index.
It will remove all the data in the database and the index, and then reinitialize them with the default state.

**[save_data.sh](save_data.sh)**:
This script will dump mongodb and elastic search data into the `backup` directory.
This can be used for migrating the data to another environment, or making a checkpoint during development.
Since all the data needed for the service is stored in the database, this script will back up all the data needed for the service.

**[load_data.sh](load_data.sh)**:
This script will load the data dumped by `save_data.sh` into the database.
This will look for the backup files in the `backup` directory and give you a list of backups to choose from.
After choosing the backup, it will load the data into the database and restart the service.

**[crawler](crawler)**:
This directory contains the crawler for the service.
This will update the database with the latest data from the web and index them into the elastic search and mongodb.
Written in python and uses ChromeDriver for crawling.

**[elasticsearch](elasticsearch)**:
The elastic search configuration for the service. This will install the elastic search plugin needed for the service when the container is built.

**[flask](flask)**:
The backend worker for the service. This will handle the requests from the frontend and respond with the data from the database.
Still in development, and looking to change to FastAPI, since it will use JSON api to communicate with the frontend, and there is no need for the flask's template rendering.

**[nginx](nginx)**:
The nginx configuration for the service. This will serve the static files from the frontend and proxy the requests to the backend worker.
This will provide users with the static files from the frontend and proxy the requests to the backend worker.
