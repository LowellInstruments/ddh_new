# get for us host's BLE
sudo killall -9 bluetoothd
service dbus restart && service bluetooth restart
/usr/sbin/bluetoothd --debug &


# container access to X server & /dev entries such BLE & bind volume
sudo docker run -it \
    -v "$HOME/docker/ddh/dl_files:/ddh/dl_files:rw" \
    -v "/sys/kernel/debug/bluetooth:/_sys/kernel/debug/bluetooth:rw" \
    -v "$HOME/.Xauthority:/root/.Xauthority:rw" \
    -v /etc/localtime:/etc/localtime \
    -v /etc/timezone:/etc/timezone \
    -e "DISPLAY" \
    --privileged \
    --network=host \
    ddh:latest /bin/bash


# list containers by ID       -->  sudo docker ps
# export running container    -->  sudo docker export <cont_ID> > my_export.tar
# stop container              -->  sudo docker stop <cont_ID>
# container removal           -->  sudo docker rm <cont_ID>
# image removal               -->  sudo docker rmi <img_ID>
# import such exp. container  -->  cat <file>.tar | sudo docker import - <name>:<tag>
