IMAGE_NAME=wechatgpt-api

build-image:
	docker build -t ${IMAGE_NAME} .

start:
	source ./.env && FLASK_APP=wechatgpt/server.py FLASK_DEBUG=1 FLASK_ENV=development flask run -p 10812

DEPLOY_HOST=YOUR_CHATGPT_DEPLOY_HOST
PORT=9090
THREADS=20
deploy:
	- rm -r build
	mkdir build
	tar cvf build/app.tar.gz --exclude __pycache__ --exclude *.pyc wechatgpt makefile Dockerfile pip.conf .env
	$(eval VER=$(shell date +%Y%m%d_%H%M%S))
	ssh ${DEPLOY_HOST} "mkdir -pv tmp/wechatgpt/${VER} tmp/wechatgpt/logs"
	scp build/app.tar.gz ${DEPLOY_HOST}:tmp/wechatgpt/${VER}/
	ssh ${DEPLOY_HOST} "cd tmp/wechatgpt/${VER}/ && tar xf app.tar.gz && make build-image IMAGE_NAME=${IMAGE_NAME}:${VER}"
	- ssh ${DEPLOY_HOST} "docker logs wechatgpt-api > tmp/wechatgpt/logs/wechatgpt-api.${VER}.log && docker stop wechatgpt-api && docker rm wechatgpt-api"
	ssh ${DEPLOY_HOST} 'source tmp/wechatgpt/${VER}/.env && docker run -d -p ${PORT}:${PORT} \
	 	-e THREADS=${THREADS} \
		-e chat_gpt_token=$${chat_gpt_token} \
		-e http_proxy=$${http_proxy} \
		-e token=$${token} \
		-e wechat_token=$${wechat_token} \
		-e admin_user_ids=$${admin_user_ids} \
		-e white_list_user_ids=$${white_list_user_ids} \
		-e admin_email=$${admin_email} \
		-e PORT=${PORT} \
		--name wechatgpt-api ${IMAGE_NAME}:${VER}'
