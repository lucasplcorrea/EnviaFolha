import streamlit as st
import subprocess
import os
import pandas as pd
from datetime import datetime
import sys
import time
from status_manager import StatusManager

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

# Inicializar StatusManager
status_manager = StatusManager()

# Seção de Status de Execução
st.subheader("📊 Status de Execução")
status = status_manager.get_status()

if status["is_running"]:
    st.warning("🔄 **Execução em andamento!**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Progresso", f"{status['processed_employees']}/{status['total_employees']}")
    with col2:
        st.metric("Sucessos", status['successful_sends'])
    with col3:
        st.metric("Falhas", status['failed_sends'])
    
    # Barra de progresso
    progress = status_manager.get_progress_percentage()
    st.progress(progress / 100)
    st.text(f"Progresso: {progress:.1f}%")
    
    # Status atual
    if status["current_step"]:
        st.info(f"**Etapa atual:** {status['current_step']}")
    
    if status["current_employee"]:
        st.info(f"**Funcionário atual:** {status['current_employee']}")
    
    # Botão para atualizar status
    if st.button("🔄 Atualizar Status", key="refresh_status"):
        st.rerun()
    
    # Botão para resetar (emergência)
    if st.button("🛑 Parar Execução (Emergência)", key="stop_execution"):
        status_manager.reset_status()
        st.success("Execução interrompida!")
        st.rerun()

else:
    if status["end_time"]:
        st.success("✅ **Última execução finalizada**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Processado", status['processed_employees'])
        with col2:
            st.metric("Sucessos", status['successful_sends'])
        with col3:
            st.metric("Falhas", status['failed_sends'])
    else:
        st.info("ℹ️ **Nenhuma execução em andamento**")

st.markdown("---")

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
        df['ID_Unico_Str'] = df['ID_Unico'].apply(lambda x: str(x).zfill(9))
        df['Arquivo Esperado'] = df['ID_Unico_Str'].apply(lambda x: f"{x}_holerite_setembro_2025.pdf")
        df['Será Enviado?'] = df['Arquivo Esperado'].apply(lambda x: 'Sim' if x in arquivos_segmentados else 'Não')
        
        # Adicionar status de envio se houver dados de execução
        status = status_manager.get_status()
        if status["employees_status"]:
            def get_send_status(id_unico):
                id_str = str(id_unico).zfill(9)
                if id_str in status["employees_status"]:
                    emp_status = status["employees_status"][id_str]["status"]
                    if emp_status == "success":
                        return "✅ Enviado"
                    elif emp_status == "failed":
                        return "❌ Falha"
                    elif emp_status == "processing":
                        return "🔄 Processando"
                return "⏳ Aguardando"
            
            df['Status de Envio'] = df['ID_Unico'].apply(get_send_status)
            
            # Mostrar tabela com status
            st.dataframe(df[['Nome_Colaborador', 'Telefone', 'Arquivo Esperado', 'Será Enviado?', 'Status de Envio']])
            
            # Painel detalhado de status por funcionário
            st.subheader("📋 Status Detalhado por Funcionário")
            
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox(
                    "Filtrar por status:",
                    ["Todos", "✅ Enviado", "❌ Falha", "🔄 Processando", "⏳ Aguardando"],
                    key="status_filter"
                )
            
            with col2:
                search_name = st.text_input("Buscar por nome:", key="search_name")
            
            # Aplicar filtros
            filtered_df = df.copy()
            if status_filter != "Todos":
                filtered_df = filtered_df[filtered_df['Status de Envio'] == status_filter]
            
            if search_name:
                filtered_df = filtered_df[filtered_df['Nome_Colaborador'].str.contains(search_name, case=False, na=False)]
            
            # Mostrar resultados filtrados
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    id_str = str(row['ID_Unico']).zfill(9)
                    
                    with st.expander(f"{row['Status de Envio']} {row['Nome_Colaborador']} (ID: {id_str})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Telefone:** {row['Telefone']}")
                            st.write(f"**Arquivo:** {row['Arquivo Esperado']}")
                            st.write(f"**Disponível:** {row['Será Enviado?']}")
                        
                        with col2:
                            if id_str in status["employees_status"]:
                                emp_data = status["employees_status"][id_str]
                                st.write(f"**Status:** {emp_data['status']}")
                                st.write(f"**Mensagem:** {emp_data['message']}")
                                if emp_data.get('timestamp'):
                                    timestamp = datetime.fromisoformat(emp_data['timestamp'])
                                    st.write(f"**Última atualização:** {timestamp.strftime('%d/%m/%Y %H:%M:%S')}")
            else:
                st.info("Nenhum funcionário encontrado com os filtros aplicados.")
        else:
            st.dataframe(df[['Nome_Colaborador', 'Telefone', 'Arquivo Esperado', 'Será Enviado?']])
            
    except Exception as e:
        st.error(f"Erro ao carregar colaboradores: {e}")
else:
    st.info("Envie e segmente arquivos para ver a prévia de envio.")

# Envio final
if st.button("📤 Enviar holerites via Evolution API", key="btn_enviar", disabled=status_manager.is_running()):
    if status_manager.is_running():
        st.error("❌ Já existe uma execução em andamento. Aguarde a conclusão.")
    else:
        with st.status("📤 Enviando arquivos via API...", expanded=True) as status_widget:
            result = subprocess.run(
                [sys.executable, "send_holerites_evolution.py"],
                capture_output=True,
                text=True
            )
            st.code(result.stdout)
            if result.stderr:
                st.error(result.stderr)
                status_widget.update(label="❌ Erro no envio.", state="error")
            else:
                st.success("✅ Todos os holerites foram enviados com sucesso!")
                status_widget.update(label="✅ Envio concluído.", state="complete")

# Visualizar arquivos segmentados
with st.expander("📄 Ver arquivos segmentados gerados"):
    files = os.listdir(OUTPUT_DIR)
    if files:
        for f in sorted(files):
            st.text(f)
    else:
        st.info("Nenhum holerite segmentado encontrado ainda.")
