REPO		?= gianlu33/reactive-uart2ip
TAG			?= latest

BACKUP	?= registry.rosetta.ericssondevops.com/gftl-er-5g-hosts/authentic-execution/fosdem-21-images/reactive-uart2ip:latest

LOG			?= info

build:
	docker build -t $(REPO):$(TAG) .

push:
	docker push $(REPO):$(TAG)

push_backup:
		docker tag $(REPO):$(TAG) $(BACKUP)
		docker push $(BACKUP)

pull:
	docker pull $(REPO):$(TAG)

run: check_port check_device
	docker run --network=host --device=$(DEVICE) --rm $(REPO):$(TAG) reactive-uart2ip -p $(PORT) -d $(DEVICE) -l $(LOG)

login:
	docker login

clean:
	docker rm $(shell docker ps -a -q) 2> /dev/null || true
	docker image prune -f

check_port:
	@test $(PORT) || (echo "PORT variable not defined. Run make <target> PORT=<port>" && return 1)

check_device:
	@test $(DEVICE) || (echo "DEVICE variable not defined. Run make <target> DEVICE=<device>" && return 1)
