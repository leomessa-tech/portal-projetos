from datetime import datetime, date
from typing import Dict, Any, Tuple

def parse_data(d_str: str) -> date:
    if isinstance(d_str, (datetime, date)):
        return d_str if isinstance(d_str, date) else d_str.date()
    return datetime.strptime(str(d_str)[:10], "%Y-%m-%d").date()

def obter_badge_prioridade(prioridade: str) -> Tuple[str, str]:
    p = (prioridade or "Média").capitalize()
    if p == "Crítica":
        return "#dc2626", "🔥"
    elif p == "Alta":
        return "#ea580c", "⚡"
    elif p == "Média":
        return "#d97706", "📌"
    else: # Baixa
        return "#64748b", "☕"

def calcular_metricas_projeto(proj: Dict[str, Any], hoje: date = None) -> Dict[str, Any]:
    if hoje is None:
        hoje = date.today()
        
    inicio = parse_data(proj["data_inicio"])
    termino = parse_data(proj["data_termino"])
    aviso = parse_data(proj["data_aviso"])
    concluido = bool(proj.get("concluido", 0))
    prioridade = proj.get("prioridade", "Média") or "Média"
    status_manual = proj.get("status_manual", "Em Execução") or "Em Execução"
    
    dias_restantes_termino = (termino - hoje).days
    dias_restantes_aviso = (aviso - hoje).days
    duracao_total = max((termino - inicio).days, 1)
    dias_decorridos = max((hoje - inicio).days, 0)
    
    progresso = min(max(int((dias_decorridos / duracao_total) * 100), 0), 100)
    
    # Determinação do Status Automático (Baseado em Prazos)
    if concluido:
        status = "Concluído"
        status_cor = "#2563EB" # Azul
        status_icone = "✅"
    elif hoje > termino:
        status = "Atrasado"
        status_cor = "#DC2626" # Vermelho
        status_icone = "🚨"
    elif hoje >= aviso:
        status = "Chegando ao Fim"
        status_cor = "#D97706" # Amarelo/Laranja
        status_icone = "⚠️"
    else:
        status = "No Prazo"
        status_cor = "#16A34A" # Verde
        status_icone = "🟢"
        
    precisa_aviso = (status in ["Chegando ao Fim", "Atrasado"]) and not concluido
    cor_prio, icone_prio = obter_badge_prioridade(prioridade)
    
    return {
        "status": status,
        "status_cor": status_cor,
        "status_icone": status_icone,
        "prioridade": prioridade,
        "prioridade_cor": cor_prio,
        "prioridade_icone": icone_prio,
        "status_manual": status_manual,
        "dias_restantes_termino": dias_restantes_termino,
        "dias_restantes_aviso": dias_restantes_aviso,
        "progresso": progresso,
        "precisa_aviso": precisa_aviso
    }

