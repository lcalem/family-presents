PROJECT_NAME := gifts
SHARED := $(if $(SHARED_VOLUME), -v $(SHARED_VOLUME):$(SHARED_VOLUME),)


build_dev:
	docker build -t ${PROJECT_NAME}_dev -f docker/Dockerfile .

build_prod:
	docker build -t ${PROJECT_NAME}_prod -f docker/Dockerfile-nginx-flask .

up_db_dev:
	docker-compose -f docker/docker-compose-dev.yml up -d mongo

up_db_prod:
	docker-compose -f docker/docker-compose-prod.yml up -d mongo_prod

run_dev:
	# docker run -it --name ${PROJECT_NAME}_dev_${USER} ${SHARED} -v ${PROJECT_HOME}/src:/src/ -v ${PROJECT_HOME}:/workspace/ -v /var/run/docker.sock:/var/run/docker.sock:ro -p 5555:5555 ${PROJECT_NAME}_dev
	set -a
	export PROJECT_HOME=$(CURDIR) && docker-compose -f docker/docker-compose-dev.yml up -d server
	docker logs -f docker_server_1  # docker compose name

run_prod:
	docker-compose -f docker/docker-compose-prod.yml up -d server_prod

run_all_prod: up_db_dev run_prod

restart_server:
	docker-compose -f docker/docker-compose.yml restart server
	docker logs -f docker_server_1


.PHONY: build_dev build_prod up_db_dev up_db_prod run_dev run_prod run_all_prod restart_server