#FROM ghcr.io/hyperledger/aries-cloudagent-python:py3.9-indy-1.16.0-0.8.2
#bcgovimages/von-image:py36-1.16-1
FROM ghcr.io/hyperledger/aries-cloudagent-python:py3.9-indy-1.16.0-0.12.2

USER root
ENV POETRY_HOME=/opt/poetry \
    VENV=/usr/src/app/.venv
ENV PATH="$POETRY_HOME/bin:$VENV/bin:$PATH"

#RUN curl -sSL https://install.python-poetry.org | python3 -
# Fixes installation failure
RUN pip3 install --no-cache-dir poetry
USER indy
RUN poetry config virtualenvs.create true; poetry config virtualenvs.in-project true

#RUN mkdir acapy_cache_redis && touch acapy_cache_redis/__init__.py
COPY --chown=indy:indy pyproject.toml poetry.lock ./

RUN poetry install 

# Make site packages location more accessible (for use with volumes)
#RUN ln -s $(poetry env info -p)/lib/python3.6/site-packages site-packages

#COPY --chown=indy:indy docker/default.yml .
COPY --chown=indy:indy afj_load_testing/ afj_load_testing/

#ENTRYPOINT ["/bin/bash", "-c", "aca-py \"$@\"", "--"]
ENTRYPOINT ["/bin/bash", "-c", "poetry run aca-py \"$@\"", "--"]
CMD ["start", "--arg-file", "default.yml"]
