# Multi-stage: build React UI, serve with nginx (proxies /api → nexus-api)

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Browser talks to same origin /api; nginx proxies to the API service.
ENV VITE_NEXUS_API_URL=
RUN npm run build

FROM nginx:1.27-alpine

# Required by the mosip/kattu docker-build reusable workflow's build-check step.
ARG SOURCE
ARG COMMIT_HASH
ARG COMMIT_ID
ARG BUILD_TIME
LABEL source=${SOURCE}
LABEL commit_hash=${COMMIT_HASH}
LABEL commit_id=${COMMIT_ID}
LABEL build_time=${BUILD_TIME}

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Run as the image's unprivileged nginx user so the Helm chart can enable
# runAsNonRoot / readOnlyRootFilesystem by default. /var/cache/nginx and
# /var/run are mounted as writable emptyDirs by the chart at runtime (their
# baked-in ownership below only matters for `docker run` without a chart).
RUN chown -R nginx:nginx /var/cache/nginx
USER nginx

EXPOSE 8501
CMD ["nginx", "-g", "daemon off;"]
