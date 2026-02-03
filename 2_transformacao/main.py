import pandas as pd
import requests
import os
import zipfile
import re
from io import StringIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

# --- CONFIGURACOES ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.abspath(os.path.join(CURRENT_DIR, "..", "1_etl_ans", "output", "consolidado_despesas.csv"))
BASE_FTP = "https://dadosabertos.ans.gov.br/FTP/PDA/"
OUTPUT_DIR = "output"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "despesas_agregadas.csv")
OUTPUT_ZIP = os.path.join(OUTPUT_DIR, "Teste_JoaoGabriel.zip")
# Caminho para persistir o CADOP bruto para uso na tarefa de Banco de Dados
OUTPUT_CADOP = os.path.join(OUTPUT_DIR, "relatorio_cadop.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def validar_cnpj(cnpj):
    '''Valida CNPJ usando Algoritmo Modulo 11'''
    cnpj = re.sub(r'\D', '', str(cnpj))
    if len(cnpj) != 14 or len(set(cnpj)) == 1: return False

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    digito1 = 11 - (soma1 % 11)
    digito1 = 0 if digito1 >= 10 else digito1
    if digito1 != int(cnpj[12]): return False

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 11 - (soma2 % 11)
    digito2 = 0 if digito2 >= 10 else digito2
    return digito2 == int(cnpj[13])


def obter_url_cadop_dinamica():
    '''Busca a URL correta do CSV de Operadoras Ativas via Scraping'''
    try:
        print(f"Buscando URL do CADOP em: {BASE_FTP}")
        response = requests.get(BASE_FTP, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')

        link_pasta = None
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and 'operadora' in href.lower() and 'ativa' in href.lower():
                link_pasta = href
                break

        # Fallback se nao encontrar a pasta
        if not link_pasta:
            return "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_planos_de_saude_ativas/Relatorio_Cadop.csv"

        url_pasta = urljoin(BASE_FTP, link_pasta)

        resp_pasta = requests.get(url_pasta, timeout=30)
        soup_pasta = BeautifulSoup(resp_pasta.text, 'html.parser')

        for a in soup_pasta.find_all('a'):
            href = a.get('href')
            if href and href.lower().endswith('.csv'):
                if 'relatorio' in href.lower() or 'cadop' in href.lower():
                    url_encontrada = urljoin(url_pasta, href)
                    print(f"URL encontrada: {url_encontrada}")
                    return url_encontrada
        return None
    except Exception as e:
        print(f"Erro no scraping: {e}")
        return None


def baixar_cadop():
    '''Baixa, processa e salva o arquivo de operadoras'''
    print("Iniciando download do Cadastro de Operadoras (CADOP)...")
    url = obter_url_cadop_dinamica()
    if not url: raise Exception("URL CADOP nao encontrada.")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        try:
            texto_csv = response.content.decode('latin-1')
        except UnicodeDecodeError:
            texto_csv = response.content.decode('cp1252', errors='replace')

        df = pd.read_csv(StringIO(texto_csv), sep=';', dtype=str, on_bad_lines='skip')

        # Normalizacao de colunas
        df.columns = [c.strip().upper().replace('RAZAO_SOCIAL', 'RazaoSocial') for c in df.columns]
        col_map = {
            'REGISTRO_OPERADORA': 'RegistroANS',
            'REGISTRO_ANS': 'RegistroANS', 'REG_ANS': 'RegistroANS', 'CD_OPS': 'RegistroANS', 'CODIGO': 'RegistroANS',
            'CNPJ': 'CNPJ', 'RAZAO_SOCIAL': 'RazaoSocial', 'MODALIDADE': 'Modalidade', 'UF': 'UF'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        if 'RegistroANS' not in df.columns: raise Exception("Coluna RegistroANS nao encontrada no CADOP.")

        # Seleciona apenas colunas uteis
        cols = ['RegistroANS', 'CNPJ', 'RazaoSocial', 'Modalidade', 'UF']
        df_limpo = df[[c for c in cols if c in df.columns]]

        print(f"Salvando copia local do CADOP: {OUTPUT_CADOP}")

        df_limpo.to_csv(OUTPUT_CADOP, index=False, sep=';', encoding='utf-8')

        return df_limpo

    except Exception as e:
        print(f"Erro no processamento do CADOP: {e}")
        return None

def enriquecer_dados(df_despesas, df_cadop):
    print("Cruzando dados (Join)...")

    # Tratamento de chave para garantir match
    df_despesas['RegistroANS'] = df_despesas['RegistroANS'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df_cadop['RegistroANS'] = df_cadop['RegistroANS'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # Left Join para manter todas as despesas mesmo sem cadastro
    df_final = df_despesas.merge(df_cadop, on='RegistroANS', how='left', suffixes=('_orig', ''))

    # Preenchimento de nulos pos-join
    df_final['CNPJ'] = df_final['CNPJ'].fillna('N/A')
    df_final['RazaoSocial'] = df_final['RazaoSocial'].fillna(f"Operadora {df_final['RegistroANS']} Desconhecida")
    df_final['UF'] = df_final['UF'].fillna('N/A')

    return df_final


def processar_agregacao(df):
    print("Calculando estatisticas...")
    df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce').fillna(0)

    # Agrupa por Operadora e UF
    agregado = df.groupby(['RegistroANS', 'CNPJ', 'RazaoSocial', 'UF'])['ValorDespesas'].agg(
        ValorTotal='sum',
        MediaTrimestral='mean',
        DesvioPadrao='std',
        QtdRegistros='count'
    ).reset_index()

    agregado['DesvioPadrao'] = agregado['DesvioPadrao'].fillna(0)
    return agregado.sort_values(by='ValorTotal', ascending=False)


if __name__ == "__main__":
    try:
        print(f"Lendo Tarefa 1: {INPUT_FILE}")
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError("Arquivo da Tarefa 1 nao encontrado. Execute a etapa anterior primeiro.")

        df_raw = pd.read_csv(INPUT_FILE, sep=";", dtype=str, encoding='utf-8')

        df_raw = df_raw.drop(columns=['CNPJ', 'RazaoSocial'], errors='ignore')

        # Baixa CADOP e salva em disco
        df_cadop = baixar_cadop()
        if df_cadop is None: raise Exception("Falha critica ao obter dados do CADOP.")

        # Enriquecimento
        df_enriched = enriquecer_dados(df_raw, df_cadop)

        # Validacao CNPJ
        df_enriched['CNPJ_Valido'] = df_enriched['CNPJ'].apply(validar_cnpj)

        # Agregacao Final
        df_final = processar_agregacao(df_enriched)

        print(f"Salvando Agregado: {OUTPUT_CSV}")
        df_final.to_csv(OUTPUT_CSV, index=False, sep=';', encoding='utf-8', float_format='%.2f')

        with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(OUTPUT_CSV, arcname="despesas_agregadas.csv")

        print("TAREFA 2 CONCLUIDA COM SUCESSO.")

    except Exception as e:
        print(f"ERRO FATAL: {e}")