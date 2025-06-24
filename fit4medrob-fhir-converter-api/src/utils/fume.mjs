import { FumeServer, FhirClient} from "fume-fhir-converter";
import dotenv from 'dotenv';
dotenv.config();


async function init() {
    // Creazione dell'istanza di FhirClient con la configurazione necessaria
    const fhirClient = new FhirClient();

    // Creazione dell'istanza di FumeServer
    const fumeServer = new FumeServer();

    // Registra il FhirClient personalizzato in FumeServer
    fumeServer.registerFhirClient(fhirClient);


    // Avvia il server
    try {
        await fumeServer.warmUp(); //serverOptions
        console.log('FumeServer è stato avviato con successo');
    } catch (error) {
        console.error('Errore durante l\'inizializzazione di FumeServer:', error);
    }

    // Restituisce il FumeServer per uso in altro codice
    return fumeServer;
}

let fumeServerInstance;

init().then(server => {
    fumeServerInstance = server;
}).catch(error => {
    console.error('Failed to initialize the server:', error);
});

export { fumeServerInstance as fume };