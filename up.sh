# stop and remove the running container if it exists.
docker stop openproject-recurring-tasks && rm openproject-recurring-tasks

# remove the image if it exists.
docker image rm openproject-recurring-tasks

# rebuild the image fresh.
docker build -t openproject-recurring-tasks .

# run the command with:
# -p 8022:22 port 22 (ssh port) mapped to host.
# -it, launch in interactive mode with putty attached.
# -d, detached, (negates -it, so removed one or the other)
# --rm, removes the container after it finishes executing.
# --name, name for the container
# --mount, bind moount local app dir to the containers app dir
# --env-file, used to inject parameters and api key into the container
docker run \
    -it \
    -d \
    --rm \
    --name openproject-recurring-tasks \
    --mount "type=bind,source=$(pwd)/app,target=/app" \
    --env-file "$(pwd)/.env" \
    openproject-recurring-tasks
