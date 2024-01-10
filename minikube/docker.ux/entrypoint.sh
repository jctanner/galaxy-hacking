#!/bin/sh

cd /src/ansible-hub-ui
export API_BASE_PATH=/api/galaxy
npm run start-standalone
