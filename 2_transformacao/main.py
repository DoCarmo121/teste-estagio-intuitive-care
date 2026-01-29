import pandas as pd
import requests
import os
import zipfile
import re
from io import StringIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

INPUT_FILE = "../1_etl_ans/output/consolidado_despesas.csv"
BASE_FTP = "https://dadosabertos.ans.gov.br/FTP/PDA/"
OUTPUT_DIR = "output"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "despesas_agregadas.csv")
OUTPUT_ZIP = os.path.join(OUTPUT_DIR, "Teste_JoaoGabriel.zip")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def validar_cnpj(cnpj):
    '''Algoritmo Modulo 11'''
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
    try:
        print(f"🔍 Acessando raiz: {BASE_FTP}")
        response = requests.get(BASE_FTP, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        link_pasta = None
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and 'operadora' in href.lower() and 'ativa' in href.lower():
                link_pasta = href
                break

        if not link_pasta:
            # Fallback seguro
            return "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_planos_de_saude_ativas/Relatorio_Cadop.csv"

        url_pasta = urljoin(BASE_FTP, link_pasta)
        print(f"Pasta encontrada: {link_pasta}")

        resp_pasta = requests.get(url_pasta, timeout=30)
        soup_pasta = BeautifulSoup(resp_pasta.text, 'html.parser')

        for a in soup_pasta.find_all('a'):
            href = a.get('href')
            if href and href.lower().endswith('.csv'):
                if 'relatorio' in href.lower() or 'cadop' in href.lower():
                    url_final = urljoin(url_pasta, href)
                    print(f"Arquivo encontrado: {href}")
                    return url_final
        return None

    except Exception as e:
        print(f"Erro na busca dinâmica: {e}")
        return None


def baixar_cadop():
    print("\nIniciando download do CADOP...")
    url = obter_url_cadop_dinamica()
    if not url: raise Exception("\nNão foi possível localizar o endereço do CADOP.")

    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text), sep=';', encoding='latin-1', dtype=str, on_bad_lines='skip')

        df.columns = [c.strip().upper().replace('RAZAO_SOCIAL', 'RazaoSocial') for c in df.columns]


        col_map = {
            'REGISTRO_OPERADORA': 'RegistroANS',
            'REGISTRO_ANS': 'RegistroANS',
            'REG_ANS': 'RegistroANS',  # Variação comum
            'CD_OPS': 'RegistroANS',  # Variação comum
            'CODIGO': 'RegistroANS',  # Variação comum
            'CNPJ': 'CNPJ',
            'RAZAO_SOCIAL': 'RazaoSocial',
            'MODALIDADE': 'Modalidade',
            'UF': 'UF'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Garante que RegistroANS existe
        if 'RegistroANS' not in df.columns:
            raise Exception(f"\nColuna RegistroANS não encontrada no CADOP. Colunas disponíveis: {df.columns}")

        cols = ['RegistroANS', 'CNPJ', 'RazaoSocial', 'Modalidade', 'UF']
        return df[[c for c in cols if c in df.columns]]

    except Exception as e:
        print(f"\nErro ao baixar/ler o CSV: {e}")
        return None


def enriquecer_dados(df_despesas, df_cadop):
    print("\nCruzando dados (Join)...")

    if 'RegistroANS' not in df_despesas.columns:
        print(f"\nERRO: O arquivo da Tarefa 1 não tem a coluna 'RegistroANS'.")
        print(f"\nColunas atuais: {df_despesas.columns.tolist()}")
        raise KeyError("\nRegistroANS faltando na origem (Tarefa 1)")

    df_despesas['RegistroANS'] = df_despesas['RegistroANS'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    df_cadop['RegistroANS'] = df_cadop['RegistroANS'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)

    # Join
    df_final = df_despesas.merge(df_cadop, on='RegistroANS', how='left', suffixes=('_orig', ''))

    df_final['CNPJ'] = df_final['CNPJ'].fillna('N/A')
    df_final['RazaoSocial'] = df_final['RazaoSocial'].fillna(f"Operadora {df_final['RegistroANS']} Desconhecida")
    df_final['UF'] = df_final['UF'].fillna('N/A')
    return df_final


def processar_agregacao(df):
    print("\n📊 Calculando estatísticas...")
    df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce').fillna(0)

    agregado = df.groupby(['RegistroANS', 'CNPJ', 'RazaoSocial', 'UF'])['ValorDespesas'].agg(
        ValorTotal='sum',
        MediaTrimestral='mean',
        DesvioPadrao='std',
        QtdRegistros='count'
    ).reset_index()

    agregado['DesvioPadrao'] = agregado['DesvioPadrao'].fillna(0)
    agregado = agregado.sort_values(by='ValorTotal', ascending=False)
    return agregado


if __name__ == "__main__":
    try:
        print(f"Lendo: {INPUT_FILE}")
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError("\nArquivo da Tarefa 1 não encontrado. Rode 'python 1_etl_ans/main.py' primeiro.")

        df_raw = pd.read_csv(INPUT_FILE, sep=";", dtype=str)

        # Limpeza preventiva
        df_raw = df_raw.drop(columns=['CNPJ', 'RazaoSocial'], errors='ignore')

        # Baixa CADOP
        df_cadop = baixar_cadop()
        if df_cadop is None: raise Exception("\nFalha crítica no CADOP.")

        # Enriquecimento
        df_enriched = enriquecer_dados(df_raw, df_cadop)

        print("\nValidando CNPJs...")
        df_enriched['CNPJ_Valido'] = df_enriched['CNPJ'].apply(validar_cnpj)

        # Log de Auditoria
        qtd_inv = len(df_enriched[~df_enriched['CNPJ_Valido']])
        if qtd_inv > 0:
            print(f"\nALERTA: {qtd_inv} registros possuem CNPJs inválidos (mantidos para cálculo financeiro).")

        # Agregação
        df_final = processar_agregacao(df_enriched)

        print(f"\nSalvando: {OUTPUT_CSV}")
        df_final.to_csv(OUTPUT_CSV, index=False, sep=';', encoding='utf-8', float_format='%.2f')

        with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(OUTPUT_CSV, arcname="despesas_agregadas.csv")

        print(f"\nSUCESSO! ZIP criado: {OUTPUT_ZIP}")

    except Exception as e:
        print(f"\nERRO FATAL: {e}")