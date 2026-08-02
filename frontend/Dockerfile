# Aşama 1: Node.js ile uygulamayı derle
FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Aşama 2: Nginx ile sun
FROM nginx:alpine

# Nginx config dosyasını kopyala
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Derlenen dosyaları Nginx klasörüne kopyala
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
