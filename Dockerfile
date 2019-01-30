FROM rhel  

WORKDIR /app

RUN curl -o /etc/yum.repos.d/epel7local.repo http://mochat.massopen.cloud/repos/epel7local.repo
RUN curl -o /etc/yum.repos.d/shift311.repo http://mochat.massopen.cloud/repos/shift311.repo
#RUN yum group install -y "Development Tools"
RUN yum install -y cpan

RUN yum -y install make python34 python34-pip gcc openssl-devel bzip2-devel wget digg wireshark git \
 && pip3.4 install --upgrade pip \
 && pip3.4 install 'setuptools>=18.5' \
 && cd /app

RUN cd /app \
  && git clone https://github.com/robbaronbu/openshift-acct-req.git \
  && cd openshift-acct-req \
  && pip3.4 install gunicorn \
  && pip3.4 install Flask \
  && pip3.4 install kubernetes \
  && pip3.4 install openshift \
  && pip3.4 install -r requirements.txt


RUN chmod -R 777 /app
RUN chmod -R 777 /usr

EXPOSE 8080 8443

USER 1001

WORKDIR /app/openshift-acct-req
CMD ["/app/openshift-acct-req/start.sh"]

