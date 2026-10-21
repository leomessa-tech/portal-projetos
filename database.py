import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.environ.get("PORTAL_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "projetos.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA busy_timeout = 20000")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Projetos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data_inicio TEXT NOT NULL,
            data_termino TEXT NOT NULL,
            data_aviso TEXT NOT NULL,
            responsavel TEXT NOT NULL,
            email_responsavel TEXT NOT NULL,
            concluido INTEGER DEFAULT 0,
            ultimo_aviso_enviado TEXT,
            observacoes TEXT,
            prioridade TEXT DEFAULT 'Média',
            status_manual TEXT DEFAULT 'Em Execução',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migração segura para tabelas já existentes
    cursor.execute("PRAGMA table_info(projetos)")
    colunas_existentes = [col[1] for col in cursor.fetchall()]
    if "prioridade" not in colunas_existentes:
        cursor.execute("ALTER TABLE projetos ADD COLUMN prioridade TEXT DEFAULT 'Média'")
    if "status_manual" not in colunas_existentes:
        cursor.execute("ALTER TABLE projetos ADD COLUMN status_manual TEXT DEFAULT 'Em Execução'")
    
    # Tabela de Configurações (ex: SMTP)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)
    
    # Tabela de Usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT,
            senha_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Migração segura para tabelas já existentes
    cursor.execute("PRAGMA table_info(usuarios)")
    colunas_existentes_u = [col[1] for col in cursor.fetchall()]
    if "ativo" not in colunas_existentes_u:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER DEFAULT 1")
    
    # Tabela de Propostas Comerciais e Técnicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            referencia TEXT NOT NULL,
            data_proposta TEXT NOT NULL,
            hotel_cliente TEXT NOT NULL,
            chamado_servicenow TEXT DEFAULT 'N/A',
            contato_ac TEXT DEFAULT 'Hotel',
            descricao_servico TEXT NOT NULL,
            valor_total REAL NOT NULL DEFAULT 0.0,
            condicoes_comerciais TEXT,
            email_destinatario TEXT,
            razao_social TEXT,
            cnpj TEXT,
            nome_assinatura TEXT,
            cargo_assinatura TEXT,
            email_cobranca TEXT,
            status TEXT DEFAULT 'Em Elaboração',
            data_envio TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id) ON DELETE CASCADE
        )
    """)
    
    # Verificar se existe usuário cadastrado, se não, cria admin inicial
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    total_users = cursor.fetchone()["total"]
    if total_users == 0:
        import auth
        h, s = auth.hash_senha("admin123")
        cursor.execute("""
            INSERT INTO usuarios (username, nome, email, senha_hash, salt, is_admin)
            VALUES (?, ?, ?, ?, ?, 1)
        """, ("admin", "Administrador", "admin@empresa.com.br", h, s))
    
    conn.commit()
    conn.close()

# --- Operações de Projetos ---

def listar_projetos() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*,
               pr.id AS proposta_id,
               pr.status AS proposta_status,
               pr.referencia AS proposta_referencia,
               pr.valor_total AS proposta_valor,
               pr.data_envio AS proposta_data_envio
        FROM projetos p
        LEFT JOIN propostas pr ON pr.id = (
            SELECT id FROM propostas WHERE projeto_id = p.id ORDER BY id DESC LIMIT 1
        )
        ORDER BY p.data_termino ASC, p.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def obter_projeto(projeto_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projetos WHERE id = ?", (projeto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def criar_projeto(
    nome: str,
    data_inicio: str,
    data_termino: str,
    data_aviso: str,
    responsavel: str,
    email_responsavel: str,
    observacoes: str = "",
    prioridade: str = "Média",
    status_manual: str = "Em Execução"
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO projetos (nome, data_inicio, data_termino, data_aviso, responsavel, email_responsavel, observacoes, prioridade, status_manual, concluido)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (nome.strip(), data_inicio, data_termino, data_aviso, responsavel.strip(), email_responsavel.strip(), observacoes.strip(), prioridade.strip(), status_manual.strip()))
    projeto_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return projeto_id

def atualizar_projeto(
    projeto_id: int,
    nome: str,
    data_inicio: str,
    data_termino: str,
    data_aviso: str,
    responsavel: str,
    email_responsavel: str,
    concluido: int,
    observacoes: str = "",
    prioridade: str = "Média",
    status_manual: str = "Em Execução"
):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projetos
        SET nome = ?, data_inicio = ?, data_termino = ?, data_aviso = ?,
            responsavel = ?, email_responsavel = ?, concluido = ?, observacoes = ?,
            prioridade = ?, status_manual = ?
        WHERE id = ?
    """, (nome.strip(), data_inicio, data_termino, data_aviso, responsavel.strip(), email_responsavel.strip(), concluido, observacoes.strip(), prioridade.strip(), status_manual.strip(), projeto_id))
    conn.commit()
    conn.close()

