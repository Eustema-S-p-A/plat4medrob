import express from 'express';
const router = express.Router();
import { controllers } from './controllers.mjs';
import authenticateJWT from '../core/authenticate_jwt.mjs'


/**
 * @openapi
 * /message2json:
 *   post:
 *     summary: Converti un messaggio HL7 grezzo in formato JSON
 *     requestBody:
 *       description: Testo grezzo del messaggio HL7 da convertire in JSON
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *              type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/message2json', authenticateJWT, controllers.message2Json); 
/**
 * @openapi
 * /message2fhir:
 *   post:
 *     summary: Converti un messaggio HL7 grezzo in formato FHIR
 *     requestBody:
 *       description: Testo grezzo del messaggio HL7 da convertire in FHIR
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *             type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/message2fhir', authenticateJWT, controllers.message2fhir); 

/**
 * @openapi
 * /eeg2fhir:
 *   post:
 *     summary: Converti un messaggio json estratto da un file edf in formato FHIR
 *     requestBody:
 *       description: testo contenente le informazioni del segnale eeg (da convertire in json) da convertire in FHIR
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *             type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/eeg2fhir',  authenticateJWT, controllers.eeg2fhir); 
/**
 * @openapi
 * /redcap2fhir:
 *   post:
 *     summary: Converti un messaggio json estratto da un progetto redcap in formato FHIR
 *     parameters:
 *       - in: query
 *         name: schema
 *         required: false
 *         description: Specifica lo schema FHIR di destinazione (ad esempio, patient, encounter, observation)
 *         schema:
 *           type: string
 *           enum:
 *             - patient
 *             - encounter
 *             - observation
 *     requestBody:
 *       description: Testo contenente le informazioni dei record esportati da Redcap da convertire in FHIR
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *             type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/redcap2fhir',  controllers.redcap2fhir);  

/**
 * @openapi
 * /redcap2fhir:
 *   post:
 *     summary: Converti un messaggio json estratto da un file DICOM in una risorsa in formato FHIR da ingestionare in HAPI
 *     requestBody:
 *       description: testo contenente le informazioni dell'esame DICOM (da convertire in json) da convertire in risorsa FHIR
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *             type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/dicom2fhir', authenticateJWT,  controllers.dicom2fhir); // 

/**
 * @openapi
 * /eeg2fhir:
 *   post:
 *     summary: Converti un messaggio json estratto da un file mvnx in formato FHIR
 *     requestBody:
 *       description: testo contenente le informazioni del segnale di motion captures sxens (da convertire in json) da convertire in FHIR
 *       required: true
 *       content:
 *         text/plain:
 *           schema:
 *             type: string
 *     responses:
 *       '200':
 *         description: Conversione riuscita
 *         content:
 *           application/json: {}
 */
router.post('/mvnx2fhir',  authenticateJWT, controllers.mvnx2fhir);  


export default router;