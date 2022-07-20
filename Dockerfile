FROM python:3.9
WORKDIR /runtime

# download gftp needed for yapapi
ADD https://github.com/golemfactory/yagna/releases/download/v0.10.1/golem-requestor-linux-v0.10.1.tar.gz .
RUN tar -xvf golem-requestor-linux-v0.10.1.tar.gz
RUN mv golem-requestor-linux-v0.10.1/gftp .
RUN rm -fr golem-requestor-linux-v0.10.1
RUN rm golem-requestor-linux-v0.10.1.tar.gz

RUN pip install poetry yapapi ansicolors quart aiohttp requests

COPY run.sh ./
RUN chmod +x run.sh

ADD ethnode_requestor ./ethnode_requestor
ENV PATH=".:${PATH}"
