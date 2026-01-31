FROM node:20-slim

WORKDIR /app

# Copia i file dei pacchetti
COPY package*.json ./

# Installa le dipendenze
RUN npm install

# Copia tutto il resto
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
