FROM alpine:latest

RUN apk add --no-cache \
    iproute2 \
    iptables \
    iputils \
    bash \
    net-tools

RUN echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

WORKDIR /root

RUN echo '#!/bin/bash' > /root/start.sh && \
    echo 'sleep 3' >> /root/start.sh && \
    echo 'sysctl -w net.ipv4.ip_forward=1' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'ip link set eth1 up' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'ip link add link eth1 name eth1.10 type vlan id 10' >> /root/start.sh && \
    echo 'ip addr add 10.10.10.1/24 dev eth1.10' >> /root/start.sh && \
    echo 'ip link set eth1.10 up' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'ip link add link eth1 name eth1.20 type vlan id 20' >> /root/start.sh && \
    echo 'ip addr add 10.10.20.1/24 dev eth1.20' >> /root/start.sh && \
    echo 'ip link set eth1.20 up' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'ip link add link eth1 name eth1.30 type vlan id 30' >> /root/start.sh && \
    echo 'ip addr add 10.10.30.1/24 dev eth1.30' >> /root/start.sh && \
    echo 'ip link set eth1.30 up' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'ip link add link eth1 name eth1.100 type vlan id 100' >> /root/start.sh && \
    echo 'ip addr add 10.10.100.1/24 dev eth1.100' >> /root/start.sh && \
    echo 'ip link set eth1.100 up' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo 'echo "=== Router configurato! ==="' >> /root/start.sh && \
    echo 'ip -4 addr show | grep inet' >> /root/start.sh && \
    echo '' >> /root/start.sh && \
    echo '/bin/bash' >> /root/start.sh && \
    chmod +x /root/start.sh

CMD ["/root/start.sh"]
