"""
Modulo per la generazione di report PDF con grafici boxplot.
Utilizza un approccio a classi per una migliore organizzazione e manutenibilità.
"""
import logging
from io import BytesIO
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from fpdf import FPDF
from matplotlib.patches import Patch

from app.schemas.stratification import AnalyticsResponse

# Configurazione logger
logger = logging.getLogger(__name__)


class BoxplotPositionCalculator:
    """
    Classe per calcolare le posizioni ottimali dei boxplot nei grafici.
    """

    @staticmethod
    def calculate_positions(num_timings: int, num_groups: int, box_width: float = 0.2,
                            spacing: float = 0.05) -> List[List[float]]:
        """
        Calcola le posizioni ottimali per i boxplot con spaziatura tra i gruppi.

        Args:
            num_timings: Numero di timing points (T0, T1, ecc.)
            num_groups: Numero di gruppi da visualizzare
            box_width: Larghezza di ogni boxplot
            spacing: Spaziatura aggiuntiva tra gruppi di boxplot

        Returns:
            Matrice con le posizioni per ogni gruppo e timing
        """
        # Calcola lo spazio totale necessario per gruppo, includendo la spaziatura
        total_width = (box_width * num_groups) + (spacing * (num_groups - 1))

        # Calcola gli offset per centrare i gruppi
        start_offset = -(total_width / 2) + (box_width / 2)

        # Crea la matrice delle posizioni
        positions_matrix = []
        for group in range(num_groups):
            group_positions = []
            for timing in range(num_timings):
                # La posizione base è il timing
                base_position = timing
                # Aggiungi l'offset per questo gruppo, includendo la spaziatura
                group_offset = start_offset + (group * (box_width + spacing))
                position = base_position + group_offset
                group_positions.append(position)
            positions_matrix.append(group_positions)

        return positions_matrix


