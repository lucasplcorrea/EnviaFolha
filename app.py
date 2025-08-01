import streamlit as st
import subprocess
import os
import pandas as pd
from datetime import datetime
import sys

# Diretórios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "holerites_formatados_final"
ENVIADOS_DIR = "enviados"

# Garante que as pastas existem
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ENVIADOS_DIR, exist_ok=True)

# Configurações da página
st.set_page_config(page_title="Envio de Holerites", page_icon="📄")
st.title("📄 Sistema de Envio de Holerites")

st.markdown("""
### 📝 Etapas:
1️⃣ Faça upload dos arquivos PDF de holerite (um por empresa)  
2️⃣ Clique em **Segmentar Holerites**  
3️⃣ Veja a prévia de quem irá receber os arquivos  
4️⃣ Clique em **Enviar Holerites** para usar a Evolution API
""")

# Upload de arquivos
with st.status("Aguardando upload de arquivos", expanded=False):
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
            st.success(f"✅ {file.name} salvo em uploads/")

# Segmentação dos PDFs
if st.button("📂 Segmentar todos os holerites enviados", key="btn_segmentar"):
    files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith(".pdf")]
    if not files:
        st.warning("Nenhum arquivo PDF encontrado em uploads/.")
    else:
        with st.status("Segmentando holerites...", expanded=True) as status:
            for pdf in files:
                full_path = os.path.join(UPLOAD_DIR, pdf)
                st.write(f"📎 Processando: `{pdf}`")
                result = subprocess.run(
                    [sys.executable, "manus.py", full_path],
                    capture_output=True,
                    text=True
                )
                st.code(result.stdout)
                if result.stderr:
                    st.error(result.stderr)
            status.update(label="✅ Segmentação finalizada.", state="complete")

# Pré-visualização dos destinatários
if os.path.exists("Colaboradores.xlsx") and os.listdir(OUTPUT_DIR):
    st.subheader("👥 Prévia dos destinatários")
    try:
        df = pd.read_excel("Colaboradores.xlsx")
        arquivos_segmentados = set(os.listdir(OUTPUT_DIR))
        df['Arquivo Esperado'] = df['ID_Unico'].apply(lambda x: f"{str(x).zfill(9)}_holerite_junho_2025.pdf")
        df['Será Enviado?'] = df['Arquivo Esperado'].apply(lambda x: 'Sim' if x in arquivos_segmentados else 'Não')
        st.dataframe(df[['Nome_Colaborador', 'Telefone', 'Arquivo Esperado', 'Será Enviado?']])
    except Exception as e:
        st.error(f"Erro ao carregar colaboradores: {e}")
else:
    st.info("Envie e segmente arquivos para ver a prévia de envio.")

# Envio final
if st.button("📤 Enviar holerites via Evolution API", key="btn_enviar"):
    with st.status("📤 Enviando arquivos via API...", expanded=True) as status:
        result = subprocess.run(
            [sys.executable, "send_holerites_evolution.py"],
            capture_output=True,
            text=True
        )
        st.code(result.stdout)
        if result.stderr:
            st.error(result.stderr)
            status.update(label="❌ Erro no envio.", state="error")
        else:
            st.success("✅ Todos os holerites foram enviados com sucesso!")
            status.update(label="✅ Envio concluído.", state="complete")

# Visualizar arquivos segmentados
with st.expander("📄 Ver arquivos segmentados gerados"):
    files = os.listdir(OUTPUT_DIR)
    if files:
        for f in sorted(files):
            st.text(f)
    else:
        st.info("Nenhum holerite segmentado encontrado ainda.")
