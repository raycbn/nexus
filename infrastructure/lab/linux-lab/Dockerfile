FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    nginx \
    python3 \
    python3-pip \
    procps \
    iproute2 \
    curl \
    net-tools \
    lsof \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd /var/log/nginx /var/www/html

RUN useradd -m -s /bin/bash -G sudo nexus && \
    echo 'nexus ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

RUN mkdir -p /home/nexus/.ssh && \
    chown -R nexus:nexus /home/nexus && \
    chmod 700 /home/nexus/.ssh

RUN echo 'PermitRootLogin no' >> /etc/ssh/sshd_config && \
    echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config && \
    echo 'PasswordAuthentication no' >> /etc/ssh/sshd_config && \
    echo 'AuthorizedKeysFile .ssh/authorized_keys' >> /etc/ssh/sshd_config

COPY linux-lab/ssh/sshd_config /etc/ssh/sshd_config

RUN chown root:root /etc/ssh/sshd_config && \
    chmod 644 /etc/ssh/sshd_config

COPY config/api.py /opt/api/app.py
COPY config/requirements.txt /opt/api/requirements.txt

RUN pip3 install --break-system-packages --no-cache-dir -r /opt/api/requirements.txt && \
    chown -R nexus:nexus /opt/api

COPY config/nginx.conf /etc/nginx/sites-available/lab
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/lab /etc/nginx/sites-enabled/lab && \
    nginx -t

RUN mkdir -p /var/log/app && chown -R nexus:nexus /var/log/app

COPY linux-lab/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown root:root /entrypoint.sh

EXPOSE 22 80

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