def gerar_conteudo_email_alerta(proj: Dict[str, Any], metricas: Dict[str, Any], lang: str = "pt_BR") -> Tuple[str, str, str]:
    """
    Retorna (assunto, corpo_texto, corpo_html) com suporte a pt_BR, en_US, es_ES, fr_FR.
    """
    nome = proj["nome"]
    responsavel = proj["responsavel"]
    data_termino_fmt = parse_data(proj["data_termino"]).strftime("%d/%m/%Y")
    data_aviso_fmt = parse_data(proj["data_aviso"]).strftime("%d/%m/%Y")
    status = metricas["status"]
    dias_restantes = metricas["dias_restantes_termino"]
    
    prioridade = proj.get("prioridade", "Média") or "Média"
    status_manual = proj.get("status_manual", "Em Execução") or "Em Execução"
    observacoes = proj.get("observacoes", "")
    is_atrasado = (status == "Atrasado")
    badge_color = "#dc2626" if is_atrasado else "#d97706"

    # Dicionário de templates de e-mail por idioma
    email_i18n = {
        "pt_BR": {
            "subj_atrasado": f"🚨 [URGENTE - PRAZO EXPIRADO] [{prioridade.upper()}] Projeto: {nome}",
            "subj_aviso": f"⚠️ [ALERTA DE PRAZO] [{prioridade.upper()}] Projeto próximo do término: {nome}",
            "msg_atrasado": f"o prazo final foi ultrapassado há {abs(dias_restantes)} dia(s) (venceu em {data_termino_fmt}).",
            "msg_aviso": f"a data de aviso ({data_aviso_fmt}) foi atingida e restam apenas {dias_restantes} dia(s) para a data de término ({data_termino_fmt}).",
            "saudacao": f"Olá, {responsavel}!",
            "intro": "Este é um aviso automático referente ao acompanhamento de projetos.",
            "lbl_proj": "Projeto:",
            "lbl_prio": "Prioridade:",
            "lbl_cronog": "Status Cronograma:",
            "lbl_operac": "Status Operacional:",
            "lbl_ini": "Data de Início:",
            "lbl_aviso": "Data de Aviso:",
            "lbl_fim": "Data de Término:",
            "lbl_resp": "Responsável:",
            "lbl_obs": "Observações:",
            "call_to_action": "Por gentileza, verifique o cronograma de atividades e garanta que as pendências sejam concluídas dentro do prazo estipulado.",
            "footer": "Enviado automaticamente pelo <strong>Portal de Gestão e Acompanhamento de Projetos</strong>."
        },
        "en_US": {
            "subj_atrasado": f"🚨 [URGENT - DEADLINE EXPIRED] [{prioridade.upper()}] Project: {nome}",
            "subj_aviso": f"⚠️ [DEADLINE ALERT] [{prioridade.upper()}] Project nearing end: {nome}",
            "msg_atrasado": f"the final deadline was exceeded {abs(dias_restantes)} day(s) ago (expired on {data_termino_fmt}).",
            "msg_aviso": f"the alert date ({data_aviso_fmt}) has been reached with only {dias_restantes} day(s) remaining until the deadline ({data_termino_fmt}).",
            "saudacao": f"Hello, {responsavel}!",
            "intro": "This is an automated notification regarding project tracking.",
            "lbl_proj": "Project:",
            "lbl_prio": "Priority:",
            "lbl_cronog": "Timeline Status:",
            "lbl_operac": "Operational Status:",
            "lbl_ini": "Start Date:",
            "lbl_aviso": "Alert Date:",
            "lbl_fim": "End Date:",
            "lbl_resp": "Project Lead:",
            "lbl_obs": "Notes:",
            "call_to_action": "Please review your activities schedule and ensure pending deliverables are concluded on time.",
            "footer": "Sent automatically by the <strong>Project Tracking & Management Portal</strong>."
        },
        "es_ES": {
            "subj_atrasado": f"🚨 [URGENTE - PLAZO VENCIDO] [{prioridade.upper()}] Proyecto: {nome}",
            "subj_aviso": f"⚠️ [ALERTA DE PLAZO] [{prioridade.upper()}] Proyecto próximo a finalizar: {nome}",
            "msg_atrasado": f"el plazo final se ha superado hace {abs(dias_restantes)} día(s) (venció el {data_termino_fmt}).",
            "msg_aviso": f"se ha alcanzado la fecha de aviso ({data_aviso_fmt}) y restan solo {dias_restantes} día(s) para el término ({data_termino_fmt}).",
            "saudacao": f"¡Hola, {responsavel}!",
            "intro": "Este es un aviso automático de seguimiento de proyectos.",
            "lbl_proj": "Proyecto:",
            "lbl_prio": "Prioridad:",
            "lbl_cronog": "Estado Cronograma:",
            "lbl_operac": "Estado Operativo:",
            "lbl_ini": "Fecha de Inicio:",
            "lbl_aviso": "Fecha de Aviso:",
            "lbl_fim": "Fecha de Término:",
            "lbl_resp": "Responsable:",
            "lbl_obs": "Observaciones:",
            "call_to_action": "Por favor, revise el cronograma y asegúrese de que los pendientes se concluyan a tiempo.",
            "footer": "Enviado automáticamente por el <strong>Portal de Gestión y Seguimiento de Proyectos</strong>."
        },
        "fr_FR": {
            "subj_atrasado": f"🚨 [URGENT - ÉCHÉANCE DÉPASSÉE] [{prioridade.upper()}] Projet : {nome}",
            "subj_aviso": f"⚠️ [ALERTE DÉLAI] [{prioridade.upper()}] Projet proche de l'échéance : {nome}",
            "msg_atrasado": f"l'échéance finale est dépassée de {abs(dias_restantes)} jour(s) (expirée le {data_termino_fmt}).",
            "msg_aviso": f"la date d'alerte ({data_aviso_fmt}) a été atteinte et il ne reste que {dias_restantes} jour(s) avant la fin ({data_termino_fmt}).",
            "saudacao": f"Bonjour {responsavel} !",
            "intro": "Ceci est une notification automatique de suivi de projet.",
            "lbl_proj": "Projet :",
            "lbl_prio": "Priorité :",
            "lbl_cronog": "Statut Calendrier :",
            "lbl_operac": "Statut Opérationnel :",
            "lbl_ini": "Date de Début :",
            "lbl_aviso": "Date d'Alerte :",
            "lbl_fim": "Date de Fin :",
            "lbl_resp": "Responsable :",
            "lbl_obs": "Remarques :",
            "call_to_action": "Veuillez vérifier le calendrier de vos activités et veiller à finaliser les livrables dans les délais.",
            "footer": "Envoyé automatiquement par le <strong>Portail de Gestion et Suivi de Projets</strong>."
        }
    }

    txts = email_i18n.get(lang, email_i18n["pt_BR"])
    assunto = txts["subj_atrasado"] if is_atrasado else txts["subj_aviso"]
    msg_situacao = txts["msg_atrasado"] if is_atrasado else txts["msg_aviso"]

    obs_texto = f"\n{txts['lbl_obs']} {observacoes}" if observacoes else ""
    obs_html = f"<tr><td class='label'>{txts['lbl_obs']}</td><td>{observacoes}</td></tr>" if observacoes else ""

    corpo_texto = f"""{txts['saudacao']}

{txts['intro']}

{txts['lbl_proj']} {nome}
{txts['lbl_prio']} {prioridade}
{txts['lbl_cronog']} {status}
{txts['lbl_operac']} {status_manual}
{txts['lbl_ini']} {proj['data_inicio']}
{txts['lbl_fim']} {data_termino_fmt}
{txts['lbl_aviso']} {data_aviso_fmt}{obs_texto}

{msg_situacao}

{txts['call_to_action']}

{txts['footer'].replace('<strong>', '').replace('</strong>', '')}
"""

    corpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
            .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); overflow: hidden; border: 1px solid #e2e8f0; }}
            .header {{ background-color: {badge_color}; color: white; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 20px; }}
            .content {{ padding: 25px; }}
            .highlight-box {{ background-color: #f1f5f9; border-left: 4px solid {badge_color}; padding: 15px; margin: 15px 0; border-radius: 4px; }}
            .info-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            .info-table td {{ padding: 8px 4px; border-bottom: 1px solid #f1f5f9; }}
            .info-table td.label {{ font-weight: 600; color: #475569; width: 40%; }}
            .footer {{ background-color: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <h1>{assunto}</h1>
            </div>
            <div class="content">
                <p>{txts['saudacao']}</p>
                <div class="highlight-box">
                    <p style="margin: 0; font-size: 15px;">
                        {msg_situacao}
                    </p>
                </div>
                <table class="info-table">
                    <tr><td class="label">{txts['lbl_proj']}</td><td><strong>{nome}</strong></td></tr>
                    <tr><td class="label">{txts['lbl_prio']}</td><td><strong>{prioridade}</strong></td></tr>
                    <tr><td class="label">{txts['lbl_cronog']}</td><td><span style="color: {badge_color}; font-weight: bold;">{status}</span></td></tr>
                    <tr><td class="label">{txts['lbl_operac']}</td><td>{status_manual}</td></tr>
                    <tr><td class="label">{txts['lbl_ini']}</td><td>{parse_data(proj['data_inicio']).strftime('%d/%m/%Y')}</td></tr>
                    <tr><td class="label">{txts['lbl_aviso']}</td><td>{data_aviso_fmt}</td></tr>
                    <tr><td class="label">{txts['lbl_fim']}</td><td><strong>{data_termino_fmt}</strong></td></tr>
                    <tr><td class="label">{txts['lbl_resp']}</td><td>{responsavel} ({proj['email_responsavel']})</td></tr>
                    {obs_html}
                </table>
                <p style="margin-top: 20px; font-size: 14px; color: #334155;">
                    {txts['call_to_action']}
                </p>
            </div>
            <div class="footer">
                {txts['footer']}
            </div>
        </div>
    </body>
    </html>
    """
    return assunto, corpo_texto, corpo_html

# ==============================================================================
# MODELO E GERAÇÃO DE PROPOSTA COMERCIAL & TÉCNICA
# ==============================================================================

CONDICOES_COMERCIAIS_PADRAO = """Validade da proposta: 15 dias;
Já incluso impostos;
Prazo de execução conforme cronograma acordado entre as partes;
Pagamento: 10 dias após a execução;
Garantia de 30 dias após a execução;
Qualquer solicitação de alteração nos serviços descritos acima, serão tratados através de uma nova proposta;"""

MESES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

def formatar_data_extenso_pt(d: date = None) -> str:
    if d is None:
        d = date.today()
    elif isinstance(d, str):
        try:
            d = parse_data(d)
        except Exception:
            return d
    return f"{d.day} de {MESES_PT[d.month]} de {d.year}"

def formatar_moeda_br(valor: float) -> str:
    try:
        val_f = float(valor)
        val_str = f"{val_f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {val_str}"
    except Exception:
        return f"R$ {valor}"

def gerar_conteudo_email_proposta(prop: Dict[str, Any], lang: str = "pt_BR") -> Tuple[str, str, str]:
    ref = prop.get("referencia", "26-001")
    data_prop = prop.get("data_proposta", "") or formatar_data_extenso_pt()
    hotel = prop.get("hotel_cliente", "Hotel Cliente")
    chamado = prop.get("chamado_servicenow", "N/A") or "N/A"
    contato_ac = prop.get("contato_ac", "Hotel") or "Hotel"
    descricao = prop.get("descricao_servico", "Serviço Técnico Especializado")
    valor = formatar_moeda_br(prop.get("valor_total", 0.0))
    condicoes = prop.get("condicoes_comerciais", CONDICOES_COMERCIAIS_PADRAO) or CONDICOES_COMERCIAIS_PADRAO
    
    razao = prop.get("razao_social", "") or "__________________________"
    cnpj = prop.get("cnpj", "") or "_________________________________"
    nome_ass = prop.get("nome_assinatura", "") or "_______________________________"
    cargo_ass = prop.get("cargo_assinatura", "") or "_______________________________"
    email_cob = prop.get("email_cobranca", "") or "________________________________________________@accor.com"

    assunto = f"📄 Proposta Comercial e Técnica - Ref: {ref} - {hotel}"

    # Versão em texto puro
    condicoes_txt = "\n".join([f"- {linha.strip()}" for linha in condicoes.splitlines() if linha.strip()])
    corpo_texto = f"""
================================================================================
PROPOSTA COMERCIAL E TÉCNICA
Ref: {ref} | Data: {data_prop}
================================================================================

{hotel}
Chamado Service Now: {chamado}
A/C: {contato_ac}

Conforme a vossa solicitação, apresentamos nossa proposta comercial e técnica para os seguintes itens:

--------------------------------------------------------------------------------
Descrição do Serviço                                    | Total
--------------------------------------------------------------------------------
{descricao:<55} | {valor}
--------------------------------------------------------------------------------

Condições comerciais:
{condicoes_txt}

--------------------------------------------------------------------------------
De acordo:
Razão Social: {razao}
CNPJ: {cnpj}
NOME: {nome_ass}    CARGO: {cargo_ass}
Email de cobrança: {email_cob}
Assinatura: ________________________________________
Data Assinatura: _______/________/________
================================================================================
    """

    # Versão em HTML elegante e corporativo
    condicoes_html = "".join([f"<li style='margin-bottom: 4px;'>{linha.strip()}</li>" for linha in condicoes.splitlines() if linha.strip()])
    
    corpo_html = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #f1f5f9; color: #1e293b; margin: 0; padding: 20px; }}
            .container {{ max-width: 750px; margin: 0 auto; background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 30px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
            .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; border: 1px solid #1e3a8a; }}
            .header-table td {{ padding: 10px 14px; font-size: 14px; font-weight: bold; background-color: #f8fafc; color: #1e3a8a; }}
            .hotel-info {{ margin-bottom: 20px; line-height: 1.6; font-size: 14px; }}
            .hotel-name {{ font-size: 18px; font-weight: bold; color: #0f172a; margin-bottom: 4px; }}
            .intro-text {{ margin-bottom: 18px; font-size: 14px; color: #334155; }}
            .items-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; }}
            .items-table th {{ background-color: #1e3a8a; color: #ffffff; text-align: left; padding: 10px 14px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .items-table td {{ border: 1px solid #cbd5e1; padding: 12px 14px; font-size: 14px; }}
            .items-table td.total {{ text-align: right; font-weight: bold; color: #1e3a8a; white-space: nowrap; width: 140px; font-size: 15px; }}
            .section-title {{ font-weight: bold; font-size: 14px; color: #0f172a; margin-top: 20px; margin-bottom: 8px; text-transform: uppercase; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }}
            .conditions-list {{ padding-left: 20px; font-size: 13px; color: #475569; line-height: 1.6; margin-bottom: 25px; }}
            .acceptance-box {{ border: 2px solid #94a3b8; border-radius: 4px; padding: 16px; background-color: #f8fafc; margin-top: 15px; font-size: 13px; line-height: 1.8; }}
            .footer-note {{ margin-top: 25px; font-size: 11px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Tabela de Cabeçalho / Referência -->
            <table class="header-table">
                <tr>
                    <td style="text-align: left; border-right: 1px solid #cbd5e1;">Ref: <strong>{ref}</strong></td>
                    <td style="text-align: right;">{data_prop}</td>
                </tr>
            </table>

            <!-- Identificação do Cliente / Hotel -->
            <div class="hotel-info">
                <div class="hotel-name">{hotel}</div>
                <div><strong>Chamado Service Now:</strong> {chamado}</div>
                <div><strong>A/C:</strong> {contato_ac}</div>
            </div>

            <!-- Introdução -->
            <div class="intro-text">
                Conforme a vossa solicitação, apresentamos nossa proposta comercial e técnica para os seguintes itens:
            </div>

            <!-- Tabela de Itens e Preços -->
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Descrição do Serviço</th>
                        <th style="text-align: right;">Total</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>{descricao}</strong></td>
                        <td class="total">{valor}</td>
                    </tr>
                </tbody>
            </table>

            <!-- Condições Comerciais -->
            <div class="section-title">Condições Comerciais:</div>
            <ul class="conditions-list">
                {condicoes_html}
            </ul>

            <!-- Quadro de "De acordo" -->
            <div class="section-title">De acordo:</div>
            <div class="acceptance-box">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="width: 50%; padding-bottom: 8px;"><strong>Razão Social:</strong> {razao}</td>
                        <td style="width: 50%; padding-bottom: 8px;"><strong>CNPJ:</strong> {cnpj}</td>
                    </tr>
                    <tr>
                        <td style="padding-bottom: 8px;"><strong>NOME:</strong> {nome_ass}</td>
                        <td style="padding-bottom: 8px;"><strong>CARGO:</strong> {cargo_ass}</td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding-bottom: 12px;"><strong>Email de cobrança:</strong> {email_cob}</td>
                    </tr>
                    <tr>
                        <td style="padding-top: 10px;"><strong>Assinatura:</strong> ________________________________________</td>
                        <td style="padding-top: 10px;"><strong>Data Assinatura:</strong> _______/________/________</td>
                    </tr>
                </table>
            </div>

            <div class="footer-note">
                Proposta gerada e enviada através do Portal de Gestão de Projetos.
            </div>
        </div>
    </body>
    </html>"""

    return assunto, corpo_texto, corpo_html


