FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV container=docker

RUN apt-get update && apt-get install -y --no-install-recommends \
    systemd systemd-sysv openssh-server nginx samba curl procps iproute2 \
    sudo ca-certificates && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash nexus && \
    echo 'nexus ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    mkdir -p /home/nexus/.ssh /run/sshd && \
    chown -R nexus:nexus /home/nexus/.ssh && chmod 700 /home/nexus/.ssh

COPY ssh/authorized_keys /home/nexus/.ssh/authorized_keys
RUN chown nexus:nexus /home/nexus/.ssh/authorized_keys && chmod 600 /home/nexus/.ssh/authorized_keys

RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    systemctl enable ssh nginx smbd

RUN printf '%s\n' '[Unit]' 'Description=NEXUS Demo Service' 'After=network.target' '' \
    '[Service]' 'Type=simple' 'ExecStart=/usr/bin/python3 -m http.server 9090 --bind 0.0.0.0' \
    'Restart=on-failure' '' '[Install]' 'WantedBy=multi-user.target' > /etc/systemd/system/nexus-demo.service

RUN systemctl enable nexus-demo.service && mkdir -p /srv/nexus-share && \
    printf '%s\n' '[nexus-share]' 'path = /srv/nexus-share' 'browseable = yes' 'read only = no' 'guest ok = yes' >> /etc/samba/smb.conf

EXPOSE 22 80 9090 445

STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
