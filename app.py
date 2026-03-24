import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA API ---
CHAVE_API = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=CHAVE_API)

# --- INTERFACE ---
st.set_page_config(page_title="Validador Fatecie", layout="wide")
st.title("Validador de Estágios - UniFatecie")
st.markdown("Análise automática e geração de pareceres oficiais.")

arquivo_pdf = st.file_uploader("Anexe o termo de compromisso", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("Analisando documento e gerando parecer..."):
        try:
            pdf_parts = [{"mime_type": "application/pdf", "data": arquivo_pdf.getvalue()}]

            prompt = """
            Você é um analista do Setor de Estágios da UniFatecie. Sua tarefa é analisar o PDF e gerar um parecer baseado nestas regras:

            1. REGRAS DE CARGA HORÁRIA (Roteiro Ana Julia):
               - Artes, História, Geografia e Biológicas: 16h se marcar 1 área na Cláusula 1.4; 32h se marcar as duas.
               - Letras: 32h totais (16h Fundamental + 16h Médio).
               - Limite de 6h/dia e 30h/semana.
            2. REGRAS DE SUPERVISOR:
               - Deve ser 'professor regente'[cite: 917]. Não pode ser apenas diretor/coordenador[cite: 198].
               - Deve ter formação na área do curso[cite: 931]. CPF e Telefone são obrigatórios[cite: 889].
            3. REGRAS DE ASSINATURA:
               - Manuais exigem carimbo[cite: 202]. Assinaturas via Clicksign dispensam carimbo[cite: 704].

            PARECER FINAL (Use os modelos do documento 'Respostas para Requerimentos'):
            - Se TUDO estiver OK: Use o modelo 'DEFERIDO' .
            - Se C.H. for menor que a exigida: Use 'INDEFERIMENTO POR C.H INSUFICIENTE' [cite: 725-730].
            - Se supervisor não for regente: Use 'INDEFERIDO - SUPERVISOR DEVE SER O PROFESSOR REGENTE' [cite: 918-922].
            - Se faltar CPF/Telefone: Use 'INDEFERIDO - SEM CPF E TELEFONE' [cite: 890-894].
            - Se formação for incompatível: Use 'INDEFERIDO - SUPERVISOR SEM FORMAÇÃO NA ÁREA' [cite: 932-935].

            Retorne apenas JSON:
            {
              "resumo": { "ok": 0, "pendencias": 0, "atencao": 0 },
              "cards": {
                "concedente": { "status": "ok|pendencia", "mensagem": "..." },
                "supervisor": { "status": "ok|pendencia", "mensagem": "..." },
                "vigencia_carga": { "status": "ok|pendencia", "mensagem": "..." },
                "assinaturas": { "status": "ok|atencao", "mensagem": "..." }
              },
              "mensagem_aluno": "TEXTO DA MENSAGEM OFICIAL AQUI"
            }
            """

            model = genai.GenerativeModel('gemini-2.5-flash')
            resposta = model.generate_content([prompt, pdf_parts[0]])
            dados = json.loads(resposta.text.strip().replace('```json', '').replace('```', ''))

            # --- EXIBIÇÃO ---
            col_esq, col_dir = st.columns([1, 1.5])

            with col_esq:
                st.subheader("Análise dos Cards")
                for titulo, info in dados['cards'].items():
                    if info['status'] == 'ok': st.success(f"**{titulo.upper()}**: {info['mensagem']}")
                    else: st.error(f"**{titulo.upper()}**: {info['mensagem']}")

            with col_dir:
                st.subheader("Mensagem para o Aluno")
                st.info("Copie e cole a mensagem abaixo no sistema:")
                st.text_area("Parecer Final", value=dados['mensagem_aluno'], height=300)

        except Exception as e:
            st.error(f"Erro: {e}")
