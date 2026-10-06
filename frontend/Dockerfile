# AI-LifeOS frontend image.
#
# Built as static assets and served by nginx. The API base URL is baked in at
# BUILD time (Vite inlines import.meta.env into the bundle), so changing it
# requires a rebuild, not just a container restart.

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy manifests first so `npm ci` is cached until dependencies actually change.
COPY package.json package-lock.json ./

RUN npm ci

COPY . .

# Same-origin API by default: nginx proxies /api to the backend service, so the
# browser never makes a cross-origin request and CORS is not involved at all.
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
