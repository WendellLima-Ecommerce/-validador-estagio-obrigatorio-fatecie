import streamlit as st
import google.generativeai as genai
import json
import time

# --- CONFIGURAÇÃO DA API ---
# O sistema busca a chave nos 'Secrets' do Streamlit Cloud
CHAVE_API = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=CHAVE_API)

# --- INTERFACE ---
st.set_page_config(page_title="Validador Fatecie", layout="wide")
st.title("Validador de Estágios - UniFatecie")
st.markdown("Análise automática baseada nos roteiros oficiais e lógica de assinaturas.")

arquivo_pdf = st.file_uploader("Anexe o termo de compromisso", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("Analisando documento e cruzando regras..."):
        try:
            pdf_parts = [{"mime_type": "application/pdf", "data": arquivo_pdf.getvalue()}]

            # PROMPT MESTRE COM A NOVA LÓGICA DO ÁUDIO
            prompt = """
            Você é um analista do Setor de Estágios da UniFatecie. Analise o PDF e gere um parecer JSON:

            1. CARGA HORÁRIA (Roteiro Ana Julia):
               - Artes, História, Geografia e Biológicas: 16h se marcar 1 área na 1.4; 32h se marcar as duas [cite: 187-193].
               - Letras: 32h totais (16h Fundamental + 16h Médio) [cite: 178-181].
               - Máximo 6h/dia e 30h/semana[cite: 296, 528].

            2. SUPERVISOR:
               - Deve ser 'professor regente'. CPF, Telefone, E-mail e Formação na área são obrigatórios [cite: 198-199].

            3. ASSINATURAS E E-MAILS (Lógica do Áudio):
               - Se NÃO houver assinatura E carimbo do CONCEDENTE e do SUPERVISOR:
                 * Status: 'Atenção'. 
                 * Ação: 'Encaminhar para TODOS (Concedente, Supervisor e Estagiário)'.
               - Se ESTIVER ASSINADO E CARIMBADO (ou via ClickSign):
                 * Status: 'OK'.
                 * Ação: 'Encaminhar APENAS para o aluno'.

            Retorne apenas JSON:
            {
              "resumo": { "ok": 0, "pendencias": 0, "atencao": 0 },
              "cards": {
                "concedente": { "status": "ok|pendencia", "mensagem": "..." },
                "supervisor": { "status": "ok|pendencia", "mensagem": "..." },
                "vigencia_carga": { "status": "ok|pendencia", "mensagem": "..." },
                "assinaturas": { "status": "ok|atencao", "acao_envio": "...", "mensagem": "..." }
              },
              "mensagem_aluno": "MENSAGEM OFICIAL (Baseada no documento Respostas para Requerimentos)"
            }
            """

            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Lógica para evitar o erro 429 (Too Many Requests)
            try:
                resposta = model.generate_content([prompt, pdf_parts[0]])
            except Exception as e:
                if "429" in str(e):
                    st.warning("Limite de cota atingido. Aguardando 30 segundos para tentar novamente...")
                    time.sleep(30)
                    resposta = model.generate_content([prompt, pdf_parts[0]])
                else:
                    raise e

            dados = json.loads(resposta.text.strip().replace('```json', '').replace('```', ''))

            # --- EXIBIÇÃO ---
            col_esq, col_dir = st.columns([1, 1.5])

            with col_esq:
                st.subheader("Análise Técnica")
                for titulo, info in dados['cards'].items():
                    if info['status'] == 'ok': st.success(f"**{titulo.upper()}**: {info['mensagem']}")
                    elif info['status'] == 'atencao': st.warning(f"**{titulo.upper()}**: {info['mensagem']}")
                    else: st.error(f"**{titulo.upper()}**: {info['mensagem']}")
                
                # Exibe a ação recomendada do áudio
                st.write("---")
                st.write(f"### 📧 Ação de Envio: \n**{dados['cards']['assinaturas'].get('acao_envio', 'Análise pendente')}**")

            with col_dir:
                st.subheader("Parecer para o Sistema")
                st.text_area("Copie e cole este texto:", value=dados['mensagem_aluno'], height=350)

        except Exception as e:
            st.error(f"Erro na análise: {e}")
