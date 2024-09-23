FROM ghcr.io/osgeo/gdal:ubuntu-small-latest

ENV TASK_ROOT=/var/task
ENV PATH="$TASK_ROOT/bin:$PATH"

RUN apt-get update && \
    apt-get install -y build-essential gcc-aarch64-linux-gnu ca-certificates curl gnupg vim libasound2-dev libatk1.0-0 libc6 libcairo2 libcups2 \
    libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 \
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 \
    libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libnss3 \
    lsb-release xdg-utils wget ca-certificates libclang-dev libgc1 libobjc4 libpq5 libxcb-xkb1 \
    libxkbcommon-x11-0 libgbm-dev python3-pip python3-venv && \
    python3 -m venv $TASK_ROOT && \
    $TASK_ROOT/bin/pip install --upgrade pip

COPY ./fastapi/requirements.txt ${TASK_ROOT}/fastapi/requirements.txt

RUN $TASK_ROOT/bin/pip install --no-cache-dir -r ${TASK_ROOT}/fastapi/requirements.txt --break-system-packages

WORKDIR ${TASK_ROOT}

RUN mkdir ${TASK_ROOT}/fastapi/data ${TASK_ROOT}/fastapi/db

RUN groupadd -r appgroup && useradd -r -g appgroup -d ${TASK_ROOT} -s /bin/bash appuser && \
    chown -R appuser:appgroup ${TASK_ROOT}
    
USER appuser
EXPOSE 8080

COPY ./fastapi/main.py ${TASK_ROOT}/fastapi/main.py
COPY ./fastapi/test_unittests.py ${TASK_ROOT}/fastapi/unittests.py

CMD ["bash", "-c", "PYTHONPATH=${TASK_ROOT}/fastapi uvicorn main:app --host 0.0.0.0 --port 8080 --log-level debug --timeout-keep-alive 300"]