def alternar_conclusao(projeto_id: int, novo_status: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projetos SET concluido = ? WHERE id = ?", (novo_status, projeto_id))
    conn.commit()
    conn.close()

def excluir_projeto(projeto_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projetos WHERE id = ?", (projeto_id,))
    conn.commit()
    conn.close()

def registrar_envio_aviso(projeto_id: int):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE projetos SET ultimo_aviso_enviado = ? WHERE id = ?", (agora, projeto_id))
    conn.commit()
    conn.close()

# --- Operações de Configurações ---

def obter_configuracoes() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM configuracoes")
    rows = cursor.fetchall()
    conn.close()
    return {row["chave"]: row["valor"] for row in rows}

def salvar_configuracao(chave: str, valor: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
        ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
    """, (chave, valor))
    conn.commit()
    conn.close()

def salvar_configuracoes_smtp(smtp_data: Dict[str, str]):
    conn = get_connection()
    cursor = conn.cursor()
    for chave, valor in smtp_data.items():
        cursor.execute("""
            INSERT INTO configuracoes (chave, valor) VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
        """, (chave, valor))
    conn.commit()
    conn.close()

# --- Operações de Usuários e Autenticação ---

def criar_usuario(username: str, nome: str, email: str, senha: str, is_admin: int = 0, ativo: int = 1) -> Tuple[bool, str]:
    import auth
    username = username.strip().lower()
    nome = nome.strip()
    email = email.strip()
    
    if not username or not nome or not senha:
        return False, "Usuário, Nome e Senha são obrigatórios."
    if len(senha) < 4:
        return False, "A senha deve conter no mínimo 4 caracteres."
        
    conn = get_connection()
    cursor = conn.cursor()
    try:
        senha_hash, salt = auth.hash_senha(senha)
        cursor.execute("""
            INSERT INTO usuarios (username, nome, email, senha_hash, salt, is_admin, ativo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (username, nome, email, senha_hash, salt, is_admin, ativo))
        conn.commit()
        conn.close()
        return True, "Usuário cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"O nome de usuário '{username}' já está em uso."
    except Exception as e:
        conn.close()
        return False, f"Erro ao criar usuário: {str(e)}"

def autenticar_usuario(username: str, senha: str) -> Optional[Dict[str, Any]]:
    import auth
    username = username.strip().lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    dados = dict(row)
    if auth.verificar_senha(senha, dados["senha_hash"], dados["salt"]):
        # Remove hashes antes de retornar
        dados.pop("senha_hash", None)
        dados.pop("salt", None)
        if dados.get("ativo", 1) == 0:
            return {"inativo": True, "username": username, "nome": dados.get("nome", "")}
        return dados
    return None

def listar_usuarios() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, nome, email, is_admin, ativo, created_at FROM usuarios ORDER BY nome ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def alternar_status_usuario(usuario_id: int, ativo: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (ativo, usuario_id))
        conn.commit()
        conn.close()
        return True, "Status do usuário alterado com sucesso."
    except Exception as e:
        conn.close()
        return False, f"Erro ao alterar status: {str(e)}"

def excluir_usuario(usuario_id: int) -> Tuple[bool, str]:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        conn.commit()
        conn.close()
        return True, "Usuário excluído com sucesso."
    except Exception as e:
        conn.close()
        return False, f"Erro ao excluir usuário: {str(e)}"

# --- Operações de Propostas Comerciais & Técnicas ---

def obter_proposta_por_projeto(projeto_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM propostas 
        WHERE projeto_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (projeto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def proxima_referencia_proposta() -> str:
    """Gera o próximo sequencial de referência no padrão 26-XXX (ano-sequencial)."""
    ano_abrev = datetime.now().strftime("%y")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM propostas")
    row = cursor.fetchone()
    total = (row["total"] if row else 0) + 1
    conn.close()
    return f"{ano_abrev}-{total:03d}"

def salvar_proposta(
    projeto_id: int,
    referencia: str,
    data_proposta: str,
    hotel_cliente: str,
    chamado_servicenow: str,
    contato_ac: str,
    descricao_servico: str,
    valor_total: float,
    condicoes_comerciais: str,
    email_destinatario: str,
    razao_social: str = "",
    cnpj: str = "",
    nome_assinatura: str = "",
    cargo_assinatura: str = "",
    email_cobranca: str = "",
    status: str = "Em Elaboração"
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM propostas WHERE projeto_id = ? ORDER BY id DESC LIMIT 1", (projeto_id,))
    existente = cursor.fetchone()
    
    if existente:
        prop_id = existente["id"]
        cursor.execute("""
            UPDATE propostas
            SET referencia = ?, data_proposta = ?, hotel_cliente = ?, chamado_servicenow = ?,
                contato_ac = ?, descricao_servico = ?, valor_total = ?, condicoes_comerciais = ?,
                email_destinatario = ?, razao_social = ?, cnpj = ?, nome_assinatura = ?,
                cargo_assinatura = ?, email_cobranca = ?, status = ?
            WHERE id = ?
        """, (
            referencia.strip(), data_proposta.strip(), hotel_cliente.strip(), chamado_servicenow.strip(),
            contato_ac.strip(), descricao_servico.strip(), float(valor_total), condicoes_comerciais.strip(),
            email_destinatario.strip(), razao_social.strip(), cnpj.strip(), nome_assinatura.strip(),
            cargo_assinatura.strip(), email_cobranca.strip(), status.strip(), prop_id
        ))
    else:
        cursor.execute("""
            INSERT INTO propostas (
                projeto_id, referencia, data_proposta, hotel_cliente, chamado_servicenow,
                contato_ac, descricao_servico, valor_total, condicoes_comerciais,
                email_destinatario, razao_social, cnpj, nome_assinatura,
                cargo_assinatura, email_cobranca, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            projeto_id, referencia.strip(), data_proposta.strip(), hotel_cliente.strip(), chamado_servicenow.strip(),
            contato_ac.strip(), descricao_servico.strip(), float(valor_total), condicoes_comerciais.strip(),
            email_destinatario.strip(), razao_social.strip(), cnpj.strip(), nome_assinatura.strip(),
            cargo_assinatura.strip(), email_cobranca.strip(), status.strip()
        ))
        prop_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    return prop_id

def atualizar_status_proposta(proposta_id: int, novo_status: str, data_envio: str = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if data_envio:
            cursor.execute("UPDATE propostas SET status = ?, data_envio = ? WHERE id = ?", (novo_status, data_envio, proposta_id))
        else:
            cursor.execute("UPDATE propostas SET status = ? WHERE id = ?", (novo_status, proposta_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

def excluir_proposta(proposta_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM propostas WHERE id = ?", (proposta_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False

