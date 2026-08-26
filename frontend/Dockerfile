FROM node:14.21.3-alpine

WORKDIR /app

# Теперь мы копируем оба файла, включая новый package-lock.json!
COPY package*.json ./

# npm ci работает на 300% быстрее, так как просто разворачивает готовый lock-файл
RUN npm install

COPY . ./

ENV NODE_OPTIONS="--max-old-space-size=4096"

RUN npm run build

CMD ["cp", "-r", "/app/build/.", "/frontend_static/"]
