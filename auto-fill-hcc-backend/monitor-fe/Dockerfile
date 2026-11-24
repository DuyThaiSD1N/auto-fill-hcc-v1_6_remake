# Build riêng để Monitor có vòng đời deploy độc lập với web quản lý hiện tại.
FROM node:20.20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_URL=http://app:8000
# Phải có giá trị mặc định: nginx template thiếu biến là container không lên.
ENV AGENT_URL=http://host.docker.internal:12009

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
# Đổi host.docker.internal (extra_hosts) thành IP trước envsubst; file phải có quyền chạy, thiếu là nginx bỏ qua.
COPY docker-entrypoint.d/18-agent-url.envsh /docker-entrypoint.d/18-agent-url.envsh
RUN sed -i 's/\r$//' /docker-entrypoint.d/18-agent-url.envsh && chmod 755 /docker-entrypoint.d/18-agent-url.envsh
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 12007
