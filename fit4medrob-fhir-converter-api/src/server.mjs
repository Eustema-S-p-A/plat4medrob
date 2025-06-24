import express from 'express';
import swaggerUi from 'swagger-ui-express';
import swaggerDocument from './swagger.mjs';
import routes from './api/routes.mjs';
import dotenv from 'dotenv';
dotenv.config();

const app = express();
const PORT = 4000;

// Middleware per analizzare il corpo della richiesta come plain/text
app.use(express.text());


// Aggiungi le rotte definite nel file routes.js all'app
app.use('/', routes);

// Swagger
app.use('/docs', swaggerUi.serve, swaggerUi.setup(swaggerDocument));

// Avvia il server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Il server è in ascolto sulla porta ${PORT}`);
});