# Description: Dockerfile for server

FROM node:20-slim

RUN mkdir -p /app

WORKDIR /app

RUN corepack enable

# copy project package files
COPY package.json .
COPY yarn.lock .

# copy yarn configuration files
COPY .yarn ./.yarn
COPY .yarnrc.yml .

# install dependencies
RUN yarn workspaces focus --production --all

# copy app files
COPY dist/* .

# copy app configuration files
COPY examples/wattrouter.cfg ./cfg/

# configure logging
COPY examples/wattrouter.logrotate /etc/logrotate.d/wattrouter

# making sure container starts from the right folder
WORKDIR /app

# run server
ENTRYPOINT ["node", "main.js", "-c", "cfg/wattrouter.cfg", "-l", "/var/log/wattrouter/wattrouter.log", "-v", "info"]
