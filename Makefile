PROJECT_NAME := gifts
SHARED := $(if $(SHARED_VOLUME), -v $(SHARED_VOLUME):$(SHARED_VOLUME),)


docker:
	docker build -t ${PROJECT_NAME}_dev -f docker/Dockerfile .

build_nginx:
	docker build -t ${PROJECT_NAME}_nginx -f docker/Dockerfile-nginx-flask .

up_db:
	docker-compose -f docker/docker-compose.yml up -d mongo

up_db_prod:
	docker-compose -f docker/docker-compose-nginx.yml up -d mongo_prod

run:
	# docker run -it --name ${PROJECT_NAME}_dev_${USER} ${SHARED} -v ${PROJECT_HOME}/src:/src/ -v ${PROJECT_HOME}:/workspace/ -v /var/run/docker.sock:/var/run/docker.sock:ro -p 5555:5555 ${PROJECT_NAME}_dev
	set -a
	export PROJECT_HOME=$(CURDIR) && docker-compose -f docker/docker-compose.yml up -d server
	docker logs -f docker_server_1  # docker compose name

run_nginx: 
	docker-compose -f docker/docker-compose-nginx.yml up -d server_prod
	# docker run -p 5555:80 ${PROJECT_NAME}_nginx

restart_server:
	docker-compose -f docker/docker-compose.yml restart server
	docker logs -f docker_server_1


.PHONY: docker up_db run restart_server