class AnalyticsReportPDF(FPDF):
    """
    Classe per la generazione di report PDF di analisi con tabelle e grafici.
    Estende la classe FPDF.
    """

    def __init__(self, orientation="P", unit="mm", format="A4"):
        """Inizializza il documento PDF con impostazioni personalizzate."""
        super().__init__(orientation=orientation, unit=unit, format=format)
        self.set_auto_page_break(auto=True, margin=15)
        self.logo_path = "./app/resources/image/csm_logo_FIT4MEDROB_footer_uniformato_258215c4be.png"

    def header(self):
        """Personalizza l'intestazione di ogni pagina."""
        # Rendering logo e header colorato
        self.set_fill_color(39, 78, 131)
        self.rect(0, 0, self.w, 30, 'F')
        self.image(self.logo_path, 10, 6, 43, keep_aspect_ratio=True)

    def footer(self):
        """Personalizza il piè di pagina di ogni pagina."""
        # Position cursor at 1.5 cm from bottom
        self.set_y(-15)
        # Setting font: helvetica italic 8
        self.set_font("helvetica", style="I", size=8)
        # Printing page number
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def add_title(self, title: str):
        """Aggiunge un titolo al documento."""
        self.set_text_color(255, 255, 255)
        self.set_font("Arial", size=24)
        self.cell(200, 10, txt=title, ln=True, align='C')
        self.ln(10)
        self.set_text_color(0, 0, 0)

    def add_group_header(self, label: str, filter_text: str):
        """Aggiunge un'intestazione per un gruppo di dati."""
        self.ln(8)
        self.set_font("Arial", size=12)
        self.cell(200, 10, txt=f"Gruppo: {label} - Filtro: {filter_text}", ln=True)
        self.ln(5)

    def add_analytics_table(self, timings: List[List[float]], measure: str, t_labels: List[str]):
        """Aggiunge una tabella con statistiche descrittive per ogni timing."""
        # Impostazioni per la tabella
        self.set_font("Arial", size=10)

        # Calcolare le larghezze delle colonne in base ai dati
        col_widths = {
            "timing": self.get_string_width("Timing") + 6,
            "mean": self.get_string_width(f"Valore Medio {measure.upper()}") + 6,
            "median": self.get_string_width(f"Mediana {measure.upper()}") + 6,
            "std": self.get_string_width(f"Deviazione standard {measure.upper()}") + 6,
            "min_max": self.get_string_width(f"Min-Max {measure.upper()}") + 6,
            "count": self.get_string_width(f"Numerosità {measure.upper()}") + 6
        }

        # Calcolare la larghezza massima dei dati in ciascuna colonna
        for i, timing_data in enumerate(timings):
            timing_label = f"T{t_labels[i]}"
            col_widths["timing"] = max(col_widths["timing"], self.get_string_width(timing_label) + 6)
            col_widths["mean"] = max(col_widths["mean"], self.get_string_width(f"{np.mean(timing_data):.2f}") + 6)
            col_widths["median"] = max(col_widths["median"], self.get_string_width(f"{np.median(timing_data):.2f}") + 6)
            col_widths["std"] = max(col_widths["std"], self.get_string_width(f"{np.std(timing_data):.2f}") + 6)
            col_widths["min_max"] = max(col_widths["min_max"],
                                        self.get_string_width(
                                            f"{np.min(timing_data):.2f} ÷ {np.max(timing_data):.2f} ") + 6)
            col_widths["count"] = max(col_widths["count"], self.get_string_width(f"{len(timing_data)}") + 6)

        # Intestazioni della tabella
        self.set_text_color(255, 255, 255)
        self.set_fill_color(39, 78, 131)  # Colore di sfondo per le intestazioni
        self.set_font(family="Arial", style="B")
        self.cell(col_widths["timing"], 10, "Timing", border=1, align='C', fill=True)
        self.set_font(family="Arial")
        self.cell(col_widths["mean"], 10, f"Valore Medio {measure.upper()}", border=1, align='C', fill=True)
        self.cell(col_widths["median"], 10, f"Mediana {measure.upper()}", border=1, align='C', fill=True)
        self.cell(col_widths["std"], 10, f"Deviazione standard {measure.upper()}", border=1, align='C', fill=True)
        self.cell(col_widths["min_max"], 10, f"Min-Max {measure.upper()}", border=1, align='C', fill=True)
        self.cell(col_widths["count"], 10, f"Numerosità {measure.upper()}", border=1, align='C', fill=True)
        self.set_text_color(0, 0, 0)
        self.ln()

        # Righe dei dati
        for i, timing_data in enumerate(timings):
            timing_label = f"{t_labels[i]}"
            self.cell(col_widths["timing"], 10, timing_label, border=1, align='C')
            self.cell(col_widths["mean"], 10, f"{np.mean(timing_data):.2f}", border=1, align='C')
            self.cell(col_widths["median"], 10, f"{np.median(timing_data):.2f}", border=1, align='C')
            self.cell(col_widths["std"], 10, f"{np.std(timing_data):.2f}", border=1, align='C')
            self.cell(col_widths["min_max"], 10, f"{np.min(timing_data):.2f} ÷ {np.max(timing_data):.2f}", border=1,
                      align='C')
            self.cell(col_widths["count"], 10, f"{len(timing_data)}", border=1, align='C')
            self.ln()

    def add_new_page_if_needed(self, needed_space: int = 100):
        """Aggiunge una nuova pagina se lo spazio rimanente è insufficiente."""
        if self.get_y() + needed_space > self.h - 20:
            self.add_page()
            self.ln(40)  # Spazio dopo l'header


