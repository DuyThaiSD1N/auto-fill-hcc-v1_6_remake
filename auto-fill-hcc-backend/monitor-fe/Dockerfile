# Build riêng để Monitor có vòng đời deploy độc lập với web quản lý hiện tại.
FROM node:20.20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

ENV BACKEND_URL=http://app:8000

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 12007
