FROM python:3.9
RUN pip install poetry
WORKDIR /runtime

COPY poetry.lock pyproject.toml .
RUN poetry install

COPY check_docker_yagna.py .
COPY run.sh .
ADD https://github.com/golemfactory/yagna/releases/download/v0.10.1/golem-requestor-linux-v0.10.1.tar.gz .
RUN tar -xvf golem-requestor-linux-v0.10.1.tar.gz
RUN mv golem-requestor-linux-v0.10.1/gftp .
RUN rm -fr golem-requestor-linux-v0.10.1
RUN rm golem-requestor-linux-v0.10.1.tar.gz
ADD ethnode_requestor ./ethnode_requestor
ENV PATH=".:${PATH}"
