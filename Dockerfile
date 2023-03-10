from ubuntu:20.04

RUN apt-get update && apt-get install -y vim curl
RUN apt-get install -y python3 python3-pip

RUN mkdir /root/.pip
# If you're deploying to some host in china, please uncomment this to build image faster.
# COPY pip.conf /root/.pip/pip.conf

RUN pip3 install --upgrade pip
# after upgrade pip, the pip3 command will not be working
RUN pip install uwsgi Flask requests lxml

RUN apt-get install -y language-pack-en-base && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
RUN echo 'LANGUAGE=en_US.UTF-8' >> /etc/environment && \
    echo 'LC_ALL=en_US.UTF-8' >> /etc/environment

RUN DEBIAN_FRONTEND=noninteractive TZ=Asia/Shanghai apt-get -y install tzdata && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

WORKDIR /app

COPY ./wechatgpt ./wechatgpt

ENV THREADS 4

CMD UWSGI_PYTHONPATH=/app UWSGI_MODULE=wechatgpt.server:app TZ=Asia/Shanghai LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8 PYTHONIOENCODING=UTF-8 \
    UWSGI_LOG_MASTER=true USWGI_THREADED_LOGGER=true UWSGI_SAFE_PIDFILE=/var/run/uwsgi.pid \
    uwsgi --http :9090 --master --http-workers 1 --http-processes 1 --processes 1 --workers 1 --threads ${THREADS} --stats :9091 --stats-http --enable-threads