# keep amd64 since plaso image is amd64
FROM --platform=linux/amd64 log2timeline/plaso:latest

USER root
ENV DFIRBOX_HOME=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# deps + build tools for yara-python and MemProcFS
RUN rm -rf /var/lib/apt/lists/* && mkdir -p /var/lib/apt/lists/partial && \
    apt-get update && apt-get install -y --no-install-recommends \
      python3-venv python3-dev build-essential pkg-config \
      python3-pip jq findutils file yara libyara-dev tini \
      libusb-1.0-0 libusb-1.0-0-dev libfuse2 libfuse-dev \
      openssl libssl-dev lz4 liblz4-dev \
    && rm -rf /var/lib/apt/lists/*

# create and use virtualenv to bypass PEP 668
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
# ensure the venv's bin is first in PATH so 'python' and 'dfirbox' use it
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install python dependencies into the venv
COPY requirements.txt /tmp/requirements.txt
RUN "$VIRTUAL_ENV/bin/python" -m pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY src/ /app/src/
COPY profiles/ /app/profiles/
COPY rules/ /app/rules/
COPY LICENSE README.md /app/

COPY hayabusa-3.7.0 /opt/hayabusa

RUN chmod +x /opt/hayabusa/hayabusa-3.7.0-lin-x64-musl \
    && ln -s /opt/hayabusa/hayabusa-3.7.0-lin-x64-musl /usr/local/bin/hayabusa

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/entrypoint.sh"]
CMD ["dfirbox","--help"]
