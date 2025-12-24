import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import json
import time
import os
from datetime import datetime

# ==============================================================================
# 1. SETUP & CORES (VISUAL OCTO RESTAURADO)
# ==============================================================================
st.set_page_config(page_title="Otti Workspace", layout="wide", page_icon="🐙")

# Paleta Oficial Octo (A que você gostou)
C_BG_MAIN     = "#001024" # Azul Profundo (Black Pearl)
C_SIDEBAR     = "#020A14" # Quase Preto
C_PURPLE_GRAD = "linear-gradient(90deg, #3F00FF 0%, #031A89 100%)" # Gradiente Roxo
C_TEXT_WHITE  = "#F8FAFC"
C_CARD_BG     = "rgba(3, 26, 137, 0.2)"
C_BORDER      = "#3F00FF"

if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# ==============================================================================
# 2. CONEXÃO
# ==============================================================================
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_connection():
    if not SUPABASE_URL: return None
    try: return create_client(SUPABASE_URL, SUPABASE_KEY)
    except: return None

supabase = init_connection()

# ==============================================================================
# 3. CSS BLINDADO (O VISUAL QUE FUNCIONAVA)
# ==============================================================================
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&family=Inter:wght@300;400;600&display=swap');

    /* --- GERAL --- */
    .stApp {{
        background-color: {C_BG_MAIN};
        color: {C_TEXT_WHITE};
        font-family: 'Inter', sans-serif;
    }}
    
    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] {{
        background-color: {C_SIDEBAR};
        border-right: 1px solid rgba(255,255,255,0.1);
    }}
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div {{
        color: #FFFFFF !important;
    }}

    /* --- TIPOGRAFIA --- */
    h1, h2, h3, h4 {{
        font-family: 'Sora', sans-serif;
        color: {C_TEXT_WHITE} !important;
        font-weight: 700;
    }}
    p, label, span {{ color: {C_TEXT_WHITE}; }}

    /* --- INPUTS (LOGIN LEGÍVEL) --- */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea {{
        background-color: #0B1221 !important;
        color: #FFFFFF !important;
        border: 1px solid {C_BORDER};
        border-radius: 8px;
    }}
    
    /* Selectbox */
    div[data-baseweb="select"] > div {{
        background-color: #0B1221 !important;
        color: #FFFFFF !important;
        border-color: {C_BORDER} !important;
    }}
    div[data-baseweb="select"] span {{ color: #FFFFFF !important; }}
    div[data-baseweb="popover"] {{ background-color: #0B1221 !important; }}
    div[data-baseweb="option"] {{ color: #FFFFFF !important; }}

    /* --- BOTÃO PRIMARY (ACESSAR / SALVAR) --- */
    button[kind="primary"] {{
        background: {C_PURPLE_GRAD} !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        font-family: 'Sora', sans-serif;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.85rem;
    }}
    button[kind="primary"]:hover {{
        opacity: 0.9;
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(63, 0, 255, 0.4);
    }}
    button[kind="primary"] p {{ color: #FFFFFF !important; }}

    /* --- BOTÃO SAIR (SIDEBAR) --- */
    /* Força borda e texto branco para contrastar com fundo escuro */
    section[data-testid="stSidebar"] button {{
        background-color: transparent !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }}
    section[data-testid="stSidebar"] button p {{ color: #FFFFFF !important; }}
    section[data-testid="stSidebar"] button:hover {{
        background-color: rgba(255,255,255,0.1) !important;
        border-color: #FFFFFF !important;
    }}

    /* --- CARDS KPI --- */
    div[data-testid="stMetric"] {{
        background-color: {C_CARD_BG};
        border: 1px solid {C_BORDER};
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }}
    div[data-testid="stMetricValue"] {{
        color: #E7F9A9 !important; /* Amarelo Neon Octo */
        font-family: 'Sora', sans-serif;
    }}
    label[data-testid="stMetricLabel"] {{ color: rgba(255,255,255,0.7) !important; }}

    /* --- LOGIN WRAPPER --- */
    .login-wrapper {{
        margin-top: 10vh;
        max-width: 400px;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
        padding: 2rem;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
    }}
    .login-wrapper div[data-testid="stImage"] {{ margin: 0 auto; display: block; }}
    
    #MainMenu, footer, header {{visibility: hidden;}}
    .block-container {{padding-top: 2rem;}}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 4. LOGIN (COM FORM E ENTER FUNCIONANDO)
# ==============================================================================
def render_logo(width=100):
    if os.path.exists("logo.png"): st.image("logo.png", width=width)
    else: st.markdown(f"<h1 style='color:{C_ELECTRIC}; margin:0; font-family:Sora; text-align:center;'>OCTO</h1>", unsafe_allow_html=True)

if 'usuario_logado' not in st.session_state: st.session_state['usuario_logado'] = None

def render_login_screen():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        render_logo(width=120)
        st.markdown(f"<h3 style='margin-bottom:30px; text-align:center;'>Otti Workspace</h3>", unsafe_allow_html=True)
        
        with st.form("login_master"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("ACESSAR SISTEMA", use_container_width=True, type="primary")
            
            if submitted:
                if not email or not senha:
                    st.warning("Preencha todos os campos.")
                else:
                    if not supabase: st.error("Banco de dados desconectado.")
                    else:
                        try:
                            res = supabase.table('acesso_painel').select('*').eq('email', email).eq('senha', senha).execute()
                            if res.data:
                                st.session_state['usuario_logado'] = res.data[0]
                                st.rerun()
                            else: st.error("Acesso Negado.")
                        except: st.error("Erro de conexão.")
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['usuario_logado']:
    render_login_screen()
    st.stop()

# ==============================================================================
# 5. DASHBOARD
# ==============================================================================
user = st.session_state['usuario_logado']
perfil = user['perfil']

# SIDEBAR
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    render_logo(width=130)
    st.markdown("---")
    st.write(f"Olá, **{user['nome_usuario']}**")
    
    # Toggle (apenas visual, forçamos dark no CSS)
    st.toggle("Modo Escuro", value=True, disabled=True)
    
    st.markdown("---")
    if st.button("SAIR"):
        st.session_state['usuario_logado'] = None
        st.rerun()

# DADOS
if not supabase: st.stop()
try: df_kpis = pd.DataFrame(supabase.table('view_dashboard_kpis').select("*").execute().data)
except:
    st.error("Erro ao carregar dados.")
    st.stop()

# SELECTOR
if perfil == 'admin':
    lista = df_kpis['nome_empresa'].unique()
    if 'last_cli' not in st.session_state: st.session_state['last_cli'] = lista[0]
    if st.session_state['last_cli'] not in lista: st.session_state['last_cli'] = lista[0]
    idx = list(lista).index(st.session_state['last_cli'])
    sel = st.sidebar.selectbox("Cliente:", lista, index=idx, key="cli_selector")
    st.session_state['last_cli'] = sel
    c_data = df_kpis[df_kpis['nome_empresa'] == sel].iloc[0]
else:
    filtro = df_kpis[df_kpis['cliente_id'] == user['cliente_id']]
    if filtro.empty: st.stop()
    c_data = filtro.iloc[0]

c_id = int(c_data['cliente_id'])
active = not bool(c_data['bot_pausado'])

# HEADER
c1, c2 = st.columns([3, 1])
with c1:
    st.title(c_data['nome_empresa'])
    st.caption(f"ID: {c_id}")
with c2:
    st.markdown("<br>", unsafe_allow_html=True)
    lbl = "⏸️ PAUSAR" if active else "▶️ ATIVAR"
    # Botão secundário fora da sidebar (usa CSS padrão do main)
    if st.button(lbl, use_container_width=True):
        supabase.table('clientes').update({'bot_pausado': active}).eq('id', c_id).execute()
        st.rerun()

st.divider()

# KPIS
tot = c_data['total_mensagens']
sav = round((tot * 1.5) / 60, 1)
rev = float(c_data['receita_total'] or 0)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Receita", f"R$ {rev:,.2f}")
k2.metric("Tempo", f"{sav}h")
k3.metric("Atendimentos", c_data['total_atendimentos'])
k4.metric("Status", "Online" if active else "Offline")
st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["Analytics", "Espião", "Produtos", "Agenda", "Cérebro"])

with tabs[0]:
    try:
        r_s = supabase.table('agendamentos_salao').select('created_at, valor_sinal_registrado, status, produto_salao_id').eq('cliente_id', c_id).execute().data
        r_p = supabase.table('agendamentos').select('created_at, valor_sinal_registrado, status, servico_id').eq('cliente_id', c_id).execute().data
        r_pr = supabase.table('produtos').select('id, nome').eq('cliente_id', c_id).execute().data
        map_pr = {p['id']: p['nome'] for p in r_pr} if r_pr else {}
        lista = []
        if r_s:
            for i in r_s: lista.append({'dt': i['created_at'], 'v': i.get('valor_sinal_registrado',0), 'st': i['status'], 'p': map_pr.get(i.get('produto_salao_id'), 'Salão')})
        if r_p:
            for i in r_p: lista.append({'dt': i['created_at'], 'v': i.get('valor_sinal_registrado',0), 'st': i['status'], 'p': map_pr.get(i.get('servico_id'), 'Serviço')})
        if lista:
            df = pd.DataFrame(lista)
            df['dt'] = pd.to_datetime(df['dt'], format='mixed').dt.date
            df = df[df['st'] != 'Cancelado']
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                st.markdown("##### Receita Diária")
                df_g = df.groupby('dt')['v'].sum().reset_index()
                fig = px.line(df_g, x='dt', y='v', template='plotly_dark', markers=True)
                fig.update_traces(line_color="#3F00FF", line_width=3)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': 'white'})
                st.plotly_chart(fig, use_container_width=True)
            with c_g2:
                st.markdown("##### Produtos Mais Vendidos")
                df_top = df['p'].value_counts().reset_index().head(5)
                fig2 = px.bar(df_top, x='count', y='p', orientation='h', template='plotly_dark')
                fig2.update_traces(marker_color="#5396FF")
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={'color': 'white'})
                st.plotly_chart(fig2, use_container_width=True)
        else: st.info("Sem dados.")
    except Exception as e: st.error(f"Erro Visual: {e}")

with tabs[1]:
    cl, cr = st.columns([1, 2])
    with cl:
        try:
            rc = supabase.table('conversas').select('id, cliente_wa_id, updated_at, metadata').eq('cliente_id', c_id).order('updated_at', desc=True).limit(15).execute()
            if rc.data:
                opts = {}
                for c in rc.data:
                    dt = pd.to_datetime(c['updated_at']).strftime('%d/%m %H:%M') if c['updated_at'] else ""
                    m = c.get('metadata') or {}
                    nm = m.get('push_name') or c['cliente_wa_id']
                    opts[f"{nm} ({dt})"] = c['id']
                sel = st.radio("Conversas:", list(opts.keys()))
                sid = opts[sel]
                if st.button("Atualizar"): st.rerun()
            else: sid = None
        except: sid = None
    with cr:
        if sid:
            try:
                rm = supabase.table('historico_mensagens').select('*').eq('conversa_id', sid).order('created_at', desc=True).limit(40).execute()
                msgs = rm.data[::-1] if rm.data else []
                cont = st.container(height=500)
                with cont:
                    for m in msgs:
                        role = m['role']
                        av = "👤" if role=='user' else "🐙"
                        with st.chat_message(role, avatar=av): st.write(m['content'])
            except: pass

with tabs[2]:
    c1, c2 = st.columns([2,1])
    with c1:
        rp = supabase.table('produtos').select('nome, categoria, ativo').eq('cliente_id', c_id).order('nome').execute()
        if rp.data: st.dataframe(pd.DataFrame(rp.data), use_container_width=True, hide_index=True)
    with c2:
        with st.form("add"):
            st.write("Novo Item")
            n = st.text_input("Nome")
            c = st.text_input("Categoria")
            p = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Salvar", type="primary"):
                js = {"preco_padrao": p, "duracao_minutos": 60}
                supabase.table('produtos').insert({"cliente_id": c_id, "nome": n, "categoria": c, "ativo": True, "regras_preco": json.dumps(js)}).execute()
                st.rerun()

with tabs[3]:
    st.subheader("Próximos Agendamentos")
    try:
        df_final = pd.DataFrame()
        rs = supabase.table('agendamentos_salao').select('data_reserva, valor_total_registrado, cliente_final_waid').eq('cliente_id', c_id).order('created_at', desc=True).limit(50).execute()
        rv = supabase.table('agendamentos').select('data_hora_inicio, valor_total_registrado').eq('cliente_id', c_id).order('created_at', desc=True).limit(50).execute()
        if rs.data:
            d = pd.DataFrame(rs.data)
            d['Data'] = pd.to_datetime(d['data_reserva']).dt.strftime('%d/%m/%Y')
            df_final = d[['Data', 'valor_total_registrado', 'cliente_final_waid']]
            df_final.columns = ['Data', 'Valor (R$)', 'Cliente']
        elif rv.data:
            d = pd.DataFrame(rv.data)
            d['Data/Hora'] = pd.to_datetime(d['data_hora_inicio']).dt.strftime('%d/%m/%Y %H:%M')
            df_final = d[['Data/Hora', 'valor_total_registrado']]
            df_final.columns = ['Data/Hora', 'Valor (R$)']
        if not df_final.empty: st.dataframe(df_final, use_container_width=True, hide_index=True)
        else: st.info("Agenda vazia.")
    except Exception as e: st.error(f"Erro agenda: {e}")

# 5. CÉREBRO (CORREÇÃO ERRO VÍRGULA + VISUAL LIMPO)
if perfil == 'admin' and len(tabs) > 4:
    with tabs[4]:
        st.subheader("Configuração da IA")
        try:
            res = supabase.table('clientes').select('config_fluxo, prompt_full').eq('id', c_id).execute()
            if res.data:
                d = res.data[0]
                curr_c = d.get('config_fluxo') or {}
                if isinstance(curr_c, str): curr_c = json.loads(curr_c)
                
                # --- COLUNA 1: PROMPT ---
                c_p1, c_p2 = st.columns([2, 1])
                with c_p1:
                    st.markdown("##### 1. Personalidade (Prompt)")
                    new_p = st.text_area("", value=d.get('prompt_full','') or '', height=350)

                # --- COLUNA 2: ÁUDIO E VOZ ---
                with c_p2:
                    st.markdown("##### 2. Áudio e Voz")
                    vozes = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
                    v_atual = curr_c.get('openai_voice', 'alloy')
                    if v_atual not in vozes: v_atual = 'alloy'
                    nova_voz = st.selectbox("Voz da IA:", vozes, index=vozes.index(v_atual))
                    
                    # CORREÇÃO DO ERRO '0,8' PARA O SLIDER
                    raw_temp = curr_c.get('temperature', 0.5)
                    try:
                        if isinstance(raw_temp, str): raw_temp = raw_temp.replace(',', '.')
                        temp_atual = float(raw_temp)
                    except: temp_atual = 0.5
                    
                    nova_temp = st.slider("Criatividade da Resposta:", min_value=0.0, max_value=1.0, value=temp_atual, step=0.1)
                    
                    with st.expander("🗣️ Guia de Vozes"):
                        st.markdown("""
                        - **Alloy:** Neutra
                        - **Echo:** Masculina/Suave
                        - **Onyx:** Masculina/Grave
                        - **Nova:** Feminina/Alegre
                        - **Shimmer:** Feminina/Sofisticada
                        """)

                # --- COLUNA 3: JSON TÉCNICO (TEXT_AREA = SEGURANÇA) ---
                st.markdown("##### 3. Configuração Técnica (JSON)")
                st.caption("⚠️ Edite com cuidado.")
                
                view_json = curr_c.copy()
                if 'openai_voice' in view_json: del view_json['openai_voice']
                if 'temperature' in view_json: del view_json['temperature']
                
                json_str = st.text_area("", value=json.dumps(view_json, indent=4, ensure_ascii=False), height=300)
                
                if st.button("SALVAR CÉREBRO", type="primary"):
                    try:
                        final_json = json.loads(json_str)
                        final_json['openai_voice'] = nova_voz
                        final_json['temperature'] = nova_temp # Salva float puro (0.8)
                        
                        supabase.table('clientes').update({
                            'config_fluxo': final_json,
                            'prompt_full': new_p
                        }).eq('id', c_id).execute()
                        st.success("Salvo com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("Erro no JSON.")
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

        except Exception as e: st.error(f"Erro: {e}")
