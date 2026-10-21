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
    cursor.execute("SELECT * FROM projetos ORDER BY data_termino ASC, id DESC")
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

