import streamlit as st
import pandas as pd
import qrcode
from PIL import Image
import io
import zipfile

# Librerie per la creazione geometrica del PDF
from reportlab.lib.pagesizes import a4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage
from reportlab.lib.units import cm

st.set_page_config(page_title="Generatore QR Code Multiformato", page_icon="🔲", layout="centered")

st.title("🔲 Generatore QR Code Avanzato")
st.write(
    "Carica un file CSV con i tuoi indirizzi web. Scegli se esportare le singole immagini BMP "
    "oppure generare direttamente un foglio PDF A4 con i QR code impaginati esattamente a **4x4 cm**."
)

# Parametri costanti per la conversione e qualità
DPI = 300
CM_SIZE = 4.0
pixel_size = int((CM_SIZE / 2.54) * DPI)  # ~472 pixel per la massima nitidezza

uploaded_file = st.file_uploader("Scegli un file CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.success("File CSV caricato con successo!")
        
        # Anteprima
        st.write("### Anteprima dei dati:")
        st.dataframe(df.head(3))
        
        # Selezione colonna URL
        columns = df.columns.tolist()
        selected_column = st.selectbox("Seleziona la colonna che contiene i link web:", columns)
        
        # INTERFACCIA DI SCELTA: ZIP o PDF
        output_format = st.radio(
            "Scegli il formato di output desiderato:",
            (
                "Archivio ZIP con singoli file BMP (4x4 cm, 300 DPI)", 
                "Documento PDF (Impaginazione a griglia, QR Code di 4x4 cm)"
            )
        )
        
        if st.button("Avvia Elaborazione"):
            urls = df[selected_column].dropna().tolist()
            
            if not urls:
                st.error("La colonna selezionata non contiene link validi.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # --- OPZIONE 1: GENERAZIONE ARCHIVIO ZIP (FILE BMP SINGOLI) ---
                if "ZIP" in output_format:
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for index, url in enumerate(urls, start=1):
                            status_text.text(f"Generazione BMP {index} di {len(urls)}...")
                            
                            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                            qr.add_data(str(url))
                            qr.make(fit=True)
                            
                            qr_img = qr.make_image(fill_color="black", back_color="white").convert('1')
                            qr_resized = qr_img.resize((pixel_size, pixel_size), resample=Image.NEAREST)
                            
                            img_buffer = io.BytesIO()
                            qr_resized.save(img_buffer, format="BMP", dpi=(DPI, DPI))
                            img_buffer.seek(0)
                            
                            zip_file.writestr(f"qr_{index}.bmp", img_buffer.getvalue())
                            progress_bar.progress(index / len(urls))
                            
                    status_text.text("Archivio ZIP pronto per il download!")
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="📥 Scarica l'archivio ZIP (BMP)",
                        data=zip_buffer,
                        file_name="qr_codes_bmp.zip",
                        mime="application/zip"
                    )
                
                # --- OPZIONE 2: GENERAZIONE UNICO FILE PDF ---
                else:
                    pdf_buffer = io.BytesIO()
                    
                    # Definiamo il documento in formato A4 con margini di 1.5 cm
                    doc = SimpleDocTemplate(
                        pdf_buffer, 
                        pagesize=a4, 
                        leftMargin=1.5*cm, rightMargin=1.5*cm, 
                        topMargin=1.5*cm, bottomMargin=1.5*cm
                    )
                    
                    story = []
                    pdf_images = []
                    
                    for index, url in enumerate(urls, start=1):
                        status_text.text(f"Elaborazione e vettorializzazione QR {index} di {len(urls)}...")
                        
                        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
                        qr.add_data(str(url))
                        qr.make(fit=True)
                        
                        qr_img = qr.make_image(fill_color="black", back_color="white").convert('1')
                        qr_resized = qr_img.resize((pixel_size, pixel_size), resample=Image.NEAREST)
                        
                        # Per inserire l'immagine nel PDF manteniamo la massima compatibilità convertendo in PNG temporaneo
                        png_buffer = io.BytesIO()
                        qr_resized.save(png_buffer, format="PNG")
                        png_buffer.seek(0)
                        
                        # Definiamo l'immagine per il PDF forzando le dimensioni fisiche a 4.0 x 4.0 cm
                        rl_img = RLImage(png_buffer, width=4.0*cm, height=4.0*cm)
                        pdf_images.append(rl_img)
                        progress_bar.progress(index / len(urls))
                    
                    # Organizziamo i QR code in una griglia di 4 colonne per riga
                    grid_data = []
                    current_row = []
                    for img in pdf_images:
                        current_row.append(img)
                        if len(current_row) == 4:
                            grid_data.append(current_row)
                            current_row = []
                    if current_row:
                        # Se l'ultima riga è incompleta, aggiungiamo celle vuote per non scompaginare la tabella
                        while len(current_row) < 4:
                            current_row.append("")
                        grid_data.append(current_row)
                    
                    # Generazione della tabella con spaziatura tra i QR Code
                    # 4.2 cm di larghezza colonna garantisce 2 millimetri di spazio vuoto protettivo tra un QR e l'altro
                    qr_table = Table(grid_data, colWidths=[4.3*cm]*4)
                    qr_table.setStyle(TableStyle([
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 12), # Spazio verticale tra le righe
                        ('TOPPADDING', (0,0), (-1,-1), 12),
                    ]))
                    
                    story.append(qr_table)
                    doc.build(story)
                    
                    status_text.text("Documento PDF generato con successo!")
                    pdf_buffer.seek(0)
                    
                    st.download_button(
                        label="📥 Scarica il documento PDF pronto per la stampa",
                        data=pdf_buffer,
                        file_name="catalogo_qr_4x4cm.pdf",
                        mime="application/pdf"
                    )
                    
    except Exception as e:
        st.error(f"Si è verificato un errore durante l'elaborazione: {e}")