import streamlit as st
import subprocess
import os
from datetime import datetime
import sys

# Diretórios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "holerites_formatados_final"

# Garantir que as pastas existam
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configuração da página
st.set_page_config(page_title="Envio de Holerites", page_icon="📄")
st.title("📄 Sistema de Envio de Holerites")

st.markdown("""
1️⃣ **Faça upload dos arquivos PDF (um por empresa)**  
2️⃣ **Clique em 'Segmentar Holerites' para processar todos os PDFs enviados**  
3️⃣ **Clique em 'Enviar Holerites' para utilizar a Evolution API**
""")

# ================================
# 🔼 UPLOAD DOS ARQUIVOS
# ================================
uploaded_files = st.file_uploader(
    "📎 Enviar arquivos PDF de holerites (você pode enviar mais de um)",
    type="pdf",
    accept_multiple_files=True,
    key="upload_pdf"
)

if uploaded_files:
    for file in uploaded_files:
        file_path = os.path.join(UPLOAD_DIR, file.name)
        with open(file_path, "wb") as f:
            f.write(file.read())
        st.success(f"Arquivo '{file.name}' salvo com sucesso.")

# ================================
# 🔨 SEGMENTAÇÃO DOS ARQUIVOS
# ================================
if st.button("📂 Segmentar holerites", key="btn_segmentar"):
    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]
    if not files:
        st.warning("Nenhum arquivo PDF encontrado na pasta de uploads.")
    else:
        for pdf in files:
            full_path = os.path.join(UPLOAD_DIR, pdf)
            st.write(f"➡️ Segmentando: `{pdf}`")
            result = subprocess.run(
                [sys.executable, "manus.py", full_path],
                capture_output=True,
                text=True
            )
            st.code(result.stdout)
            if result.stderr:
                st.error(result.stderr)
        st.success("Todos os arquivos foram segmentados com sucesso.")

# ================================
# 📤 ENVIO DOS HOLERITES
# ================================
if st.button("📤 Enviar holerites via Evolution API", key="btn_enviar"):
    st.info("Iniciando envio...")
    result = subprocess.run(
        [sys.executable, "send_holerites_evolution.py"],
        capture_output=True,
        text=True
    )
    st.code(result.stdout)
    if result.stderr:
        st.error(result.stderr)
    else:
        st.success("Todos os holerites foram enviados com sucesso!")

# ================================
# 📁 LISTA DE ARQUIVOS GERADOS
# ================================
with st.expander("📄 Arquivos segmentados gerados", expanded=False):
    files = os.listdir(OUTPUT_DIR)
    if files:
        for f in sorted(files):
            st.text(f)
    else:
        st.info("Nenhum holerite segmentado encontrado ainda.")
