FROM python:3.10-slim

ENV DEBIAN_FRONTEND noninteractive
ENV APP_HOME /app
ENV CONFIG_DIR /config
ENV DOWNLOAD_DIR /app/downloads

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    # Chrome dependencies
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libglib2.0-0 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm-dev \
    libgtk-3-0 \
    libxkbcommon-dev \
    libxss1 \
    libx11-xcb1 \
    libxcomposite1 \
    libxrandr2 \
    libdbus-glib-1-2 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

COPY pyproject.toml .
COPY IMDBTraktSyncer IMDBTraktSyncer
COPY LICENSE .

RUN pip install --no-cache-dir .

CMD ["IMDBTraktSyncer"]