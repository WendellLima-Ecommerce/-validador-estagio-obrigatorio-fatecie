import streamlit as st
import google.generativeai as genai
import json
import time

# --- CONFIGURAÇÃO DE SEGURANÇA E API ---
# A chave deve estar configurada nos "Secrets" do Streamlit com o nome GEMINI_API_KEY
if "GEMINI_API_KEY" not in st.secrets:
    st.error("Erro: Chave GEMINI_API_KEY não encontrada nos Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- FUNÇÃO DE CHAMADA COM RETRY (CONTORNA ERRO 429) ---
def chamar_gemini_com_retry(model, conteudo, max_tentativas=3):
    for tentativa in range(max_tentativas):
        try:
            return model.generate_content(conteudo)
        except Exception as e:
            if "429" in str(e) and tentativa < max_tentativas - 1:
                tempo_espera = (tentativa + 1) * 15  # Espera progressiva
                st.warning(f"Limite atingido. Reajustando em {tempo_espera}s... (Tentativa {tentativa+1}/{max_tentativas})")
                time.sleep(tempo_espera)
            else:
                raise e

# --- INTERFACE DO USUÁRIO ---
st.set_page_config(page_title="Validador Fatecie v3.0", layout="wide")
st.title("Validador de Estágios Obrigatórios - UniFatecie")
st.markdown("---")

arquivo_pdf = st.file_uploader("Anexe o termo de compromisso (PDF)", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("Analisando critérios técnicos e gerando parecer oficial..."):
        try:
            pdf_data = [{"mime_type": "application/pdf", "data": arquivo_pdf.getvalue()}]
            
            # PROMPT INTEGRAL COM TODAS AS REGRAS E MENSAGENS
            prompt_mestre = """
            Você é um analista sênior do Setor de Estágios da UniFatecie. Analise o PDF anexo com base nestas regras fixas:

            1. VALIDAÇÃO DE CARGA HORÁRIA (Roteiro Ana Julia):
               - Cursos (Artes, História, Geografia, Biológicas): 16h se 1 área marcada na 1.4; 32h se ambas [cite: 187-193].
               - Letras (Port/Ing ou Port/Lib): Sempre 32h totais (16h Fundamental II + 16h Médio) [cite: 178-181].
               - Limites Legais: Máx 6h diárias e 30h semanais[cite: 296, 528].
               - Verifique erro comum: Se o aluno preencher 400h para estágio de 32h, aponte erro de C.H. Insuficiente ou Excessiva conforme o curso [cite: 716-730].

            2. SUPERVISOR E CONCEDENTE:
               - Supervisor DEVE ser professor regente. Se for apenas diretor/coordenador, use a mensagem de indeferimento específica [cite: 198, 917-922].
               - Formação do supervisor deve ser na mesma área do curso do aluno [cite: 931-935].
               - CPF, Telefone e E-mail são obrigatórios [cite: 199, 890-894].

            3. LÓGICA DE ASSINATURAS E ENVIO (Baseada no Áudio):
               - Documento via Clicksign (Log de assinaturas digitais presente): Carimbo é DISPENSADO. Ação: 'Enviar apenas para o ALUNO'.
               - Documento com assinaturas manuais: EXIGE carimbo do local e do supervisor[cite: 202]. 
               - Se faltar assinatura ou carimbo manual: Ação: 'Enviar para TODOS (Concedente, Supervisor e Estagiário)'.

            4. MENSAGEM PARA O SISTEMA (Respostas para Requerimentos):
               - Use estritamente as nomenclaturas e textos do documento oficial .
               - DEFERIDO: Se tudo estiver OK [cite: 697-708].
               - INDEFERIDO: Especifique o motivo exato (C.H., Supervisor, Formação, Datas Divergentes, etc) [cite: 709-945].

            Retorne apenas JSON:
            {
              "resumo": { "ok": 0, "pendencias": 0, "atencao": 0 },
              "cards": {
                "concedente": { "status": "ok|pendencia", "mensagem": "..." },
                "supervisor": { "status": "ok|pendencia", "mensagem": "..." },
                "vigencia_carga": { "status": "ok|pendencia", "mensagem": "..." },
                "assinaturas": { "status": "ok|atencao", "acao_envio": "...", "mensagem": "..." }
              },
              "parecer_oficial": "TEXTO DA RESPOSTA PARA O ALUNO"
            }
            """

            # Uso do modelo Gemini 2.0 Flash conforme lista de permissão do usuário
            model = genai.GenerativeModel('gemini-2.5-flash')
            resposta = chamar_gemini_com_retry(model, [prompt_mestre, pdf_data[0]])
            
            # Limpeza e conversão do JSON
            json_texto = resposta.text.strip().replace('```json', '').replace('```', '')
            dados = json.loads(json_texto)

            # --- LAYOUT DE RESULTADOS ---
            col_cards, col_msg = st.columns([1, 1.2])

            with col_cards:
                st.subheader("📋 Status da Análise")
                for titulo, info in dados['cards'].items():
                    status = info['status']
                    if status == 'ok':
                        st.success(f"**{titulo.upper()}**: {info['mensagem']}")
                    elif status == 'atencao':
                        st.warning(f"**{titulo.upper()}**: {info['mensagem']}")
                    else:
                        st.error(f"**{titulo.upper()}**: {info['mensagem']}")
                
                st.info(f"### 📧 Ação Recomendada:\n**{dados['cards']['assinaturas'].get('acao_envio', 'Não identificada')}**")

            with col_msg:
                st.subheader("✍️ Parecer Final para o Sistema")
                st.text_area("Copie o texto abaixo e cole no portal da faculdade:", 
                             value=dados['parecer_oficial'], height=450)

        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")
