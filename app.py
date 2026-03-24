import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA API ---
CHAVE_API = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=CHAVE_API)

# --- INTERFACE ---
st.set_page_config(page_title="Validador Fatecie", layout="centered")
st.title("Validador de Estágios - Fatecie")
st.markdown("Análise automática baseada no Roteiro Ana Julia.")

arquivo_pdf = st.file_uploader("Anexe o termo de compromisso", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("Validando regras de carga horária e dados..."):
        try:
            pdf_parts = [{"mime_type": "application/pdf", "data": arquivo_pdf.getvalue()}]

            prompt = """
            Você é um analista rigoroso de estágios da Fatecie. Analise o PDF e valide:
            
            1. SUPERVISOR: Deve ser 'professor regente' com formação na área, CPF e Telefone.
            2. CLÁUSULA 1.4 vs 2.2 (REGRA DE OURO):
               - Para Artes, História, Geografia e Biológicas:
                 * Se APENAS UMA área (Fundamental ou Médio) estiver marcada na 1.4 -> Carga Total deve ser 16h.
                 * Se AS DUAS áreas estiverem marcadas na 1.4 -> Carga Total deve ser 32h.
               - Para Letras (Port/Ing ou Port/Lib): 
                 * Segue a mesma lógica de 16h por nível, totalizando 32h se ambos marcados.
               - Verifique se o cálculo de dias na 2.2 bate com a carga diária (máx 6h) e semanal (máx 30h).
            3. ASSINATURAS: Se manuais, EXIGEM carimbo. Se via Clicksign (assinatura digital), o carimbo é dispensado.
            4. ATIVIDADES: Devem ser presenciais. CONHECIMENTOS: Devem ser expectativas.

            Retorne APENAS o JSON:
            {
              "resumo": { "ok": 0, "pendencias": 0, "atencao": 0 },
              "concedente": { "status": "ok|pendencia", "mensagem": "..." },
              "supervisor": { "status": "ok|pendencia", "mensagem": "..." },
              "vigencia_carga": { "status": "ok|pendencia", "mensagem": "..." },
              "atividades": { "status": "ok|pendencia", "mensagem": "..." },
              "assinaturas": { "status": "ok|atencao", "mensagem": "..." }
            }
            """

            model = genai.GenerativeModel('gemini-2.5-flash')
            resposta = model.generate_content([prompt, pdf_parts[0]])
            
            texto_limpo = resposta.text.strip().replace('```json', '').replace('```', '')
            dados = json.loads(texto_limpo)

            # Exibição dos cards
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 OK", dados['resumo']['ok'])
            col2.metric("🔴 Pendências", dados['resumo']['pendencias'])
            col3.metric("🟡 Atenção", dados['resumo']['atencao'])

            def exibir_card(titulo, info):
                if info['status'] == 'ok': st.success(f"**{titulo}**: {info['mensagem']}")
                elif info['status'] == 'pendencia': st.error(f"**{titulo}**: {info['mensagem']}")
                else: st.warning(f"**{titulo}**: {info['mensagem']}")

            exibir_card("Concedente", dados['concedente'])
            exibir_card("Supervisor", dados['supervisor'])
            exibir_card("Vigência e Carga Horária", dados['vigencia_carga'])
            exibir_card("Atividades", dados['atividades'])
            exibir_card("Assinaturas", dados['assinaturas'])

        except Exception as e:
            st.error(f"Erro na análise: {e}")
