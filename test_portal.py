import database
import logic
import email_service

import seed_data

def test_everything():
    seed_data.popular_dados_exemplo(forcar=True)
    projs = database.listar_projetos()
    print(f"Total de projetos carregados: {len(projs)}")
    assert len(projs) >= 4, "Deveriam existir pelo menos 4 projetos de exemplo."
    
    statuses_encontrados = set()
    for p in projs:
        m = logic.calcular_metricas_projeto(p)
        statuses_encontrados.add(m["status"])
        assunto, texto, html = logic.gerar_conteudo_email_alerta(p, m)
        assert len(assunto) > 0
        assert len(texto) > 0
        assert len(html) > 0
        print(f"-> [{m['status']}] {p['nome']} (Resp: {p['responsavel']})")
        
    print("Status identificados:", statuses_encontrados)
    assert "No Prazo" in statuses_encontrados
    assert "Chegando ao Fim" in statuses_encontrados
    assert "Atrasado" in statuses_encontrados
    assert "Concluído" in statuses_encontrados
    
    # Testar CRUD com prioridade e status manual
    novo_id = database.criar_projeto(
        nome="Projeto Teste Unitário",
        data_inicio="2026-10-01",
        data_termino="2026-10-31",
        data_aviso="2026-10-25",
        responsavel="Testador",
        email_responsavel="teste@exemplo.com",
        observacoes="Criado pelo teste",
        prioridade="Crítica",
        status_manual="Em Homologação"
    )
    p_criado = database.obter_projeto(novo_id)
    assert p_criado is not None
    assert p_criado["nome"] == "Projeto Teste Unitário"
    assert p_criado["prioridade"] == "Crítica"
    assert p_criado["status_manual"] == "Em Homologação"
    
    # Testar atualização
    database.atualizar_projeto(
        projeto_id=novo_id,
        nome="Projeto Teste Atualizado",
        data_inicio="2026-10-01",
        data_termino="2026-10-31",
        data_aviso="2026-10-25",
        responsavel="Testador",
        email_responsavel="teste@exemplo.com",
        concluido=0,
        observacoes="Observação atualizada",
        prioridade="Alta",
        status_manual="Em Pausa"
    )
    p_atualizado = database.obter_projeto(novo_id)
    assert p_atualizado["prioridade"] == "Alta"
    assert p_atualizado["status_manual"] == "Em Pausa"
    
    database.excluir_projeto(novo_id)
    assert database.obter_projeto(novo_id) is None
    
    # Testar verificação SMTP sem host
    ok, msg = email_service.testar_conexao_smtp({})
    assert not ok
    
    # Testar internacionalização (i18n) em 4 idiomas
    import i18n
    for lang in ["pt_BR", "en_US", "es_ES", "fr_FR"]:
        title = i18n.t("portal_title", lang)
        assert len(title) > 0, f"Título vazio no idioma {lang}"
        # Testar geração de e-mail no idioma
        assunto_l, texto_l, html_l = logic.gerar_conteudo_email_alerta(projs[0], logic.calcular_metricas_projeto(projs[0]), lang=lang)
        assert len(assunto_l) > 0
        assert len(texto_l) > 0
        assert len(html_l) > 0
        print(f"-> i18n [{lang}] OK")

    # Testar Autenticação e Usuários
    database.init_db()
    admin_user = database.autenticar_usuario("admin", "admin123")
    assert admin_user is not None, "Usuário admin inicial não foi autenticado."
    assert admin_user["username"] == "admin"
    
    # Testar falha de login com senha errada
    assert database.autenticar_usuario("admin", "senha_errada") is None
    
    # Testar cadastro de novo usuário (idempotente)
    import time
    test_user = f"gestor_{int(time.time())}"
    ok_user, msg_user = database.criar_usuario(test_user, "Gestor de Teste", "gestor@empresa.com", "senha123")
    assert ok_user, f"Falha ao criar usuário: {msg_user}"
    
    # Testar login do novo usuário
    user_logado = database.autenticar_usuario(test_user, "senha123")
    assert user_logado is not None
    assert user_logado["nome"] == "Gestor de Teste"
    
    # Testar bloqueio de duplicidade de username
    ok_dup, _ = database.criar_usuario(test_user, "Outro", "outro@empresa.com", "1234")
    assert not ok_dup, "Deveria bloquear criação de username duplicado."

    # Testar inativação de usuário
    ok_inativar, _ = database.alternar_status_usuario(user_logado["id"], 0)
    assert ok_inativar
    tentativa_inativo = database.autenticar_usuario(test_user, "senha123")
    assert tentativa_inativo is not None and tentativa_inativo.get("inativo") is True, "Usuário inativo não deveria conseguir logar."

    # Testar reativação de usuário
    ok_ativar, _ = database.alternar_status_usuario(user_logado["id"], 1)
    assert ok_ativar
    tentativa_ativo = database.autenticar_usuario(test_user, "senha123")
    assert tentativa_ativo is not None and tentativa_ativo.get("inativo") is not True, "Usuário reativado deveria conseguir logar."

    # Testar exclusão de usuário
    ok_del, _ = database.excluir_usuario(user_logado["id"])
    assert ok_del
    assert database.autenticar_usuario(test_user, "senha123") is None, "Usuário excluído não deveria existir."

    print("-> Autenticacao, Inativacao e Gestao de Usuarios [OK]")

    # Testar Emissão de Relatórios em Excel e PDF
    import report_generator
    filtros_teste = {"Status": "No Prazo", "Prioridade": "Alta", "Responsável": "Carlos Eduardo"}
    
    for l in ["pt_BR", "en_US", "es_ES", "fr_FR"]:
        excel_out = report_generator.gerar_relatorio_excel(projs, lang=l, filtros=filtros_teste)
        assert len(excel_out) > 1000, f"Excel gerado muito pequeno para {l}: {len(excel_out)} bytes"
        
        pdf_out = report_generator.gerar_relatorio_pdf(projs, lang=l, filtros=filtros_teste)
        assert len(pdf_out) > 1000, f"PDF gerado muito pequeno para {l}: {len(pdf_out)} bytes"
        print(f"-> Relatórios Excel & PDF [{l}] OK (Excel: {len(excel_out)} B, PDF: {len(pdf_out)} B)")

        # Testar Propostas Comerciais & Técnicas
    proj_prop = projs[0]
    ref_gerada = database.proxima_referencia_proposta()
    assert len(ref_gerada) >= 5, f"Referência inválida: {ref_gerada}"
    
    prop_id = database.salvar_proposta(
        projeto_id=proj_prop["id"],
        referencia=ref_gerada,
        data_proposta="21 de Outubro de 2026",
        hotel_cliente="7859 - Ibis Budget Campo Grande",
        chamado_servicenow="INC123456",
        contato_ac="Hotel",
        descricao_servico="Instalação de interface e configuração de rede",
        valor_total=938.00,
        condicoes_comerciais=logic.CONDICOES_COMERCIAIS_PADRAO,
        email_destinatario="propostas@accor.com",
        razao_social="Accor Brasil Hotéis Ltda",
        cnpj="12.345.678/0001-90",
        nome_assinatura="Gerente Geral",
        cargo_assinatura="Gerente de TI",
        email_cobranca="cobranca@accor.com",
        status="Em Elaboração"
    )
    assert prop_id > 0, "ID da proposta deveria ser maior que 0"
    
    prop_carregada = database.obter_proposta_por_projeto(proj_prop["id"])
    assert prop_carregada is not None
    assert prop_carregada["referencia"] == ref_gerada
    assert prop_carregada["valor_total"] == 938.00
    assert prop_carregada["status"] == "Em Elaboração"
    
    # Testar formatação de email da proposta
    for l in ["pt_BR", "en_US", "es_ES", "fr_FR"]:
        p_assunto, p_txt, p_html = logic.gerar_conteudo_email_proposta(prop_carregada, lang=l)
        assert ref_gerada in p_assunto
        assert "7859 - Ibis Budget Campo Grande" in p_txt
        assert "R$ 938,00" in p_html
        assert "Accor Brasil" in p_html
        
    # Testar geração de PDF da proposta
    pdf_prop_bytes = report_generator.gerar_proposta_pdf(prop_carregada)
    assert len(pdf_prop_bytes) > 1000, f"PDF da proposta muito pequeno: {len(pdf_prop_bytes)} bytes"
    
    # Testar transição de status da proposta
    database.atualizar_status_proposta(prop_id, "Proposta Enviada", data_envio="21/10/2026 às 10:00")
    prop_enviada = database.obter_proposta_por_projeto(proj_prop["id"])
    assert prop_enviada["status"] == "Proposta Enviada"
    assert prop_enviada["data_envio"] == "21/10/2026 às 10:00"
    
    database.atualizar_status_proposta(prop_id, "Proposta Aprovada")
    prop_aprovada = database.obter_proposta_por_projeto(proj_prop["id"])
    assert prop_aprovada["status"] == "Proposta Aprovada"
    
    database.atualizar_status_proposta(prop_id, "Proposta Recusada")
    prop_recusada = database.obter_proposta_por_projeto(proj_prop["id"])
    assert prop_recusada["status"] == "Proposta Recusada"
    
    # Testar se listar_projetos inclui dados da proposta associada
    projs_com_prop = database.listar_projetos()
    proj_com_prop_item = next((p for p in projs_com_prop if p["id"] == proj_prop["id"]), None)
    assert proj_com_prop_item is not None
    assert proj_com_prop_item["proposta_id"] == prop_id
    assert proj_com_prop_item["proposta_status"] == "Proposta Recusada"
    assert proj_com_prop_item["proposta_referencia"] == ref_gerada
    assert proj_com_prop_item["proposta_valor"] == 938.00
    
    # Limpeza da proposta de teste
    database.excluir_proposta(prop_id)
    assert database.obter_proposta_por_projeto(proj_prop["id"]) is None
    print("-> Gestão de Propostas Comerciais, SMTP, PDF & Status [OK]")

    print("\n[SUCESSO] Todos os testes automatizados passaram com sucesso!")

if __name__ == "__main__":
    test_everything()
