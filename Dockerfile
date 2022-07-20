FROM python:3.9
RUN pip install poetry
WORKDIR /runtime

COPY poetry.lock pyproject.toml .
RUN poetry install

COPY check_docker_yagna.py .
COPY run.sh .
ADD ethnode_requestor ./ethnode_requestor
ENV PATH=".:${PATH}"
