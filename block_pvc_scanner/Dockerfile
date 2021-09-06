ARG base_image_version=3.9.7-alpine3.14
FROM python:${base_image_version} as builder

RUN apk update && apk add gcc libc-dev linux-headers

# setup build venv
ENV VIRTUAL_ENV=/opt/build-venv
RUN python3 -m venv --system-site-packages $VIRTUAL_ENV
ENV OLD_PATH=$PATH
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# install build tools
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel build

# build
COPY . ./src
RUN cd src && python3 -m build --wheel

# setup runtime venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=$OLD_PATH
RUN python3 -m venv --system-site-packages $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$OLD_PATH"

# install package
RUN cd src && pip install --no-cache-dir --disable-pip-version-check --use-feature=in-tree-build ./dist/*.whl

# remove build tools
RUN python3 -m pip uninstall -y setuptools wheel pip

# runtime image
FROM python:${base_image_version}

# copy venv
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder /opt/venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV PYTHONUNBUFFERED=1

CMD 'block-pvc-scanner'
