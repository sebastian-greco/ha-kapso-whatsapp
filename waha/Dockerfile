FROM devlikeapro/waha:gows-2026.7.1@sha256:8f3a7b11310594b973a588b2f7de061864c83532ae2cdff43280db0402bead29

ARG BUILD_ARCH=amd64
ARG BUILD_VERSION=0.1.0

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

COPY run.mjs /ha/run.mjs
COPY control.mjs /ha/control.mjs
COPY control.html /ha/control.html

CMD ["node", "/ha/run.mjs"]
