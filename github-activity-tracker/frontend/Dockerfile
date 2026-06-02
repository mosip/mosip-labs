# Use Node.js base image
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

ARG SOURCE
ARG COMMIT_HASH
ARG COMMIT_ID
ARG BUILD_TIME

LABEL source=${SOURCE}
LABEL commit_hash=${COMMIT_HASH}
LABEL commit_id=${COMMIT_ID}
LABEL build_time=${BUILD_TIME}

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
# Use empty API_BASE_URL so frontend calls same-origin (/orgs/, /admin/) - nginx proxies to backend, no CORS
ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Use nginx to serve the static files
FROM nginxinc/nginx-unprivileged:alpine

# Copy build output to nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Use our SPA + API reverse proxy config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port (unprivileged nginx listens on 8080)
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]