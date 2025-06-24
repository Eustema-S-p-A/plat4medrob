"""
Modulo per la generazione di file CSV dai dati di analisi.
Fornisce una classe per convertire dati strutturati in formato CSV.
"""
import io
import logging
from typing import List, Dict, Any

import pandas as pd

# Configurazione logger
logger = logging.getLogger(__name__)


class CSVGenerator:
    """
    Classe per la generazione di file CSV dai dati di analisi pazienti.
    Supporta formati 'wide' e 'long'.
    """

    def __init__(self):
        """Inizializza il generatore CSV."""
        self.formats = {
            "wide": self._generate_wide_format,
            "long": self._generate_long_format
        }

    def generate(self, data: List[Dict[str, Any]], outcome_col: str,
                 format_type: str = "wide") -> io.StringIO:
        """
        Genera un CSV con i dati dei pazienti per l'analisi statistica.

        Args:
            data: Lista di dizionari contenente i dati dei pazienti
            outcome_col: Nome della colonna che rappresenta l'outcome clinico
            format_type: Formato del file ("long" o "wide")

        Returns:
            StringIO contenente il CSV generato

        Raises:
            ValueError: Se i dati sono vuoti o mancano colonne necessarie
            ValueError: Se il formato specificato non è supportato
        """
        # Validazione input
        self._validate_input(data, outcome_col, format_type)

        # Converti i dati in DataFrame
        df = pd.DataFrame(data)

        # Verifica colonne richieste
        self._verify_required_columns(df, outcome_col)

        # Normalizza l'ordine dei gruppi
        df = self._normalize_group_order(df)

        # Genera il formato richiesto
        if format_type in self.formats:
            export_df = self.formats[format_type](df, outcome_col)
        else:
            raise ValueError(f"Formato non supportato: {format_type}. "
                             f"Formati disponibili: {', '.join(self.formats.keys())}")

        # Genera il file CSV
        return self._write_to_csv(export_df)

    def _validate_input(self, data: List[Dict[str, Any]], outcome_col: str,
                        format_type: str) -> None:
        """
        Valida i dati di input.

        Args:
            data: Lista di dizionari con i dati
            outcome_col: Nome della colonna outcome
            format_type: Formato richiesto

        Raises:
            ValueError: Se i dati sono vuoti o il formato non è supportato
        """
        if not data or len(data) == 0:
            raise ValueError("Nessun dato disponibile per la generazione del CSV.")

        if not format_type in self.formats:
            raise ValueError(f"Formato non supportato: {format_type}. "
                             f"Formati disponibili: {', '.join(self.formats.keys())}")

    def _verify_required_columns(self, df: pd.DataFrame, outcome_col: str) -> None:
        """
        Verifica che tutte le colonne necessarie siano presenti nel DataFrame.

        Args:
            df: DataFrame da verificare
            outcome_col: Nome della colonna outcome

        Raises:
            ValueError: Se mancano colonne richieste
        """
        required_columns = ["Group", "Patient_ID", "Time", outcome_col]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Colonne mancanti nel dataset: {missing_columns}")

    def _normalize_group_order(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizza l'ordine dei gruppi basandosi sull'ordine di arrivo.

        Args:
            df: DataFrame da normalizzare

        Returns:
            DataFrame con ordine dei gruppi normalizzato
        """
        unique_groups = list(dict.fromkeys(df["Group"]))
        df["Group"] = pd.Categorical(df["Group"], categories=unique_groups, ordered=True)
        return df

    def _generate_wide_format(self, df: pd.DataFrame, outcome_col: str) -> pd.DataFrame:
        """
        Genera un DataFrame in formato 'wide' (una riga per paziente).

        Args:
            df: DataFrame di input in formato 'long'
            outcome_col: Nome della colonna outcome

        Returns:
            DataFrame in formato 'wide'
        """
        # Converti in formato wide con una riga per paziente e colonne per timepoint
        df_wide = df.pivot(index=["Patient_ID", "Group"],
                           columns="Time",
                           values=outcome_col).reset_index()

        # Rinomina le colonne per renderle più leggibili
        df_wide.columns = ["Patient_ID", "Group"] + [
            f"{outcome_col}_{col}" for col in df_wide.columns[2:]
        ]

        # Ordina per gruppo e ID paziente
        return df_wide.sort_values(by=["Group", "Patient_ID"])

    def _generate_long_format(self, df: pd.DataFrame, outcome_col: str) -> pd.DataFrame:
        """
        Mantiene il formato 'long' (una riga per timepoint).

        Args:
            df: DataFrame di input
            outcome_col: Nome della colonna outcome

        Returns:
            DataFrame in formato 'long' ordinato
        """
        # Ordina i dati mantenendo l'ordine dei gruppi e poi per "Patient_ID"
        return df.sort_values(by=["Group", "Patient_ID"])

    def _write_to_csv(self, df: pd.DataFrame) -> io.StringIO:
        """
        Scrive il DataFrame in un buffer CSV.

        Args:
            df: DataFrame da esportare

        Returns:
            StringIO contenente i dati CSV
        """
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)  # Riposiziona il puntatore all'inizio del file
        return output

