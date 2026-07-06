FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json saja dulu
COPY package*.json ./

# Install dependencies (gunakan npm ci jika ada lock file, jika tidak pakai install)
RUN if [ -f package-lock.json ]; then npm ci --legacy-peer-deps; else npm install --legacy-peer-deps; fi

# Copy sisa source code
COPY . .

# Build aplikasi
RUN npm run build

# Stage 2: Serve dengan Nginx
FROM nginx:alpine

# Copy hasil build
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy konfigurasi Nginx
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
