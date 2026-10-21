import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Tuple
import database
import logic

def obter_config_smtp() -> Dict[str, Any]:
    configs = database.obter_configuracoes()
    return {
        "host": configs.get("smtp_host", ""),
        "port": int(configs.get("smtp_port", "587")) if configs.get("smtp_port") else 587,
        "usuario": configs.get("smtp_usuario", ""),
        "senha": configs.get("smtp_senha", ""),
        "remetente": configs.get("smtp_remetente", ""),
        "usar_tls": configs.get("smtp_usar_tls", "1") == "1",
        "usar_ssl": configs.get("smtp_usar_ssl", "0") == "1"
    }

def testar_conexao_smtp(config: Dict[str, Any]) -> Tuple[bool, str]:
    host = config.get("host", "").strip()
    port = int(config.get("port", 587))
    usuario = config.get("usuario", "").strip()
    senha = config.get("senha", "")
    usar_tls = config.get("usar_tls", True)
    usar_ssl = config.get("usar_ssl", False)
    
    if not host:
        return False, "O endereço do servidor SMTP (host) não foi informado."
    
    try:
        if usar_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            if usar_tls:
                server.starttls()
                
        if usuario and senha:
            server.login(usuario, senha)
            
        server.quit()
        return True, "Conexão e autenticação com o servidor SMTP estabelecidas com sucesso!"
    except smtplib.SMTPAuthenticationError:
        return False, "Erro de autenticação: Usuário ou senha do SMTP inválidos."
    except smtplib.SMTPConnectError:
        return False, f"Falha ao conectar no host {host}:{port}. Verifique o endereço e a porta."
    except Exception as e:
        return False, f"Erro ao conectar ao SMTP: {str(e)}"

def enviar_email_projeto(projeto: Dict[str, Any], config: Dict[str, Any] = None, lang: str = "pt_BR") -> Tuple[bool, str]:
    if config is None:
        config = obter_config_smtp()
        
    host = config.get("host", "").strip()
    port = int(config.get("port", 587))
    usuario = config.get("usuario", "").strip()
    senha = config.get("senha", "")
    remetente = config.get("remetente", "").strip() or usuario
    usar_tls = config.get("usar_tls", True)
    usar_ssl = config.get("usar_ssl", False)
    
    destinatario = projeto.get("email_responsavel", "").strip()
    
    if not host or not remetente:
        return False, "Configurações de SMTP incompletas. Acesse a aba '⚙️ Configurações SMTP' para configurar o servidor."
    if not destinatario or "@" not in destinatario:
        return False, f"E-mail do responsável inválido ou vazio: '{destinatario}'"

    metricas = logic.calcular_metricas_projeto(projeto)
    assunto, corpo_texto, corpo_html = logic.gerar_conteudo_email_alerta(projeto, metricas, lang=lang)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    part1 = MIMEText(corpo_texto, "plain", "utf-8")
    part2 = MIMEText(corpo_html, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        if usar_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if usar_tls:
                server.starttls()
                
        if usuario and senha:
            server.login(usuario, senha)
            
        server.sendmail(remetente, [destinatario], msg.as_string())
        server.quit()
        
        # Registrar no banco de dados que o aviso foi enviado
        database.registrar_envio_aviso(projeto["id"])
        return True, f"E-mail enviado com sucesso para {destinatario}!"
    except Exception as e:
        return False, f"Falha ao enviar e-mail: {str(e)}"

def enviar_email_proposta(proposta: Dict[str, Any], config: Dict[str, Any] = None, lang: str = "pt_BR") -> Tuple[bool, str]:
    if config is None:
        config = obter_config_smtp()
        
    host = config.get("host", "").strip()
    port = int(config.get("port", 587))
    usuario = config.get("usuario", "").strip()
    senha = config.get("senha", "")
    remetente = config.get("remetente", "").strip() or usuario
    usar_tls = config.get("usar_tls", True)
    usar_ssl = config.get("usar_ssl", False)
    
    destinatario = (proposta.get("email_destinatario") or "").strip()
    
    if not host or not remetente:
        return False, "Configurações de SMTP incompletas. Acesse a aba '⚙️ Configurações SMTP' para configurar o servidor."
    if not destinatario or "@" not in destinatario:
        return False, f"E-mail de destino da proposta inválido ou vazio: '{destinatario}'"

    assunto, corpo_texto, corpo_html = logic.gerar_conteudo_email_proposta(proposta, lang=lang)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    part1 = MIMEText(corpo_texto, "plain", "utf-8")
    part2 = MIMEText(corpo_html, "html", "utf-8")
    msg.attach(part1)
    msg.attach(part2)

    try:
        if usar_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            server = smtplib.SMTP(host, port, timeout=15)
            if usar_tls:
                server.starttls()
                
        if usuario and senha:
            server.login(usuario, senha)
            
        server.sendmail(remetente, [destinatario], msg.as_string())
        server.quit()
        
        # Atualizar status da proposta no banco para 'Proposta Enviada'
        from datetime import datetime
        agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
        if proposta.get("id"):
            database.atualizar_status_proposta(proposta["id"], "Proposta Enviada", data_envio=agora)
            
        return True, f"Proposta comercial enviada com sucesso para {destinatario}!"
    except Exception as e:
        return False, f"Falha ao enviar proposta via SMTP: {str(e)}"

