docker stop openproject-automation-scripts && rm openproject-automation-scripts
docker image rm openproject-automation-scripts

docker build -t openproject-automation-scripts .
docker run \
    --name openproject-automation-scripts \
    --mount "type=bind,source=$(pwd)/app,target=/app" \
    --env-file "$(pwd)/.env" \
    --rm -itd openproject-automation-scripts