ARG base_image_tag=3.10.2-alpine3.15
FROM python:${base_image_tag} as builder

RUN apk add --no-cache gcc libc-dev linux-headers && rm -rf "/var/cache/apk/*"

# setup build venv
ENV VIRTUAL_ENV=/opt/build-venv
RUN python3 -m venv --system-site-packages $VIRTUAL_ENV
ENV OLD_PATH=$PATH
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install build tools
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel build

# build
COPY . /src
WORKDIR /src
RUN python3 -m build --wheel
WORKDIR /

# setup runtime venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=$OLD_PATH
RUN python3 -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$OLD_PATH"

# install package
WORKDIR /src
RUN pip install --no-cache-dir --disable-pip-version-check --use-feature=in-tree-build ./dist/*.whl
WORKDIR /

# remove build tools
RUN python3 -m pip uninstall -y setuptools wheel pip

# runtime image
FROM python:${base_image_tag}

# copy venv
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder /opt/venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED=1

CMD ["block-pvc-scanner"]
