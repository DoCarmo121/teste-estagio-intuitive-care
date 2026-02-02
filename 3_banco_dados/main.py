import os
import shutil
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# --- CONFIGURACOES DE CONEXAO ---
print("--- CONFIGURACAO DO BANCO DE DADOS ---")
DB_HOST = "localhost"
DB_NAME = "intuitive_care_db"
DB_USER = input("Digite seu usuario Postgres (ex: postgres): ") or "postgres"
DB_PASS = input("Digite sua senha Postgres: ")


def get_db_connection(db_name=None):
    return psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=db_name if db_name else "postgres"
    )


def criar_banco_se_nao_existir():
    print(f"Gerenciando banco de dados '{DB_NAME}'...")
    conn = get_db_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Verifica existencia do banco
    cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()

    if exists:
        print(f"   -> O banco '{DB_NAME}' ja existe. Recriando...")
        # Encerra conexoes ativas para permitir o DROP
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{DB_NAME}'
            AND pid <> pg_backend_pid();
        """)
        cur.execute(f"DROP DATABASE {DB_NAME}")

    print(f"   -> Criando banco limpo: '{DB_NAME}'...")
    cur.execute(f"CREATE DATABASE {DB_NAME}")

    cur.close()
    conn.close()


def preparar_arquivos_para_postgres(mapa_originais):
    print("Preparando arquivos para importacao...")
    temp_dir = "/tmp/intuitive_care_dados"

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.makedirs(temp_dir, exist_ok=True)
    os.chmod(temp_dir, 0o777)

    novos_caminhos = {}

    for placeholder, caminho_original in mapa_originais.items():
        if not os.path.exists(caminho_original):
            raise FileNotFoundError(
                f"Arquivo nao encontrado: {caminho_original}\n"
                f"Certifique-se de ter executado as Tarefas 1 e 2 com sucesso."
            )

        nome_arquivo = os.path.basename(caminho_original)
        caminho_temp = os.path.join(temp_dir, nome_arquivo)

        shutil.copy2(caminho_original, caminho_temp)

        # Permissao total para garantir leitura pelo Postgres
        os.chmod(caminho_temp, 0o666)

        novos_caminhos[placeholder] = caminho_temp
        print(f"   -> Arquivo preparado: {nome_arquivo}")

    return novos_caminhos


def executar_sql_arquivo(cursor, arquivo_sql, placeholders=None):
    print(f"Executando script: {os.path.basename(arquivo_sql)}...")
    with open(arquivo_sql, 'r', encoding='utf-8') as f:
        sql = f.read()

        if placeholders:
            for key, value in placeholders.items():
                # Ajuste de barras para compatibilidade SQL/SO
                clean_path = value.replace('\\', '/')
                sql = sql.replace(key, clean_path)

        cursor.execute(sql)
        print("   -> Sucesso.")


def main():
    try:
        # 1. Definicao de Caminhos Absolutos
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(base_dir)

        path_cadop = os.path.join(root_dir, "2_transformacao", "output", "relatorio_cadop.csv")
        path_despesas = os.path.join(root_dir, "1_etl_ans", "output", "consolidado_despesas.csv")
        path_agregado = os.path.join(root_dir, "2_transformacao", "output", "despesas_agregadas.csv")

        # 2. Preparacao de Arquivos (Bypass de Permissao)
        mapa_paths = {
            '{PATH_CADOP}': path_cadop,
            '{PATH_DESPESAS}': path_despesas,
            '{PATH_AGREGADO}': path_agregado
        }

        paths_seguros = preparar_arquivos_para_postgres(mapa_paths)

        # 3. Gerenciamento do Banco
        criar_banco_se_nao_existir()

        conn = get_db_connection(DB_NAME)
        conn.autocommit = True
        cur = conn.cursor()

        # 4. Execucao dos Scripts SQL
        executar_sql_arquivo(cur, os.path.join(base_dir, "1_ddl_criacao.sql"))
        executar_sql_arquivo(cur, os.path.join(base_dir, "2_importacao.sql"), paths_seguros)

        print("\nBANCO DE DADOS POPULADO COM SUCESSO.")
        print(f"Conecte-se ao banco '{DB_NAME}' para realizar as consultas.")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"\nERRO FATAL: {e}")
        # import traceback; traceback.print_exc() # Descomentar para debug


if __name__ == "__main__":
    main()
