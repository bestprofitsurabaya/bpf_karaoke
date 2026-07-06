FROM node:18-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Menjalankan build Vite yang sesungguhnya
RUN npm run build

FROM nginx:alpine
# Menyalin hasil build asli dari folder dist ke folder html nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Menyalin konfigurasi nginx internal untuk handle SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
