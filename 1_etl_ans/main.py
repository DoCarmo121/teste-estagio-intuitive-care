import requests
from bs4 import BeautifulSoup
import os
import zipfile
import pandas as pd
import re
from urllib.parse import urljoin
import shutil
import traceback

BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/"
OUTPUT_DIR = "downloads"
FINAL_CSV = "output/consolidado_despesas.csv"
FINAL_ZIP = "output/consolidado_despesas.zip"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("output", exist_ok=True)


def get_soup(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"Error ao acessar {url}: {e}")
        return None


def listar_links(url):
    soup = get_soup(url)
    if not soup:
        return []

    links = []
    for a in soup.find_all('a'):
        href = a.get('href')
        if href and href != '../' and not href.startswith('?'):
            links.append(href)
    return links


def encontrar_ultimos_trimestres(qtd=3):
    print("Mapeando trimestres disponiveis...")
    link_raiz = listar_links(BASE_URL)
    pasta_raiz = next((l for l in link_raiz if "demonstracoes_contabeis" in l.lower()), None)
    if not pasta_raiz:
        raise Exception("Pasta 'Demonstrações Contábeis' não encontrada.")

    url_base_demo = urljoin(BASE_URL, pasta_raiz)

    todos_trimestres = []
    links_anos = listar_links(url_base_demo)

    for link_ano in links_anos:
        match_ano = re.search(r'(\d{4})', link_ano)
        if match_ano:
            ano = int(match_ano.group(1))
            url_ano = urljoin(url_base_demo, link_ano)

            links_tri = listar_links(url_ano)
            for link_tri in links_tri:
                match_tri = re.search(r'(\d)T', link_tri, re.IGNORECASE)
                if match_tri:
                    tri = int(match_tri.group(1))
                    todos_trimestres.append({
                        'ano': ano,
                        'trimestre': tri,
                        'url': urljoin(url_ano, link_tri),
                    })

    todos_trimestres.sort(key=lambda x: (x['ano'], x['trimestre']), reverse=True)
    selecionados = todos_trimestres[:qtd]

    print("Trimestres selecionados:")
    for t in selecionados:
        print(f" -> {t['ano']} / {t['trimestre']}º Trimestre")

    return selecionados


