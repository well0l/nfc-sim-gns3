FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /app/data

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .

ENV DB_PATH=/app/data/nfc.db

EXPOSE 8080

# Script di configurazione rete + avvio app
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'sleep 3' >> /app/start.sh && \
    echo 'ip addr add 10.10.100.10/24 dev eth0 2>/dev/null || true' >> /app/start.sh && \
    echo 'ip link set eth0 up' >> /app/start.sh && \
    echo 'ip route add default via 10.10.100.1 2>/dev/null || true' >> /app/start.sh && \
    echo 'echo "Backend IP: 10.10.100.10"' >> /app/start.sh && \
    echo 'python app.py' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
