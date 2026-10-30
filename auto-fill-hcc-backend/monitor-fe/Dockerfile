# Build riêng để Monitor có vòng đời deploy độc lập với web quản lý hiện tại.
FROM node:20.20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

# Cùng bundle phục vụ hai web: Monitor (mặc định, 12007) và Kiểm thử (NGINX_TEMPLATE=nginx.lab.conf.template, 12008).
ARG NGINX_TEMPLATE=nginx.conf.template
ENV BACKEND_URL=http://app:8000

COPY ${NGINX_TEMPLATE} /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 12007 12008
