# Usa un'immagine di base di Node.js
FROM node:20.11.0

# Crea una directory di lavoro nell'immagine
WORKDIR /usr/src/app

# Copia i file di dipendenza e il codice sorgente nell'immagine
COPY package*.json ./
COPY . .

# Installa le dipendenze del progetto
RUN npm install

# Esponi la porta su cui il tuo server Node.js è in ascolto
EXPOSE 4000

# Avvia il tuo server quando l'immagine viene eseguita
CMD ["node", "./src/server.mjs"]