def baixar_e_extrair(trimestres):
    pasta_com_dados = []

    print("Iniciando downloads...")
    for item in trimestres:
        urls_para_baixar = []

        if item['url'].lower().endswith('.zip'):
            urls_para_baixar.append(item['url'])
        else:
            links = listar_links(item['url'])
            for l in links:
                if l.lower().endswith('.zip'):
                    urls_para_baixar.append(urljoin(item['url'], l))

        if not urls_para_baixar:
            print(f"Sem ZIP em {item['ano']}/T{item['trimestre']}. Pulando.")
            continue

        for url_zip in urls_para_baixar:
            zip_name = os.path.basename(url_zip)
            pasta_destino = os.path.join(OUTPUT_DIR, f"{item['ano']}_T{item['trimestre']}")
            caminho_zip = os.path.join(OUTPUT_DIR, "temp.zip")

            os.makedirs(pasta_destino, exist_ok=True)

            # Download
            print(f"Baixando {zip_name}...")
            try:
                with requests.get(url_zip, stream=True) as response:
                    response.raise_for_status()
                    with open(caminho_zip, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                print(" Extraindo...")
                with zipfile.ZipFile(caminho_zip, 'r') as zf:
                    zf.extractall(pasta_destino)

                pasta_com_dados.append({
                    'caminho': pasta_destino,
                    'ano': item['ano'],
                    'trimestre': item['trimestre']
                })

            except Exception as e:
                print(f"Erro no Download/extracao de {zip_name}: {e}")

            finally:
                if os.path.exists(caminho_zip):
                    os.remove(caminho_zip)

    return pasta_com_dados

def normalizar_colunas(df):
    df.columns = [
        c.strip().upper()
        .replace('Ç', 'C')
        .replace('Ã', 'A')
        .replace('Õ', 'O')
        .replace(' ', '_').replace('.', '')
        for c in df.columns
    ]
    return df


def ler_arquivo_flexivel(caminho):
    try:
        if caminho.endswith('xlsx'):
            return pd.read_excel(caminho, dtype=str)
        else:
            try:
                return pd.read_csv(caminho, sep=";", encoding='latin-1', dtype=str)
            except:
                return pd.read_csv(caminho, sep=',', encoding='utf-8', dtype=str)

    except Exception as e:
        print(f"Erro lendo o arquivo: {e}")
        return None


def processar_consolidar(pastas):
    dfs = []
    print("\n Processando arquivos...")

    for item in pastas:
        for root, _, files in os.walk(item['caminho']):
            for file in files:
                if not (file.lower().endswith('.csv') or file.lower().endswith('.xlsx')):
                    continue
                if 'receita' in file.lower() or 'ativo' in file.lower():
                    continue

                caminho_completo = os.path.join(root, file)
                df = ler_arquivo_flexivel(caminho_completo)

                if df is None: continue
                df = normalizar_colunas(df)

                col_map = {
                    'VL_SALDO_FINAL': 'ValorDespesas',
                    'VALOR': 'ValorDespesas',
                    'CD_CONTA_CONTABIL': 'Conta',
                    'REG_ANS': 'RegistroANS',
                    'DESCRIÇÃO': 'Descricao',
                    'DESCRICAO': 'Descricao'
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

                if 'ValorDespesas' not in df.columns:
                    continue

                # Filtra apenas contas de DESPESA (Começam com 4) se a coluna Conta existir
                if 'Conta' in df.columns:
                    df = df[df['Conta'].astype(str).str.startswith('4')]

                # Normaliza Valor
                df['ValorDespesas'] = (
                    df['ValorDespesas']
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)  # CORRECAO 2: Troca virgula por ponto
                )

                #Preencher nulos com 0
                df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce').fillna(0)

                df['Ano'] = item['ano']
                df['Trimestre'] = item['trimestre']

                # Colunas finais
                if 'CNPJ' not in df.columns: df['CNPJ'] = 'N/A'

                # Ajuste para garantir RazaoSocial
                if 'RAZAO_SOCIAL' in df.columns:
                    df = df.rename(columns={'RAZAO_SOCIAL': 'RazaoSocial'})
                elif 'RAZAO' in df.columns:
                    df = df.rename(columns={'RAZAO': 'RazaoSocial'})

                if 'RazaoSocial' not in df.columns:
                    df['RazaoSocial'] = 'N/A'

                cols_finais = ['CNPJ', 'RazaoSocial', 'Ano', 'Trimestre', 'ValorDespesas']
                cols_existentes = [c for c in cols_finais if c in df.columns]

                dfs.append(df[cols_existentes])

    if not dfs:
        raise Exception("Nenhum dado encontrado nos arquivos baixados.")

    return pd.concat(dfs, ignore_index=True)


if __name__ == '__main__':
    try:
        # Identificacao
        trimestres = encontrar_ultimos_trimestres()
        # Baixar e Extrair
        pastas = baixar_e_extrair(trimestres)
        # Consolidar
        df_final = processar_consolidar(pastas)

        print("\nSalvando resultados...")

        cols_obrigatorias = ['CNPJ', 'RazaoSocial', 'Trimestre', 'Ano', 'ValorDespesas']
        for c in cols_obrigatorias:
            if c not in df_final.columns:
                df_final[c] = "N/A"

        print("Padronizando Razões Sociais por CNPJ...")

        df_final.sort_values(by=['Ano', 'Trimestre'], ascending=True, inplace=True)

        mapa_nomes = df_final.groupby('CNPJ')['RazaoSocial'].last().to_dict()

        df_final['RazaoSocial'] = df_final['CNPJ'].map(mapa_nomes)

        # filtra valores negativos e zerados
        df_final = df_final[df_final['ValorDespesas'] > 0]

        # Salva o CSV
        df_final[cols_obrigatorias].to_csv(FINAL_CSV, index=False, sep=';', encoding='utf-8')
        print(f" -> CSV criado: {FINAL_CSV}")

        # Salva o ZIP (CORRECAO 4: Usar FINAL_ZIP, nao FINAL_CSV)
        with zipfile.ZipFile(FINAL_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(FINAL_CSV, arcname="consolidado_despesas.csv")
        print(f" -> ZIP final criado: {FINAL_ZIP}")

        shutil.rmtree(OUTPUT_DIR)
        print("Arquivos temporarios limpos.")

        print("TAREFA 1 CONCLUIDA COM SUCESSO!")

    except Exception as e:
        print(f"\nErro Fatal no Processo:\n{e}")
        traceback.print_exc()