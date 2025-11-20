# keep amd64 since plaso image is amd64
FROM --platform=linux/amd64 log2timeline/plaso:latest

USER root

# basic env
ENV DFIRBOX_HOME=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# deps + build tools for yara-python and MemProcFS
RUN rm -rf /var/lib/apt/lists/* && mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3-venv python3-dev build-essential pkg-config \
      python3-pip jq findutils file yara libyara-dev tini \
      libusb-1.0-0 libusb-1.0-0-dev libfuse2 libfuse-dev \
      openssl libssl-dev lz4 liblz4-dev \
      git \
    && rm -rf /var/lib/apt/lists/*

# create and use virtualenv to bypass PEP 668 and keep deps isolated
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Python deps
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt

# app code and data
WORKDIR /app

COPY src/ /app/src/
COPY profiles/ /app/profiles/
COPY rules/ /app/rules/
COPY LICENSE README.md /app/

# Hayabusa binary and config directory (from your repo)
COPY hayabusa-3.7.0 /opt/hayabusa

# Make hayabusa executable, put in PATH, and INSTALL ENCODED RULES
RUN chmod +x /opt/hayabusa/hayabusa-3.7.0-lin-x64-musl \
    && ln -s /opt/hayabusa/hayabusa-3.7.0-lin-x64-musl /usr/local/bin/hayabusa \
    && git clone --depth 1 https://github.com/Yamato-Security/hayabusa-encoded-rules.git /opt/hayabusa-encoded-rules \
    && cp /opt/hayabusa-encoded-rules/encoded_rules.yml /opt/hayabusa/ \
    && cp /opt/hayabusa-encoded-rules/rules_config_files.txt /opt/hayabusa/

# Hayabusa home for the wrapper
ENV HAYABUSA_HOME=/opt/hayabusa

# entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/entrypoint.sh"]
CMD ["dfirbox","--help"]
