import pandas as pd
import requests
import os
import zipfile
import re
from io import StringIO

INPUT_FILE = "../1_etl_ans/output/consolidado_despesas.csv"
CADOP_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_planos_de_saude_ativas/Relatorio_Cadop.csv"
OUTPUT_DIR = "output"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "despesas_agregadas.csv")
OUTPUT_ZIP = os.path.join(OUTPUT_DIR, "Teste_JoaoGabriel.zip")

os.makedirs(OUTPUT_DIR, exist_ok=True)

def validar_cnpj(cnpj):
    '''Algoritmo Modulo 11'''
    cnpj = re.sub(r'\D', '', str(cnpj))

    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    #Primeiro Digito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[1]) * pesos1[i] for i in range(12))
    digito1 = 11 - (soma1 % 11)
    digito1 = 0 if digito1 >= 10 else digito1

    if digito1 != int(cnpj[12]):
        return False

    #Segundo Digito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    digito2 = 11 - (soma2 % 11)
    digito2 = 0 if digito2 >= 10 else digito2

    return digito2 == int(cnpj[13])

def baixar_cadop():
    '''
    Baixa Cadastro de Operadoras Ativas da ANS
    Pega CNPJ e Razao Social
    '''
    print("Baixando Cadastro de Operadoras (CADOP)")
    try:
        response = requests.get(CADOP_URL, timeout=60)
        response.raise_for_status()


        df = pd.read_csv(StringIO(response.text), sep=';', encoding='latin-1', dtype=str)

        df.columns = [c.strip().upper().replace('RAZAO_SOCIAL', 'RazaoSocial') for c in df.columns]

        col_map = {
            'REGISTRO_ANS': 'RegistroANS',
            'CNPJ': 'CNPJ',
            'RAZAO_SOCIAL': 'RazaoSocial',
            'MODALIDADE': 'Modalidade',
            'UF': 'UF'
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Retorna apenas as colunas úteis
        cols_uteis = ['RegistroANS', 'CNPJ', 'RazaoSocial', 'Modalidade', 'UF']
        return df[[c for c in cols_uteis if c in df.columns]]

    except Exception as e:
        print(f"Erro ao baixar CADOP: {e}")
        return None

def enriquecer_dados(df_despesas, df_cadop):
    print("Cruzando dados (Join)...")

    df_despesas['RegistroANS'] = df_despesas['RegistroANS'].astype(str).str.strip()
    df_cadop['RegistroANS'] = df_cadop['RegistroANS'].astype(str).str.strip()

    df_final = df_despesas.merge(df_cadop, on='RegistroANS', how='left', suffixes=('_orig', ''))

    df_final['CNPJ'] = df_final['CNPJ'].fillna('N/A')
    df_final['RazaoSocial'] = df_final['RazaoSocial'].fillna(f"Operadora {df_final['RegistroANS']} Desconhecida")
    df_final['UF'] = df_final['UF'].fillna('N/A')

    return df_final

def processar_agregacao(df):
    print("Calculando estatisticas (Soma, Média, Desvio Padrão)...")

    df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce').fillna(0)

    agregado = df.groupby(['RazaoSocial', 'UF'])['ValorDespesas'].agg(
        ValorTotal='sum',  # Soma total
        MediaTrimestral='mean',  # Média
        DesvioPadrao='std',  # Desvio padrão
        QtdRegistros='count'
    ).reset_index()

    agregado['DesvioPadrao'] = agregado['DesvioPadrao'].fillna(0)

    agregado = agregado.sort_values(by='ValorTotal', ascending=False)

    return agregado

if __name__ == "__main__":
    try:
        print("Lendo arquivos da tarefa 1:")
        if not os.path.exists(INPUT_FILE):
            raise FileNotFoundError(f"Arquivo não encontrado: {INPUT_FILE}. Rode a tarefa 1 primeiro!")

        df_raw = pd.read_csv(INPUT_FILE, sep=";", dtype=str)

        df_raw = df_raw.drop(columns=['CNPJ', 'RazaoSocial'], errors='ignore')

        df_cadop = baixar_cadop()

        if df_cadop is not None:
            df_enriched = enriquecer_dados(df_raw, df_cadop)
        else:
            raise Exception("Falha crítica: Não foi possível obter dados do CADOP.")

        print("Validando CNPJs...")
        df_enriched['CNPJ_Valido'] = df_enriched['CNPJ'].apply(validar_cnpj)

        cnpjs_invalidos = df_enriched[~df_enriched['CNPJ_Valido']]

        if not cnpjs_invalidos.empty:
            qtd = len(cnpjs_invalidos)
            print(f"ALERTA: {qtd} registros possuem CNPJs inválidos ou desconhecidos")

        df_final = processar_agregacao(df_enriched)

        print(f"Salvando {OUTPUT_CSV}...")
        df_final.to_csv(OUTPUT_CSV, index=False, sep=';', encoding='utf-8', float_format='%.2f')

        with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(OUTPUT_CSV, arcname="despesas_agregadas.csv")

        print(f"SUCESSO! Arquivo pronto: {OUTPUT_ZIP}")

    except Exception as e:
        print(f"\n ERRO FATAL: {e}")