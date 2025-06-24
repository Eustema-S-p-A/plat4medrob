import { fume } from "../utils/fume.mjs";
import fs from "fs/promises";
import {fumeUtils} from "fume-fhir-converter";

const convert = async (entity, input, res) => {
  try {
    const map = fs.readFileSync(`../mappings/${entity}.txt`, "utf8");
    const fhir = await fume.transform(input, map);
    res.json(fhir);
  } catch (error) {
    console.error("Errore durante la conversione:", error.message);
    res.status(500).json(error);
  }
};

export const controllers = {
  message2Json: async (req, res) => {
    try {
      const response = await fumeUtils.v2json(req.body);
      res.json(response);
    } catch (error) {
      console.error("Errore durante il parsing:", error.message);
      res.status(500).json(error);
    }
  },
  message2fhir: async (req, res) => {
    const path = "./src/utils/map_hl7_tb.txt";
    try {
      await fs.access(path);
      const map = await fs.readFile(path, "utf8");
      const input = JSON.parse(req.body); 
      const fhir = await fume.transform(input, map);
      console.log("Conversione in fhir del messaggio hl7 andata a buon fine") 
      res.json(fhir);
    } catch (error) {
      console.error("Errore durante la conversione del messaggio hl7:", error.message);
      res.status(500).json(error);
    }
  },
  eeg2fhir: async (req, res) => {
    const path = "./src/utils/map_eeg.txt";
    try {
      
      await fs.access(path);
      const map = await fs.readFile(path, "utf8");
      const jsonData = JSON.parse(req.body);
      const fhir = await fume.transform(jsonData, map);
      console.log("Conversione in fhir dell'eeg andata a buon fine");
      res.json(fhir);
    } catch (error) {
      console.error("Errore durante la conversione dell'eeg:", error.message);
      res.status(500).json(error);
    }
  },
  redcap2fhir: async (req, res) => {
    const schema = req.query.schema ?? "";
    const path = `./src/utils/map_redcap_${schema}.txt`;
    try {
      await fs.access(path);
      const map = await fs.readFile(path, "utf8");
      const jsonData = JSON.parse(req.body);
      const fhir = await fume.transform(jsonData, map);
      console.log("Conversione in fhir dei dati redcap andata a buon fine");
      res.json(fhir);
    } catch (error) {
      console.error("Errore durante la conversione dei dati redcap:", error.message);
      res.status(500).json(error);
    }
  },
  dicom2fhir: async (req, res) => {
    const path = "./src/utils/map_dicom.txt";
    try {
      await fs.access(path);
      const map = await fs.readFile(path, "utf8");
      const jsonData = JSON.parse(req.body);
      const fhir = await fume.transform(jsonData, map);
      console.log("Conversione in fhir dei dati dicom andata a buon fine");
      res.json(fhir);
    } catch (error) {
      console.error("Errore durante la conversione dei dati dicom:", error.message);
      res.status(500).json(error);
    }
  },
  mvnx2fhir: async (req, res) => {
    const path = "./src/utils/map_mvnx.txt";
    try {
      
      await fs.access(path);
      const map = await fs.readFile(path, "utf8");
      const jsonData = JSON.parse(req.body);
      const fhir = await fume.transform(jsonData, map);
      console.log("Conversione in fhir del mvnx andata a buon fine");
      res.json(fhir);
    } catch (error) {
      console.error("Errore durante la conversione del mvnx:", error.message);
      res.status(500).json(error);
    }
  },

};
