# ====== Angular 17 dev server ======
FROM node:20-alpine

WORKDIR /app

# Disable analytics prompt
ENV NG_CLI_ANALYTICS=false
# Force polling for file watching (Windows bind mounts)
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true

# Cache layer: install deps
COPY package*.json ./
RUN npm install

# Copy rest of source (volume mount overrides in dev)
COPY . ./

EXPOSE 4200

# Bind to 0.0.0.0 so Docker port forward works
# --poll enables file watch polling
CMD ["sh", "-c", "[ -d node_modules ] || npm install; npx ng serve --host 0.0.0.0 --port 4200 --poll 1000"]
