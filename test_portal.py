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

    print("\n[SUCESSO] Todos os testes automatizados passaram com sucesso!")

if __name__ == "__main__":
    test_everything()
