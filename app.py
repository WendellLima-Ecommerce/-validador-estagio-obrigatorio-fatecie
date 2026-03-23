import streamlit as st
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA API ---
# Cole sua chave aqui (Lembre-se de não compartilhar esse arquivo publicamente)
CHAVE_API = st.secrets["AIzaSyCZs7AZGgXKwGE9KdwQEjNa39UKzQnvL4I"]
genai.configure(api_key=CHAVE_API)

# --- INTERFACE DO SITE ---
st.set_page_config(page_title="Validador de Estágios", layout="centered")
st.title("Validador de Estágios - Fatecie")
st.markdown("Análise automática de termos de compromisso.")

# Área de Upload
arquivo_pdf = st.file_uploader("Anexe o termo de compromisso", type=["pdf"])

if arquivo_pdf is not None:
    with st.spinner("A Inteligência Artificial está lendo e cruzando as regras..."):
        try:
            # Prepara o PDF para a IA ler
            pdf_parts = [
                {
                    "mime_type": "application/pdf",
                    "data": arquivo_pdf.getvalue()
                }
            ]

            # O Prompt Mestre com as regras
            prompt = """
            Você é um analista administrativo de estágios da Fatecie. 
            Analise o documento PDF anexo e valide as regras:
            1. CNPJ da concedente preenchido.
            2. Supervisor precisa ser 'professor', formação compatível, com CPF e Telefone.
            3. Cláusula 1.4 preenchida corretamente (Médio e/ou Fundamental).
            4. Vigência e carga horária (máximo 6h/dia, 30h/semana).
            5. Atividades descrevendo a prática presencial e Conhecimentos descrevendo expectativas.
            6. Presença de assinaturas (exige carimbo se for física).

            Retorne APENAS um JSON válido. Não use blocos de código (```json), devolva apenas o texto bruto no formato abaixo:
            {
              "resumo": { "ok": 2, "pendencias": 1, "atencao": 0 },
              "concedente": { "status": "ok", "mensagem": "CNPJ e Área preenchidos corretamente." },
              "supervisor": { "status": "ok", "mensagem": "Professor com formação em Ciências Biológicas." },
              "vigencia_carga": { "status": "pendencia", "mensagem": "Data final incompatível com as 400h." },
              "atividades": { "status": "ok", "mensagem": "Atividades descritas." },
              "assinaturas": { "status": "atencao", "mensagem": "Faltam assinaturas físicas/carimbo." }
            }
            """

            # ---> AQUI ESTÁ A MÁGICA: Usando o modelo novo que a sua chave suporta! <---
            model = genai.GenerativeModel('gemini-2.5-flash')
            resposta = model.generate_content([prompt, pdf_parts[0]])
            
            # Limpa a resposta caso a IA coloque formatação de markdown e transforma em dicionário
            texto_limpo = resposta.text.strip().replace('```json', '').replace('```', '')
            dados = json.loads(texto_limpo)

            # --- EXIBIÇÃO DOS RESULTADOS NA TELA ---
            st.divider()
            
            # Placar do topo
            col1, col2, col3 = st.columns(3)
            col1.metric("🟢 OK", dados['resumo'].get('ok', 0))
            col2.metric("🔴 Pendências", dados['resumo'].get('pendencias', 0))
            col3.metric("🟡 Atenção", dados['resumo'].get('atencao', 0))

            st.write("### Detalhes da Análise")

            # Função auxiliar para pintar as caixinhas da cor certa
            def exibir_card(titulo, info):
                status = info.get('status', '').lower()
                mensagem = info.get('mensagem', '')
                if status == 'ok':
                    st.success(f"**{titulo}**\n\n{mensagem}")
                elif status == 'pendencia':
                    st.error(f"**{titulo}**\n\n{mensagem}")
                else:
                    st.warning(f"**{titulo}**\n\n{mensagem}")

            # Gera os cards visuais idênticos ao seu print
            exibir_card("Concedente", dados.get("concedente", {}))
            exibir_card("Supervisor", dados.get("supervisor", {}))
            exibir_card("Vigência e Carga Horária", dados.get("vigencia_carga", {}))
            exibir_card("Atividades", dados.get("atividades", {}))
            exibir_card("Assinaturas", dados.get("assinaturas", {}))

        except Exception as e:
            st.error(f"Ocorreu um erro durante a análise: {e}")