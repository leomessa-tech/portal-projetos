import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import altair as alt

import database
import logic
import email_service
import i18n
import report_generator

# Inicialização do Banco de Dados
database.init_db()

# Recuperar idioma salvo ou padrão
if "idioma" not in st.session_state:
    configs_db = database.obter_configuracoes()
    st.session_state["idioma"] = configs_db.get("idioma_padrao", "pt_BR")

cur_lang = st.session_state["idioma"]

def _t(chave: str, **kwargs) -> str:
    return i18n.t(chave, cur_lang, **kwargs)

# Configuração da Página
st.set_page_config(
    page_title=_t("page_title"),
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada
st.markdown("""
<style>
    .metric-card {
        background: #ffffff;
        padding: 18px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .metric-title {
        color: #64748b;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 4px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 10px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CONTROLE DE ACESSO (TELA DE LOGIN E CADASTRO)
# ==============================================================================
if not st.session_state.get("autenticado", False):
    # Cabeçalho da Tela de Login com Seletor de Idioma
    col_top1, col_top2 = st.columns([3, 1])
    with col_top2:
        idioma_login = st.selectbox(
            _t("lang_selector_label"),
            options=list(i18n.IDIOMAS_DISPONIVEIS.keys()),
            format_func=lambda code: i18n.IDIOMAS_DISPONIVEIS[code],
            index=list(i18n.IDIOMAS_DISPONIVEIS.keys()).index(cur_lang),
            key="login_lang_selector"
        )
        if idioma_login != cur_lang:
            st.session_state["idioma"] = idioma_login
            database.salvar_configuracao("idioma_padrao", idioma_login)
            st.rerun()

    # Card Centralizado de Login
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/fluency/96/project-management.png", width=64)
        st.markdown(f"## {_t('login_screen_title')}")
        st.write(_t("login_screen_subtitle"))

        with st.form("form_login"):
            login_user = st.text_input(_t("lbl_usuario"))
            login_pass = st.text_input(_t("lbl_senha"), type="password")
            btn_entrar = st.form_submit_button(_t("btn_acessar"), type="primary", use_container_width=True)

            if btn_entrar:
                usuario = database.autenticar_usuario(login_user, login_pass)
                if usuario:
                    if usuario.get("inativo"):
                        st.error(_t("err_usuario_inativo"))
                    else:
                        st.session_state["autenticado"] = True
                        st.session_state["usuario_atual"] = usuario
                        st.rerun()
                else:
                    st.error(_t("err_login_invalido"))

    st.stop()

# ==============================================================================
# PAINEL AUTENTICADO
# ==============================================================================
# Barra Lateral
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/project-management.png", width=64)
    st.title(_t("sidebar_title"))
    
    # Perfil do Usuário Logado e Ações
    usuario_atual = st.session_state.get("usuario_atual", {})
    st.markdown(f"👤 {_t('logged_as')} **{usuario_atual.get('nome', '')}** (`@{usuario_atual.get('username', '')}`)")
    
    if st.button(_t("btn_logout"), use_container_width=True):
        st.session_state["autenticado"] = False
        st.session_state["usuario_atual"] = None
        st.rerun()

    st.markdown("---")

    # Seletor de Idioma
    idioma_selecionado = st.selectbox(
        _t("lang_selector_label"),
        options=list(i18n.IDIOMAS_DISPONIVEIS.keys()),
        format_func=lambda code: i18n.IDIOMAS_DISPONIVEIS[code],
        index=list(i18n.IDIOMAS_DISPONIVEIS.keys()).index(cur_lang),
        key="sidebar_lang_selector"
    )
    if idioma_selecionado != cur_lang:
        st.session_state["idioma"] = idioma_selecionado
        database.salvar_configuracao("idioma_padrao", idioma_selecionado)
        st.rerun()

    # Gestão de Usuários (próximo ao de alterar idiomas)
    col_u_add, col_u_list = st.columns(2)
    with col_u_add:
        with st.popover(_t("btn_adicionar_usuario"), use_container_width=True):
            st.markdown(f"#### {_t('btn_adicionar_usuario')}")
            p_cad_user = st.text_input(_t("lbl_usuario"), key="sb_cad_user")
            p_cad_nome = st.text_input(_t("lbl_nome_completo"), key="sb_cad_nome")
            p_cad_email = st.text_input(_t("lbl_email"), key="sb_cad_email")
            p_cad_pass1 = st.text_input(_t("lbl_senha"), type="password", key="sb_cad_pass1")
            p_cad_pass2 = st.text_input(_t("lbl_confirma_senha"), type="password", key="sb_cad_pass2")
            p_cad_admin = st.checkbox(_t("is_admin_label"), key="sb_cad_admin")
            
            if st.button(_t("btn_registrar_usuario"), key="sb_btn_reg", type="primary", use_container_width=True):
                if not p_cad_user or not p_cad_nome or not p_cad_pass1:
                    st.error(_t("err_required"))
                elif p_cad_pass1 != p_cad_pass2:
                    st.error(_t("err_senhas_diferentes"))
                else:
                    ok, msg = database.criar_usuario(
                        p_cad_user, 
                        p_cad_nome, 
                        p_cad_email, 
                        p_cad_pass1, 
                        is_admin=1 if p_cad_admin else 0
                    )
                    if ok:
                        st.success(_t("success_usuario_criado"))
                        st.rerun()
                    else:
                        st.error(msg)

    with col_u_list:
        with st.popover(_t("btn_gerenciar_usuarios"), use_container_width=True):
            st.markdown(f"#### {_t('user_mgmt_title')}")
            st.caption(_t("user_mgmt_subtitle"))
            
            todos_usuarios = database.listar_usuarios()
            for u in todos_usuarios:
                eh_proprio = (u["id"] == usuario_atual.get("id"))
                is_ativo = (u.get("ativo", 1) == 1)
                
                status_cor = "#166534" if is_ativo else "#991B1B"
                status_bg = "#DCFCE7" if is_ativo else "#FEE2E2"
                status_label = _t("user_status_active") if is_ativo else _t("user_status_inactive")
                
                with st.container():
                    st.markdown(f"""
                    <div style="padding: 8px; border-radius: 6px; background-color: #f8fafc; border: 1px solid #e2e8f0; margin-bottom: 6px;">
                        <strong>{u['nome']}</strong> <span style="color: #64748b;">(@{u['username']})</span>
                        <br>
                        <small>{u.get('email', '') or 'Sem e-mail cadastrado'}</small>
                        <div style="margin-top: 4px;">
                            <span style="background-color: {status_bg}; color: {status_cor}; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                                {status_label}
                            </span>
                            {' <span style="background-color: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">⭐ Admin</span>' if u.get('is_admin') else ''}
                            {' <span style="color: #64748b; font-size: 11px;">(Você)</span>' if eh_proprio else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        if eh_proprio:
                            st.button(_t("btn_deactivate") if is_ativo else _t("btn_activate"), key=f"btn_stat_{u['id']}", disabled=True, help=_t("err_cannot_deactivate_self"), use_container_width=True)
                        else:
                            if is_ativo:
                                if st.button(_t("btn_deactivate"), key=f"btn_inativar_{u['id']}", use_container_width=True):
                                    database.alternar_status_usuario(u["id"], 0)
                                    st.success(_t("success_user_status"))
                                    st.rerun()
                            else:
                                if st.button(_t("btn_activate"), key=f"btn_ativar_{u['id']}", use_container_width=True):
                                    database.alternar_status_usuario(u["id"], 1)
                                    st.success(_t("success_user_status"))
                                    st.rerun()
                    with c_act2:
                        if eh_proprio:
                            st.button(_t("btn_delete_user"), key=f"btn_del_{u['id']}", disabled=True, help=_t("err_cannot_delete_self"), use_container_width=True)
                        else:
                            btn_del_key = f"confirm_del_u_{u['id']}"
                            if st.session_state.get(btn_del_key):
                                st.warning(_t("delete_user_confirm", user=u['username']))
                                c_yes, c_no = st.columns(2)
                                with c_yes:
                                    if st.button("✔️ Sim", key=f"yes_del_{u['id']}", type="primary", use_container_width=True):
                                        database.excluir_usuario(u["id"])
                                        st.session_state[btn_del_key] = False
                                        st.success(_t("success_user_deleted"))
                                        st.rerun()
                                with c_no:
                                    if st.button("✖️ Não", key=f"no_del_{u['id']}", use_container_width=True):
                                        st.session_state[btn_del_key] = False
                                        st.rerun()
                            else:
                                if st.button(_t("btn_delete_user"), key=f"trigger_del_{u['id']}", use_container_width=True):
                                    st.session_state[btn_del_key] = True
                                    st.rerun()
                    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    hoje = date.today()
    st.caption(f"{_t('system_date')} **{hoje.strftime('%d/%m/%Y')}**")
    
    st.markdown("---")
    
    # Ações rápidas
    if st.button(_t("refresh_btn"), use_container_width=True):
        st.rerun()
        
    st.markdown("---")
    st.markdown(f"""
    **{_t('legend_status_title')}**
    - {_t('status_no_prazo')}
    - {_t('status_chegando_fim')}
    - {_t('status_atrasado')}
    - {_t('status_concluido')}
    
    **{_t('legend_prio_title')}**
    - {_t('prio_critica_label')} | {_t('prio_alta_label')}
    - {_t('prio_media_label')} | {_t('prio_baixa_label')}
    """)
    
    st.markdown("---")
    # Carregar dados de exemplo se o banco estiver vazio
    if st.button(_t("seed_btn"), help=_t("seed_help"), use_container_width=True):
        import seed_data
        seed_data.popular_dados_exemplo(forcar=True)
        st.success(_t("seed_success"))
        st.rerun()

# Recuperar projetos do banco
projetos_raw = database.listar_projetos()

# Processar métricas dinâmicas para cada projeto
projetos = []
for p in projetos_raw:
    m = logic.calcular_metricas_projeto(p, hoje=hoje)
    item = {**p, **m}
    projetos.append(item)

# Cabeçalho Principal
st.markdown(f"## {_t('portal_title')}")
st.write(_t("portal_subtitle"))

# Abas Principais
tab_dash, tab_consulta, tab_avisos, tab_novo, tab_config = st.tabs([
    _t("tab_dash"),
    _t("tab_consulta"),
    _t("tab_avisos"),
    _t("tab_novo"),
    _t("tab_config")
])

# Mapeamentos de tradução de prioridades e status
map_prio = {
    "Crítica": _t("prio_critica"),
    "Alta": _t("prio_alta"),
    "Média": _t("prio_media"),
    "Baixa": _t("prio_baixa")
}

map_status_prazo = {
    "No Prazo": _t("status_prazo_no_prazo"),
    "Chegando ao Fim": _t("status_prazo_chegando"),
    "Atrasado": _t("status_prazo_atrasado"),
    "Concluído": _t("status_prazo_concluido")
}

# ==============================================================================
# ABA 1: PAINEL GERAL (DASHBOARD)
# ==============================================================================
with tab_dash:
    total_projetos = len(projetos)
    no_prazo = sum(1 for p in projetos if p["status"] == "No Prazo")
    chegando_fim = sum(1 for p in projetos if p["status"] == "Chegando ao Fim")
    atrasados = sum(1 for p in projetos if p["status"] == "Atrasado")
    concluidos = sum(1 for p in projetos if p["status"] == "Concluído")
    
    # Cards de KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{_t('kpi_total')}</div>
            <div class="metric-value" style="color: #3b82f6;">{total_projetos}</div>
            <span style="font-size: 12px; color: #64748b;">{_t('kpi_sub_cadastrados')}</span>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{_t('kpi_no_prazo')}</div>
            <div class="metric-value" style="color: #16a34a;">{no_prazo}</div>
            <span style="font-size: 12px; color: #16a34a;">{_t('kpi_sub_em_dia')}</span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #f59e0b; background-color: #fffbeb;">
            <div class="metric-title" style="color: #b45309;">{_t('kpi_chegando_fim')}</div>
            <div class="metric-value" style="color: #d97706;">{chegando_fim}</div>
            <span style="font-size: 12px; color: #b45309;">{_t('kpi_sub_atencao')}</span>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #ef4444; background-color: #fef2f2;">
            <div class="metric-title" style="color: #b91c1c;">{_t('kpi_atrasados')}</div>
            <div class="metric-value" style="color: #dc2626;">{atrasados}</div>
            <span style="font-size: 12px; color: #b91c1c;">{_t('kpi_sub_expirado')}</span>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{_t('kpi_concluidos')}</div>
            <div class="metric-value" style="color: #2563eb;">{concluidos}</div>
            <span style="font-size: 12px; color: #2563eb;">{_t('kpi_sub_finalizados')}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Alerta em Destaque
    projetos_atencao = [p for p in projetos if p["precisa_aviso"]]
    if projetos_atencao:
        st.warning(_t("alert_attention", count=len(projetos_atencao)))
    else:
        st.success(_t("alert_all_ok"))

    # Gráficos
    if total_projetos > 0:
        g1, g2 = st.columns([1, 1])
        with g1:
            st.subheader(_t("chart_status_title"))
            lbl_no_prazo = _t("status_prazo_no_prazo")
            lbl_chegando = _t("status_prazo_chegando")
            lbl_atrasado = _t("status_prazo_atrasado")
            lbl_concluido = _t("status_prazo_concluido")
            
            status_df = pd.DataFrame([
                {"Status": lbl_no_prazo, "Quantidade": no_prazo},
                {"Status": lbl_chegando, "Quantidade": chegando_fim},
                {"Status": lbl_atrasado, "Quantidade": atrasados},
                {"Status": lbl_concluido, "Quantidade": concluidos}
            ])
            status_df = status_df[status_df["Quantidade"] > 0]
            
            chart_status = alt.Chart(status_df).mark_bar(cornerRadius=6).encode(
                x=alt.X("Quantidade:Q", title=_t("chart_qty_axis")),
                y=alt.Y("Status:N", sort="-x", title=None),
                color=alt.Color("Status:N", scale=alt.Scale(
                    domain=[lbl_no_prazo, lbl_chegando, lbl_atrasado, lbl_concluido],
                    range=["#16a34a", "#d97706", "#dc2626", "#2563eb"]
                ), legend=None),
                tooltip=["Status", "Quantidade"]
            ).properties(height=220)
            st.altair_chart(chart_status, use_container_width=True)

        with g2:
            st.subheader(_t("chart_prio_title"))
            prio_counts = {
                _t("prio_critica"): sum(1 for p in projetos if p.get("prioridade") == "Crítica"),
                _t("prio_alta"): sum(1 for p in projetos if p.get("prioridade") == "Alta"),
                _t("prio_media"): sum(1 for p in projetos if p.get("prioridade", "Média") in ["Média", None, ""]),
                _t("prio_baixa"): sum(1 for p in projetos if p.get("prioridade") == "Baixa"),
            }
            prio_df = pd.DataFrame([{"Prioridade": k, "Total": v} for k, v in prio_counts.items() if v > 0])
            
            chart_prio = alt.Chart(prio_df).mark_bar(cornerRadius=6).encode(
                x=alt.X("Total:Q", title=_t("chart_total_axis")),
                y=alt.Y("Prioridade:N", sort=[_t("prio_critica"), _t("prio_alta"), _t("prio_media"), _t("prio_baixa")], title=None),
                color=alt.Color("Prioridade:N", scale=alt.Scale(
                    domain=[_t("prio_critica"), _t("prio_alta"), _t("prio_media"), _t("prio_baixa")],
                    range=["#dc2626", "#ea580c", "#d97706", "#64748b"]
                ), legend=None),
                tooltip=["Prioridade", "Total"]
            ).properties(height=220)
            st.altair_chart(chart_prio, use_container_width=True)

        g3, g4 = st.columns([1, 1])
        with g3:
            st.subheader(_t("chart_manual_title"))
            manual_counts = {}
            for p in projetos:
                s_man = p.get("status_manual", "Em Execução") or "Em Execução"
                manual_counts[s_man] = manual_counts.get(s_man, 0) + 1
            manual_df = pd.DataFrame([{"Status Operacional": k, "Total": v} for k, v in manual_counts.items()])
            chart_manual = alt.Chart(manual_df).mark_bar(cornerRadius=6, color="#0284c7").encode(
                x=alt.X("Total:Q", title=_t("chart_total_axis")),
                y=alt.Y("Status Operacional:N", sort="-x", title=None),
                tooltip=["Status Operacional", "Total"]
            ).properties(height=220)
            st.altair_chart(chart_manual, use_container_width=True)

        with g4:
            st.subheader(_t("chart_resp_title"))
            resp_counts = {}
            for p in projetos:
                resp_counts[p["responsavel"]] = resp_counts.get(p["responsavel"], 0) + 1
            resp_df = pd.DataFrame([{"Responsável": k, "Total": v} for k, v in resp_counts.items()])
            
            chart_resp = alt.Chart(resp_df).mark_bar(cornerRadius=6, color="#4f46e5").encode(
                x=alt.X("Total:Q", title=_t("chart_qty_axis")),
                y=alt.Y("Responsável:N", sort="-x", title=None),
                tooltip=["Responsável", "Total"]
            ).properties(height=220)
            st.altair_chart(chart_resp, use_container_width=True)

# ==============================================================================
# ABA 2: CONSULTA & ACOMPANHAMENTO
# ==============================================================================
with tab_consulta:
    st.subheader(_t("consulta_subtitle"))
    
    # Filtros
    f1, f2, f3, f4, f5 = st.columns([2, 1, 1, 1, 1])
    with f1:
        termo_busca = st.text_input(_t("search_label"), placeholder=_t("search_placeholder"))
    with f2:
        status_opcoes_raw = ["Todos", "No Prazo", "Chegando ao Fim", "Atrasado", "Concluído"]
        status_labels = [_t("filter_all"), _t("status_prazo_no_prazo"), _t("status_prazo_chegando"), _t("status_prazo_atrasado"), _t("status_prazo_concluido")]
        status_idx = st.selectbox(
            _t("filter_status_prazo"),
            range(len(status_opcoes_raw)),
            format_func=lambda i: status_labels[i]
        )
        status_filtro = status_opcoes_raw[status_idx]
    with f3:
        prio_opcoes_raw = ["Todas", "Crítica", "Alta", "Média", "Baixa"]
        prio_labels = [_t("filter_all_fem"), _t("prio_critica"), _t("prio_alta"), _t("prio_media"), _t("prio_baixa")]
        prio_idx = st.selectbox(
            _t("filter_priority"),
            range(len(prio_opcoes_raw)),
            format_func=lambda i: prio_labels[i]
        )
        prio_filtro = prio_opcoes_raw[prio_idx]
    with f4:
        man_opcoes = ["Todos", "Em Planejamento", "Em Execução", "Em Homologação", "Em Pausa", "Concluído", "Cancelado"]
        man_filtro = st.selectbox(_t("filter_manual"), man_opcoes)
    with f5:
        responsaveis_unicos = ["Todos"] + sorted(list({p["responsavel"] for p in projetos}))
        resp_filtro = st.selectbox(_t("filter_resp"), responsaveis_unicos)

    # Aplicação dos Filtros
    projetos_filtrados = projetos
    if termo_busca:
        termo = termo_busca.lower()
        projetos_filtrados = [
            p for p in projetos_filtrados
            if termo in p["nome"].lower()
            or termo in p["responsavel"].lower()
            or termo in p["email_responsavel"].lower()
            or termo in p.get("observacoes", "").lower()
            or termo in p.get("prioridade", "").lower()
            or termo in p.get("status_manual", "").lower()
        ]
    if status_filtro != "Todos":
        projetos_filtrados = [p for p in projetos_filtrados if p["status"] == status_filtro]
    if prio_filtro != "Todas":
        projetos_filtrados = [p for p in projetos_filtrados if p.get("prioridade") == prio_filtro]
    if man_filtro != "Todos":
        projetos_filtrados = [p for p in projetos_filtrados if p.get("status_manual") == man_filtro]
    if resp_filtro != "Todos":
        projetos_filtrados = [p for p in projetos_filtrados if p["responsavel"] == resp_filtro]

    st.write(_t("showing_projects", current=len(projetos_filtrados), total=len(projetos)))

    if not projetos_filtrados:
        st.info(_t("no_projects_found"))
    else:
        # Exibição dos Projetos em Cards Interativos
        for p in projetos_filtrados:
            with st.container():
                st.markdown("---")
                col_info, col_datas, col_acoes = st.columns([3, 2, 2])
                
                with col_info:
                    st.markdown(f"### {p['status_icone']} {p['nome']}")
                    
                    # Badges de Prioridade e Status Manual
                    prio_traduzida = map_prio.get(p.get("prioridade", "Média"), p.get("prioridade", "Média"))
                    st.markdown(f"""
                    <span class="badge" style="background-color: {p['prioridade_cor']}20; color: {p['prioridade_cor']}; border: 1px solid {p['prioridade_cor']}80;">
                        {p['prioridade_icone']} {_t('field_priority')}: {prio_traduzida}
                    </span>
                    <span class="badge" style="background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;">
                        📌 {_t('field_manual_status')}: {p['status_manual']}
                    </span>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**{_t('card_resp')}** {p['responsavel']}  \n✉️ [{p['email_responsavel']}](mailto:{p['email_responsavel']})")
                    if p.get("observacoes"):
                        st.info(f"📝 **{_t('card_obs')}** {p['observacoes']}")
                
                with col_datas:
                    st.markdown(f"**{_t('card_start')}** `{logic.parse_data(p['data_inicio']).strftime('%d/%m/%Y')}`")
                    st.markdown(f"**{_t('card_alert')}** `{logic.parse_data(p['data_aviso']).strftime('%d/%m/%Y')}`")
                    st.markdown(f"**{_t('card_end')}** `{logic.parse_data(p['data_termino']).strftime('%d/%m/%Y')}`")
                    
                    if p["status"] == "Concluído":
                        st.success(_t("card_status_concluido"))
                    elif p["status"] == "Atrasado":
                        st.error(_t("card_status_atrasado", days=abs(p['dias_restantes_termino'])))
                    elif p["status"] == "Chegando ao Fim":
                        st.warning(_t("card_status_chegando", days=p['dias_restantes_termino']))
                    else:
                        st.info(_t("card_status_no_prazo", days=p['dias_restantes_termino']))
                        
                    st.progress(p["progresso"] / 100, text=_t("card_elapsed", pct=p['progresso']))

                with col_acoes:
                    st.markdown("<br>", unsafe_allow_html=True)
                    # Botão Concluir / Reabrir
                    if p["concluido"]:
                        if st.button(_t("btn_reopen"), key=f"reabrir_{p['id']}", use_container_width=True):
                            database.alternar_conclusao(p["id"], 0)
                            st.rerun()
                    else:
                        if st.button(_t("btn_complete"), key=f"concluir_{p['id']}", use_container_width=True):
                            database.alternar_conclusao(p["id"], 1)
                            st.rerun()

                    # Popover para Edição do Projeto
                    with st.popover(_t("btn_edit"), use_container_width=True):
                        st.write(f"**{_t('edit_title', nome=p['nome'])}**")
                        edit_nome = st.text_input(_t("field_proj_name"), value=p["nome"], key=f"enome_{p['id']}")
                        
                        c_ep1, c_ep2 = st.columns(2)
                        with c_ep1:
                            prio_raw_list = ["Crítica", "Alta", "Média", "Baixa"]
                            edit_prio_idx = prio_raw_list.index(p.get("prioridade", "Média")) if p.get("prioridade") in prio_raw_list else 2
                            edit_prio_idx_sel = st.selectbox(
                                _t("field_priority"),
                                range(len(prio_raw_list)),
                                index=edit_prio_idx,
                                format_func=lambda i: map_prio[prio_raw_list[i]],
                                key=f"eprio_{p['id']}"
                            )
                            edit_prio = prio_raw_list[edit_prio_idx_sel]
                        with c_ep2:
                            man_opcoes_edit = ["Em Planejamento", "Em Execução", "Em Homologação", "Em Pausa", "Concluído", "Cancelado"]
                            edit_man_idx = man_opcoes_edit.index(p.get("status_manual", "Em Execução")) if p.get("status_manual") in man_opcoes_edit else 1
                            edit_man = st.selectbox(_t("field_manual_status"), man_opcoes_edit, index=edit_man_idx, key=f"eman_{p['id']}")
                            
                        c_d1, c_d2, c_d3 = st.columns(3)
                        with c_d1:
                            edit_ini = st.date_input(_t("field_start_date"), value=logic.parse_data(p["data_inicio"]), key=f"eini_{p['id']}")
                        with c_d2:
                            edit_aviso = st.date_input(_t("field_alert_date"), value=logic.parse_data(p["data_aviso"]), key=f"eaviso_{p['id']}")
                        with c_d3:
                            edit_ter = st.date_input(_t("field_end_date"), value=logic.parse_data(p["data_termino"]), key=f"eter_{p['id']}")
                        edit_resp = st.text_input(_t("field_resp_name"), value=p["responsavel"], key=f"eresp_{p['id']}")
                        edit_email = st.text_input(_t("field_resp_email"), value=p["email_responsavel"], key=f"eemail_{p['id']}")
                        edit_obs = st.text_area(_t("field_obs"), value=p.get("observacoes", ""), key=f"eobs_{p['id']}")
                        
                        if st.button(_t("btn_save_changes"), key=f"save_{p['id']}"):
                            if not edit_nome or not edit_resp or not edit_email:
                                st.error(_t("err_required"))
                            elif not (edit_ini <= edit_aviso <= edit_ter):
                                st.error(_t("err_dates"))
                            else:
                                database.atualizar_projeto(
                                    projeto_id=p["id"],
                                    nome=edit_nome,
                                    data_inicio=edit_ini.strftime("%Y-%m-%d"),
                                    data_termino=edit_ter.strftime("%Y-%m-%d"),
                                    data_aviso=edit_aviso.strftime("%Y-%m-%d"),
                                    responsavel=edit_resp,
                                    email_responsavel=edit_email,
                                    concluido=p["concluido"],
                                    observacoes=edit_obs,
                                    prioridade=edit_prio,
                                    status_manual=edit_man
                                )
                                st.success(_t("save_success"))
                                st.rerun()

                    # Botão Excluir
                    with st.popover(_t("btn_delete"), use_container_width=True):
                        st.write(_t("delete_confirm"))
                        if st.button(_t("btn_confirm_delete"), key=f"del_{p['id']}", type="primary"):
                            database.excluir_projeto(p["id"])
                            st.success(_t("deleted_success"))
                            st.rerun()

    # Emissão e Exportação de Relatórios com Filtros (PDF, Excel, CSV)
    st.markdown("---")
    st.markdown(f"### {_t('export_section_title')}")
    st.caption(_t("export_hint"))

    if projetos_filtrados:
        filtros_ativos = {
            _t("filter_status_prazo").replace(":", ""): status_filtro if status_filtro != "Todos" else None,
            _t("filter_priority").replace(":", ""): prio_filtro if prio_filtro != "Todas" else None,
            _t("filter_manual").replace(":", ""): man_filtro if man_filtro != "Todos" else None,
            _t("filter_resp").replace(":", ""): resp_filtro if resp_filtro != "Todos" else None,
            _t("search_label").replace("🔍 ", "").replace(":", ""): termo_busca if termo_busca else None
        }
        filtros_ativos = {k: v for k, v in filtros_ativos.items() if v}

        pdf_bytes = report_generator.gerar_relatorio_pdf(
            projetos=projetos_filtrados,
            lang=cur_lang,
            filtros=filtros_ativos
        )
        excel_bytes = report_generator.gerar_relatorio_excel(
            projetos=projetos_filtrados,
            lang=cur_lang,
            filtros=filtros_ativos
        )

        df_export = pd.DataFrame([
            {
                "ID": p["id"],
                "Nome": p["nome"],
                "Prioridade": p.get("prioridade", "Média"),
                "Status Cronograma": p["status"],
                "Status Operacional": p.get("status_manual", "Em Execução"),
                "Data de Inicio": p["data_inicio"],
                "Data de Aviso": p["data_aviso"],
                "Data de Termino": p["data_termino"],
                "Dias Restantes": p["dias_restantes_termino"],
                "Responsavel": p["responsavel"],
                "Email": p["email_responsavel"],
                "Concluido": "Sim" if p["concluido"] else "Nao",
                "Observacoes": p.get("observacoes", "")
            }
            for p in projetos_filtrados
        ])
        csv_data = df_export.to_csv(index=False, sep=";", encoding="utf-8-sig")

        hoje_str = date.today().strftime('%Y%m%d')
        col_pdf, col_excel, col_csv = st.columns(3)
        with col_pdf:
            st.download_button(
                label=_t("export_pdf_btn"),
                data=pdf_bytes,
                file_name=f"relatorio_projetos_{hoje_str}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        with col_excel:
            st.download_button(
                label=_t("export_excel_btn"),
                data=excel_bytes,
                file_name=f"relatorio_projetos_{hoje_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_csv:
            st.download_button(
                label=_t("export_csv_btn"),
                data=csv_data,
                file_name=f"projetos_{hoje_str}.csv",
                mime="text/csv",
                use_container_width=True
            )

# ==============================================================================
# ABA 3: CENTRAL DE AVISOS & DISPARO SMTP
# ==============================================================================
with tab_avisos:
    st.subheader(_t("avisos_title"))
    st.write(_t("avisos_subtitle"))
    
    config_smtp = email_service.obter_config_smtp()
    if not config_smtp.get("host") or not config_smtp.get("remetente"):
        st.warning(_t("smtp_not_configured"))
    
    projetos_alerta = [p for p in projetos if p["precisa_aviso"]]
    
    if not projetos_alerta:
        st.success(_t("avisos_none"))
    else:
        st.info(_t("avisos_found", count=len(projetos_alerta)))
        
        # Disparo em Lote
        col_lote1, col_lote2 = st.columns([3, 1])
        with col_lote1:
            st.write(_t("avisos_batch_desc"))
        with col_lote2:
            if st.button(_t("btn_send_all"), type="primary", use_container_width=True):
                sucessos = 0
                erros = 0
                with st.spinner("Enviando e-mails via SMTP..."):
                    for pa in projetos_alerta:
                        ok, msg = email_service.enviar_email_projeto(pa, config_smtp, lang=cur_lang)
                        if ok:
                            sucessos += 1
                        else:
                            erros += 1
                if sucessos > 0:
                    st.success(_t("batch_success", count=sucessos))
                if erros > 0:
                    st.error(_t("batch_fail", count=erros))
                st.rerun()

        st.markdown("---")
        
        # Lista detalhada de projetos com alerta
        for pa in projetos_alerta:
            with st.container():
                col_alerta_info, col_alerta_status, col_alerta_btn = st.columns([3, 2, 2])
                
                with col_alerta_info:
                    st.markdown(f"**{pa['status_icone']} {pa['nome']}**")
                    prio_t = map_prio.get(pa.get("prioridade", "Média"), pa.get("prioridade", "Média"))
                    st.markdown(f"""
                    <span class="badge" style="background-color: {pa['prioridade_cor']}20; color: {pa['prioridade_cor']}; border: 1px solid {pa['prioridade_cor']}80;">
                        {pa['prioridade_icone']} {prio_t}
                    </span>
                    <span class="badge" style="background-color: #f1f5f9; color: #334155; border: 1px solid #cbd5e1;">
                        📌 {pa['status_manual']}
                    </span>
                    """, unsafe_allow_html=True)
                    st.markdown(f"👤 **{_t('card_resp')}** {pa['responsavel']} ({pa['email_responsavel']})")
                    if pa.get("ultimo_aviso_enviado"):
                        st.caption(_t("last_alert_sent", dt=pa['ultimo_aviso_enviado']))
                    else:
                        st.caption(_t("no_alert_sent"))
                    if pa.get("observacoes"):
                        st.caption(f"📝 *{pa['observacoes']}*")
                
                with col_alerta_status:
                    if pa["status"] == "Atrasado":
                        st.error(_t("card_status_atrasado", days=abs(pa['dias_restantes_termino'])))
                    else:
                        st.warning(_t("card_status_chegando", days=pa['dias_restantes_termino']))
                    st.write(f"{_t('card_alert')} `{logic.parse_data(pa['data_aviso']).strftime('%d/%m/%Y')}`")
                    
                with col_alerta_btn:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(_t("btn_send_smtp"), key=f"send_smtp_{pa['id']}", use_container_width=True):
                        with st.spinner("Enviando..."):
                            sucesso, mensagem = email_service.enviar_email_projeto(pa, config_smtp, lang=cur_lang)
                        if sucesso:
                            st.success(mensagem)
                            st.rerun()
                        else:
                            st.error(mensagem)
                            
                # Pré-visualização do e-mail
                with st.expander(_t("preview_email")):
                    assunto, texto, html = logic.gerar_conteudo_email_alerta(pa, pa, lang=cur_lang)
                    st.markdown(f"**{_t('preview_subject')}** `{assunto}`")
                    st.components.v1.html(html, height=350, scrolling=True)
                st.markdown("---")

# ==============================================================================
# ABA 4: NOVO PROJETO
# ==============================================================================
with tab_novo:
    st.subheader(_t("new_proj_title"))
    st.write(_t("new_proj_subtitle"))
    
    with st.form("form_novo_projeto", clear_on_submit=True):
        nome_novo = st.text_input(f"{_t('field_proj_name')} *", placeholder="Ex: Modernização da Infraestrutura de TI")
        
        col_prio_1, col_prio_2 = st.columns(2)
        with col_prio_1:
            prio_raw_opcoes = ["Crítica", "Alta", "Média", "Baixa"]
            prio_idx_novo = st.selectbox(
                f"{_t('field_priority')} *",
                range(len(prio_raw_opcoes)),
                index=2,
                format_func=lambda i: map_prio[prio_raw_opcoes[i]]
            )
            prio_novo = prio_raw_opcoes[prio_idx_novo]
        with col_prio_2:
            man_novo = st.selectbox(
                f"{_t('field_manual_status')} *",
                ["Em Planejamento", "Em Execução", "Em Homologação", "Em Pausa"],
                index=1
            )
            
        col_datas_1, col_datas_2, col_datas_3 = st.columns(3)
        with col_datas_1:
            data_ini_default = date.today()
            data_ini_novo = st.date_input(f"{_t('field_start_date')} *", value=data_ini_default)
        with col_datas_2:
            data_ter_default = date.today() + timedelta(days=30)
            data_ter_novo = st.date_input(f"{_t('field_end_date')} *", value=data_ter_default)
        with col_datas_3:
            data_aviso_default = data_ter_default - timedelta(days=7)
            data_aviso_novo = st.date_input(
                f"{_t('field_alert_date')} *",
                value=data_aviso_default,
                help=_t("field_alert_date_help")
            )
            
        col_resp_1, col_resp_2 = st.columns(2)
        with col_resp_1:
            resp_novo = st.text_input(f"{_t('field_resp_name')} *", placeholder="Ex: João da Silva")
        with col_resp_2:
            email_novo = st.text_input(f"{_t('field_resp_email')} *", placeholder="Ex: joao.silva@empresa.com.br")
            
        obs_novo = st.text_area(f"{_t('field_obs')} (Opcional)", placeholder=_t("field_obs_help"))
        
        submitted = st.form_submit_button(_t("btn_create_project"), type="primary", use_container_width=True)
        
        if submitted:
            if not nome_novo.strip():
                st.error(_t("err_required"))
            elif not resp_novo.strip():
                st.error(_t("err_required"))
            elif not email_novo.strip() or "@" not in email_novo:
                st.error(_t("err_invalid_email"))
            elif not (data_ini_novo <= data_aviso_novo <= data_ter_novo):
                st.error(_t("err_dates"))
            else:
                novo_id = database.criar_projeto(
                    nome=nome_novo,
                    data_inicio=data_ini_novo.strftime("%Y-%m-%d"),
                    data_termino=data_ter_novo.strftime("%Y-%m-%d"),
                    data_aviso=data_aviso_novo.strftime("%Y-%m-%d"),
                    responsavel=resp_novo,
                    email_responsavel=email_novo,
                    observacoes=obs_novo,
                    prioridade=prio_novo,
                    status_manual=man_novo
                )
                st.success(_t("create_success", nome=nome_novo, id=novo_id))
                st.rerun()

# ==============================================================================
# ABA 5: CONFIGURAÇÕES SMTP
# ==============================================================================
with tab_config:
    st.subheader(_t("smtp_title"))
    st.write(_t("smtp_subtitle"))
    
    cfg = database.obter_configuracoes()
    
    # Presets rápidos
    st.markdown(f"**{_t('smtp_presets_title')}**")
    cp1, cp2, cp3 = st.columns(3)
    preset_escolhido = None
    with cp1:
        if st.button(_t("preset_gmail"), use_container_width=True):
            preset_escolhido = {"host": "smtp.gmail.com", "port": "587", "tls": "1", "ssl": "0"}
    with cp2:
        if st.button(_t("preset_office"), use_container_width=True):
            preset_escolhido = {"host": "smtp.office365.com", "port": "587", "tls": "1", "ssl": "0"}
    with cp3:
        if st.button(_t("preset_local"), use_container_width=True):
            preset_escolhido = {"host": "localhost", "port": "1025", "tls": "0", "ssl": "0"}
            
    if preset_escolhido:
        database.salvar_configuracao("smtp_host", preset_escolhido["host"])
        database.salvar_configuracao("smtp_port", preset_escolhido["port"])
        database.salvar_configuracao("smtp_usar_tls", preset_escolhido["tls"])
        database.salvar_configuracao("smtp_usar_ssl", preset_escolhido["ssl"])
        st.success(_t("preset_applied"))
        st.rerun()

    with st.form("form_smtp"):
        c_host, c_port = st.columns([3, 1])
        with c_host:
            host_val = st.text_input(_t("smtp_host_label"), value=cfg.get("smtp_host", "smtp.office365.com"), placeholder="smtp.exemplo.com.br")
        with c_port:
            port_val = st.text_input(_t("smtp_port_label"), value=cfg.get("smtp_port", "587"), placeholder="587")
            
        c_sec1, c_sec2 = st.columns(2)
        with c_sec1:
            tls_val = st.checkbox(_t("smtp_tls_label"), value=(cfg.get("smtp_usar_tls", "1") == "1"))
        with c_sec2:
            ssl_val = st.checkbox(_t("smtp_ssl_label"), value=(cfg.get("smtp_usar_ssl", "0") == "1"))
            
        c_user, c_pass = st.columns(2)
        with c_user:
            user_val = st.text_input(_t("smtp_user_label"), value=cfg.get("smtp_usuario", ""), placeholder="seu-email@empresa.com.br")
        with c_pass:
            pass_val = st.text_input(_t("smtp_pass_label"), value=cfg.get("smtp_senha", ""), type="password", help=_t("smtp_pass_help"))
            
        remetente_val = st.text_input(_t("smtp_from_label"), value=cfg.get("smtp_remetente", cfg.get("smtp_usuario", "")), placeholder="notificacoes@empresa.com.br")
        
        salvar_btn = st.form_submit_button(_t("btn_save_smtp"), type="primary", use_container_width=True)
        
        if salvar_btn:
            database.salvar_configuracoes_smtp({
                "smtp_host": host_val.strip(),
                "smtp_port": port_val.strip(),
                "smtp_usar_tls": "1" if tls_val else "0",
                "smtp_usar_ssl": "1" if ssl_val else "0",
                "smtp_usuario": user_val.strip(),
                "smtp_senha": pass_val,
                "smtp_remetente": remetente_val.strip()
            })
            st.success(_t("smtp_saved"))
            st.rerun()

    st.markdown("---")
    st.subheader(_t("smtp_test_section"))
    st.write(_t("smtp_test_desc"))
    
    if st.button(_t("btn_test_smtp")):
        dados_teste = {
            "host": cfg.get("smtp_host", ""),
            "port": int(cfg.get("smtp_port", "587")) if cfg.get("smtp_port") else 587,
            "usuario": cfg.get("smtp_usuario", ""),
            "senha": cfg.get("smtp_senha", ""),
            "usar_tls": cfg.get("smtp_usar_tls", "1") == "1",
            "usar_ssl": cfg.get("smtp_usar_ssl", "0") == "1"
        }
        with st.spinner("Conectando ao servidor SMTP..."):
            sucesso, msg = email_service.testar_conexao_smtp(dados_teste)
        if sucesso:
            st.success(f"✅ {msg}")
        else:
            st.error(f"❌ {msg}")