class BoxplotGenerator:
    """
    Classe per la generazione di grafici boxplot.
    """

    @staticmethod
    def create_boxplot(content: List[Dict[str, Any]], t_labels: List[str], group_input: List,
                       measure: str, figsize: Tuple[int, int] = (6, 4)) -> Tuple[plt.Figure, BytesIO]:
        """
        Crea un grafico boxplot per i dati di analytics.

        Args:
            content: Lista di risposte analytics con i dati per ogni gruppo
            t_labels: Lista delle etichette dei timing
            group_input: Lista dei gruppi con titoli e filtri
            measure: Nome della misura visualizzata
            figsize: Dimensioni della figura

        Returns:
            Tuple con la figura matplotlib e lo stream BytesIO dell'immagine
        """
        # Prepara la figura
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        # Genera una palette di colori
        palette = sns.color_palette("coolwarm", n_colors=len(group_input))

        # Calcola le posizioni dei boxplot
        max_timings = max([len(obj.get("data")) for obj in content])
        num_groups = len(content)
        positions = BoxplotPositionCalculator.calculate_positions(max_timings, num_groups)

        # Elementi per la legenda
        legend_elements = []

        # Aggiungi i boxplot per ogni gruppo
        for j, item in enumerate(content):
            legend_elements.append(Patch(facecolor=palette[j], edgecolor='black', label=group_input[j].title))

            # Aggiungi i boxplot per ogni timing all'interno del gruppo
            for i, timing_data in enumerate(item.get("data")):
                ax.boxplot(
                    timing_data,
                    positions=[positions[j][i]],
                    widths=0.2,
                    patch_artist=True,
                    boxprops=dict(facecolor=palette[j], color=(39 / 255, 78 / 255, 131 / 255), linewidth=1.5),
                    whiskerprops=dict(color="black", linewidth=1.2, linestyle="--"),
                    flierprops=dict(marker="o", color="red", markersize=6, alpha=0.6),
                    medianprops=dict(color="darkred", linewidth=2)
                )

        # Configura il grafico
        ax.set_title(f"Boxplot {measure.upper()}", fontsize=12, color=(39 / 255, 78 / 255, 131 / 255))
        ax.set_ylabel("Value", fontsize=10, color=(39 / 255, 78 / 255, 131 / 255))
        ax.set_xlabel(f"Timing", fontsize=10, color=(39 / 255, 78 / 255, 131 / 255))
        ax.set_xticks([x for x in range(len(t_labels))], t_labels)

        # Aggiungi la legenda
        ax.legend(
            handles=legend_elements,
            loc='upper left',
            bbox_to_anchor=(1.02, 0.95),
            borderpad=1,
            labelspacing=1
        )

        # Aggiungi una griglia leggera
        ax.grid(True, linestyle="--", alpha=0.6)

        # Ottimizza layout
        plt.tight_layout()

        # Salva l'immagine in un BytesIO stream
        img_stream = BytesIO()
        fig.savefig(img_stream, format="png", dpi=120, bbox_inches="tight")
        img_stream.seek(0)

        return fig, img_stream


class PDFReportGenerator:
    """
    Classe principale per generare report PDF completi con tabelle e grafici.
    """

    @staticmethod
    def generate_report(content: List[AnalyticsResponse], measure: str,
                        group_input: List, t_label: List) -> Optional[BytesIO]:
        """
        Genera un report PDF completo con dati di analytics e boxplot.

        Args:
            content: Lista di risposte analytics con i dati per ogni gruppo
            measure: Nome della misura visualizzata
            group_input: Lista dei gruppi con titoli e filtri
            t_label: Lista delle etichette dei timing

        Returns:
            BytesIO stream contenente il PDF generato o None in caso di errore
        """
        try:
            logger.debug("Inizializzazione report PDF")

            # Inizializza il documento PDF
            pdf = AnalyticsReportPDF()
            pdf.add_page()

            # Aggiungi il titolo
            pdf.add_title("Analytics Report")

            # Calcola il numero massimo di timings
            max_timings = max([len(obj.get("data")) for obj in content])

            # Loop attraverso il contenuto per aggiungere i gruppi come tabelle
            logger.debug("Costruzione tabelle report PDF")
            for j, item in enumerate(content):
                # Aggiungi intestazione del gruppo
                pdf.add_group_header(item.get("label"), group_input[j].filters)

                # Aggiungi tabella dei dati
                pdf.add_analytics_table(item.get("data"), measure, t_label)

                # Verifica spazio disponibile
                pdf.add_new_page_if_needed(100)

            # Genera il boxplot
            logger.debug("Costruzione boxplot report PDF")
            fig, img_stream = BoxplotGenerator.create_boxplot(content, t_label, group_input, measure)

            # Aggiungi spazio prima del boxplot
            pdf.ln(10)

            # Verifica se c'è abbastanza spazio per il boxplot
            pdf.add_new_page_if_needed(100)

            # Aggiungi il boxplot al PDF
            boxplot_width = 180  # Larghezza fissa
            pdf.image(img_stream, x=10, y=pdf.get_y(), w=boxplot_width)
            pdf.ln(100)  # Spazio per la prossima sezione

            # Chiudi la figura per liberare la memoria
            plt.close(fig)

            # Salva il PDF in un oggetto BytesIO e restituiscilo
            logger.debug("Scrittura byte array PDF")
            pdf_output = BytesIO()
            pdf.output(pdf_output)
            pdf_output.seek(0)

            return pdf_output

        except Exception as e:
            logger.error(f"Errore generazione report PDF: {str(e)}")
            return None
