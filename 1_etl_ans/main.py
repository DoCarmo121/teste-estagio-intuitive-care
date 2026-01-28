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
        print(f"Error  ao acessar {url}: {e}")
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