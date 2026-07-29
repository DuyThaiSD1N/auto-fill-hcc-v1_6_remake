# ===== Stage 1: build Vite =====
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
# VITE_API_BASE để trống: FE gọi /api, /auth tương đối → nginx proxy sang backend.
RUN npm run build

# ===== Stage 2: serve bằng nginx =====
FROM nginx:1.27-alpine

# Backend đích để nginx proxy /api, /auth (override khi docker run nếu cần).
ENV BACKEND_URL=http://app:8000

# Template được entrypoint nginx envsubst (thay ${BACKEND_URL}) lúc khởi động.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 12006
