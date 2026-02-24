FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .
COPY templates/ templates/


ENV BACKEND_URL=http://10.10.100.10:8080
ENV DEVICE_ID=cassa

EXPOSE 5001

RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'sleep 3' >> /app/start.sh && \
    echo 'ip addr add 10.10.20.10/24 dev eth0 2>/dev/null || true' >> /app/start.sh && \
    echo 'ip link set eth0 up' >> /app/start.sh && \
    echo 'ip route add default via 10.10.20.1 2>/dev/null || true' >> /app/start.sh && \
    echo 'echo "Cassa IP: 10.10.20.10"' >> /app/start.sh && \
    echo 'python app.py' >> /app/start.sh && \
    chmod +x /app/start.sh

CMD ["/app/start.sh"]
