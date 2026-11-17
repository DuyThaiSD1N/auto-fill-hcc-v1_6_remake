# Web tự động kiểm thử (cổng 12008): build riêng, không phụ thuộc thư mục auto-fill-hcc-backend.
FROM node:20.20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_URL=http://app:12005
ENV AGENT_URL=http://host.docker.internal:12009

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 12008
