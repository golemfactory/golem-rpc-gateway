FROM python:3.9

ENV PATH=".:${PATH}"

WORKDIR /yagna

# download release yagna binaries
ADD https://github.com/golemfactory/yagna/releases/download/v0.12.2/golem-requestor-linux-v0.12.2.tar.gz .
RUN tar -xvf golem-requestor-linux-v0.12.2.tar.gz
RUN mv golem-requestor-linux-v0.12.2/gftp .
RUN mv golem-requestor-linux-v0.12.2/yagna .
RUN rm -fr golem-requestor-linux-v0.12.2
RUN rm golem-requestor-linux-v0.12.2.tar.gz
RUN chmod +x gftp
RUN chmod +x yagna

# install python requirements for yagna_mon.py
RUN pip install quart requests

# run script + monitor
COPY run.sh .
RUN chmod +x run.sh

COPY yagna_mon.py .

