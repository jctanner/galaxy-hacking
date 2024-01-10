FROM node:18-alpine
RUN mkdir /src
RUN apk add --no-cache git bash
# RUN apk add --no-cache bash git
RUN git clone https://github.com/ansible/ansible-hub-ui /src/ansible-hub-ui
RUN cd /src/ansible-hub-ui ; npm install --verbose
COPY entrypoint.sh /entrypoint
RUN chmod +x /entrypoint
