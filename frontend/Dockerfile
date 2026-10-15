# Двухэтапная сборка: node только собирает статику, в итоговом образе один nginx.
FROM node:22-alpine AS build
WORKDIR /app
# Манифесты копируются отдельно, чтобы слой npm ci кешировался;
# npm ci ставит версии строго по package-lock.json.
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
