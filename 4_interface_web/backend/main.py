from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import re

# Carrega variáveis
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Configuração Banco
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "intuitive_care_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Intuitive Care API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def limpar_cnpj(cnpj: str):
    return re.sub(r'\D', '', cnpj)


class OperadoraSimples(BaseModel):
    registro_ans: int
    cnpj: Optional[str]
    razao_social: Optional[str]
    uf: Optional[str]

class PaginacaoOperadoras(BaseModel):
    data: List[OperadoraSimples]
    total: int
    page: int
    limit: int

class DespesaHistorico(BaseModel):
    ano: int
    trimestre: int
    data_referencia: str
    valor_despesa: float

class TopItem(BaseModel):
    nome: str
    total: float

class Estatisticas(BaseModel):
    total_despesas: float
    media_por_operadora: float
    top_5_operadoras: List[TopItem] # Requisito 4.2
    top_estados: List[TopItem]      # Requisito 4.3 (para o gráfico)

@app.get("/api/operadoras", response_model=PaginacaoOperadoras)
def listar_operadoras(page: int = 1, limit: int = 10, search: Optional[str] = None, db: Session = Depends(get_db)):
    offset = (page - 1) * limit
    sql_base = "SELECT registro_ans, cnpj, razao_social, uf FROM operadoras"
    sql_count = "SELECT count(*) FROM operadoras"
    params = {}

    if search:
        filtro = " WHERE razao_social ILIKE :search OR cnpj ILIKE :search"
        sql_base += filtro
        sql_count += filtro
        params["search"] = f"%{search}%"

    sql_base += " ORDER BY registro_ans LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset

    total = db.execute(text(sql_count), params).scalar()
    result = db.execute(text(sql_base), params).fetchall()

    operadoras = [{"registro_ans": r.registro_ans, "cnpj": r.cnpj, "razao_social": r.razao_social, "uf": r.uf} for r in result]
    return {"data": operadoras, "total": total, "page": page, "limit": limit}

@app.get("/api/operadoras/{cnpj}")
def detalhes_operadora(cnpj: str, db: Session = Depends(get_db)):
    cnpj_limpo = limpar_cnpj(cnpj)
    sql = "SELECT * FROM operadoras WHERE REGEXP_REPLACE(cnpj, '\D','','g') = :cnpj"
    op = db.execute(text(sql), {"cnpj": cnpj_limpo}).fetchone()

    if not op:
        raise HTTPException(status_code=404, detail="Operadora não encontrada")

    return {"registro_ans": op.registro_ans, "cnpj": op.cnpj, "razao_social": op.razao_social, "uf": op.uf, "modalidade": op.modalidade}

@app.get("/api/operadoras/{cnpj}/despesas", response_model=List[DespesaHistorico])
def historico_despesas(cnpj: str, db: Session = Depends(get_db)):
    cnpj_limpo = limpar_cnpj(cnpj)
    sql = """
        SELECT d.ano, d.trimestre, d.data_referencia, d.valor_despesa 
        FROM despesas_contabeis d
        JOIN operadoras o ON d.registro_ans = o.registro_ans
        WHERE REGEXP_REPLACE(o.cnpj, '\D','','g') = :cnpj
        ORDER BY d.data_referencia DESC
    """
    rows = db.execute(text(sql), {"cnpj": cnpj_limpo}).fetchall()
    return [{"ano": r.ano, "trimestre": r.trimestre, "data_referencia": str(r.data_referencia), "valor_despesa": r.valor_despesa} for r in rows]

@app.get("/api/estatisticas", response_model=Estatisticas)
def obter_estatisticas(db: Session = Depends(get_db)):
    # 1. Totais Gerais
    total = db.execute(text("SELECT SUM(valor_despesa) FROM despesas_contabeis")).scalar() or 0
    media = db.execute(text("SELECT AVG(total) FROM (SELECT SUM(valor_despesa) as total FROM despesas_contabeis GROUP BY registro_ans) sub")).scalar() or 0

    # 2. Top 5 Operadoras (Requisito 4.2)
    top_ops_raw = db.execute(text("""
        SELECT o.razao_social, SUM(d.valor_despesa) as total
        FROM despesas_contabeis d JOIN operadoras o ON d.registro_ans = o.registro_ans
        GROUP BY o.registro_ans, o.razao_social ORDER BY total DESC LIMIT 5
    """)).fetchall()

    # 3. Top Estados (Requisito 4.3 - Gráfico)
    top_uf_raw = db.execute(text("""
        SELECT o.uf, SUM(d.valor_despesa) as total 
        FROM despesas_contabeis d JOIN operadoras o ON d.registro_ans = o.registro_ans
        WHERE o.uf IS NOT NULL GROUP BY o.uf ORDER BY total DESC LIMIT 10
    """)).fetchall()

    return {
        "total_despesas": total,
        "media_por_operadora": media,
        "top_5_operadoras": [{"nome": r.razao_social, "total": r.total} for r in top_ops_raw],
        "top_estados": [{"nome": r.uf, "total": r.total} for r in top_uf_raw]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)