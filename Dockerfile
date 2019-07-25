# docker build -t docker.io/robertbartlettbaron/acct-req .
# docker run docker.io/robertbartlettbaron/acct-req
# docker push "docker.io/robertbartlettbaron/acct-req"
#FROM registry.redhat.io/rhel  
FROM centos

WORKDIR /app

RUN yum install -y cpan

RUN yum list | grep python

#RUN yum -y install rh-python36
#RUN yum -y install rh-hython36-pip 

RUN yum -y install make gcc libffi-devel openssl-devel bzip2-devel wget digg wireshark git \
 && mkdir /app/python \
 && cd /app/python \
 && wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tgz \
 && tar xzf Python-3.7.2.tgz \
 && cd Python-3.7.2 \
 && ./configure --enable-optimizations \
 && make all \
 && make install \
 && curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py \
 && python3 get-pip.py

RUN python3 --version
# && pip3.4 install --upgrade pip \
# && pip3.4 install 'setuptools>=18.5' \
# && cd /app
 
RUN mkdir /app/openshift-acct-req \
  && cd /app/openshift-acct-req \
  && pip3 install gunicorn \
  && pip3 install Flask \
  && pip3 install kubernetes \
  && pip3 install openshift

COPY wsgi.py /app/openshift-acct-req/wsgi.py
COPY start.sh /app/openshift-acct-req/start.sh
COPY requirements.txt /app/openshift-acct-req/requirements.txt
COPY config.py /app/openshift-acct-req/config.py

RUN cd /app/openshift-acct-req \
  && pip3 install -r requirements.txt

RUN chmod -R 777 /app
RUN chmod -R 777 /usr

EXPOSE 8080 8443

USER 1001

WORKDIR /app/openshift-acct-req
CMD ["/app/openshift-acct-req/start.sh"]

