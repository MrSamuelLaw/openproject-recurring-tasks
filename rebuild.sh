# stop and remove the running container if it exists.
docker stop openproject-automation-scripts && rm openproject-automation-scripts

# remove the image if it exists.
docker image rm openproject-automation-scripts

# rebuild the image fresh.
docker build -t openproject-automation-scripts .

# run the command with:
# -p 8022:22 port 22 (ssh port) mapped to host.
# -it, launch in interactive mode with putty attached.
# -d, detached, (negates -it, so removed one or the other)
# --rm, removes the container after it finishes executing.
# --name, name for the container
# --mount, bind moount local app dir to the containers app dir
# --env-file, used to inject parameters and api key into the container
docker run \
    -p 8022:22 \
    -it \
    -d \
    --rm \
    --name openproject-automation-scripts \
    --mount "type=bind,source=$(pwd)/app,target=/app" \
    --env-file "$(pwd)/.env" \
    openproject-automation-scripts