import streamlit as st
import pandas as pd
import qrcode
from PIL import Image
import io
import zipfile

# Configurazione della pagina Streamlit
st.set_page_config(page_title="Generatore QR Code BMP", page_icon="🔲", layout="centered")

st.title("🔲 Generatore QR Code in BMP (4x4 cm)")
st.write(
    "Carica un file CSV contenente i tuoi indirizzi web. Lo script calcolerà la densità a "
    "**300 DPI** per restituirti immagini `.bmp` pronte per la stampa di dimensioni esatte **4x4 cm** (472x472 px)."
)

# Costanti di conversione cm -> pixel a 300 DPI
DPI = 300
CM_SIZE = 4.0
pixel_size = int((CM_SIZE / 2.54) * DPI)  # Risultato: ~472 pixel

# Caricamento del file CSV tramite interfaccia grafica
uploaded_file = st.file_uploader("Scegli un file CSV", type=["csv"])

if uploaded_file is not None:
    try:
        # Lettura automatica con pandas
        df = pd.read_csv(uploaded_file)
        st.success("File CSV caricato correttamente!")
        
        # Mostra una piccola anteprima della tabella all'utente
        st.write("### Anteprima del file caricato:")
        st.dataframe(df.head(5))
        
        # Selezione dinamica della colonna che contiene i link
        columns = df.columns.tolist()
        selected_column = st.selectbox("Seleziona la colonna che contiene i link web:", columns)
        
        # Bottone di avvio processo
        if st.button("Elabora e Genera QR Code"):
            urls = df[selected_column].dropna().tolist()
            
            if not urls:
                st.error("La colonna selezionata è vuota o non contiene dati validi.")
            else:
                # Creazione di un archivio ZIP in memoria (in-memory bytes buffer)
                zip_buffer = io.BytesIO()
                
                # Indicatori di progresso grafici in Streamlit
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for index, url in enumerate(urls, start=1):
                        status_text.text(f"Elaborazione QR {index} di {len(urls)}...")
                        
                        # Generazione del QR Code strutturale
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(str(url))
                        qr.make(fit=True)
                        
                        # Conversione in immagine pura Bianco/Nero (modalità binaria "1")
                        qr_img = qr.make_image(fill_color="black", back_color="white").convert('1')
                        
                        # Ridimensionamento esatto a 472x472 px (Image.NEAREST mantiene i bordi nitidi)
                        qr_resized = qr_img.resize((pixel_size, pixel_size), resample=Image.NEAREST)
                        
                        # Salvataggio temporaneo dell'immagine in un flusso di byte
                        img_buffer = io.BytesIO()
                        qr_resized.save(img_buffer, format="BMP", dpi=(DPI, DPI))
                        img_buffer.seek(0)
                        
                        # Inserimento del file .bmp dentro lo ZIP
                        filename = f"qr_{index}.bmp"
                        zip_file.writestr(filename, img_buffer.getvalue())
                        
                        # Avanzamento della barra di caricamento
                        progress_bar.progress(index / len(urls))
                
                status_text.text("Generazione completata con successo!")
                
                # Reset del puntatore del buffer ZIP prima del download
                zip_buffer.seek(0)
                
                # Pulsante nativo di Streamlit per scaricare lo ZIP risultante
                st.download_button(
                    label="📥 Scarica l'archivio ZIP con tutti i file BMP",
                    data=zip_buffer,
                    file_name="qr_codes_4x4cm_bmp.zip",
                    mime="application/zip"
                )
                
    except Exception as e:
        st.error(f"Si è verificato un errore nel processare il file: {e}")