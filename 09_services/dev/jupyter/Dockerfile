FROM jupyter/base-notebook:latest

USER root

# Install the project editably at build time. The build context is the repo
# root; the compose file sets it that way. Copying the repo into /workspace
# and running pip install -e writes a .pth into /opt/conda's site-packages
# that points at /workspace. At runtime the compose file bind-mounts the
# host repo over /workspace, replacing this build-time copy with live source
# while the .pth (in the image's site-packages, outside /workspace) keeps
# pointing at /workspace — so imports resolve against the live mount and
# edits flow both ways.
COPY . /workspace
RUN pip install --no-cache-dir -e "/workspace[notebook]" \
    && chown -R ${NB_UID}:${NB_GID} /workspace

USER ${NB_UID}
