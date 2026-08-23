FROM apify/actor-node:22

COPY --chown=myuser:myuser package*.json ./
RUN npm --quiet set progress=false \
    && npm install --omit=dev --no-audit \
    && (npm list --omit=dev --all || true)

COPY --chown=myuser:myuser . ./
