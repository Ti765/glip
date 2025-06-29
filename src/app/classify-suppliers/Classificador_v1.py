#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classificador de Fornecedores (parametrizado)
--------------------------------------------
Versão: 2025-06-27

Uso:
    python Classificador_v1.py \
        --input-dir "/caminho/para/ENTRADAS" \
        --empresa 605 \
        --data-ini 2025-03-01 \
        --data-fim 2025-05-31

Requisitos (requirements.txt):
    pandas
    pyodbc
    beautifulsoup4
    lxml
    openpyxl
"""

import argparse
import sys
import re
import shutil
import zipfile
import tempfile
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

import pandas as pd
import pyodbc
from bs4 import BeautifulSoup

# ============================= 1. ARGUMENTOS ============================= #

def _parse_date(date_str: str) -> str:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Data '{date_str}' inválida – use YYYY-MM-DD ou DD/MM/AAAA."
    )

def _get_args():
    p = argparse.ArgumentParser(
        description="Classificador de Fornecedores – parâmetros de execução"
    )
    p.add_argument("--input-dir",  required=True, help="Diretório de .xml ou .zip")
    p.add_argument("--empresa",    required=True, type=int, help="Código da empresa")
    p.add_argument("--data-ini",   required=True, type=_parse_date,
                   help="Data inicial (YYYY-MM-DD ou DD/MM/AAAA)")
    p.add_argument("--data-fim",   required=True, type=_parse_date,
                   help="Data final (YYYY-MM-DD ou DD/MM/AAAA)")
    return p.parse_args()

# ========================= 2. CONFIGURAÇÕES GERAIS ====================== #

args = _get_args()
input_dir = Path(args.input_dir).expanduser().resolve()
if not input_dir.exists():
    sys.exit(f"❌ Pasta de entrada inexistente: {input_dir}")

output_root = input_dir.parent / "ARQUIVOS CLASSIFICADOS"
output_root.mkdir(exist_ok=True, parents=True)

EMPRESA  = args.empresa
DATA_INI = args.data_ini
DATA_FIM = args.data_fim

# Conexão direta: caminho da biblioteca ODBC Driver 17 instalada pelo Nix
DRIVER_LIB = "/nix/store/9mklkwp6arkh39dprkdbp7x39i9a87rx-msodbcsql17-17.7.1.1-1/lib/libmsodbcsql-17.7.so.1.1"
UID, PWD = "BI", "4431610"

MAX_PATH = 250
TRUNC    = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

_tmp_dir = Path(tempfile.mkdtemp(prefix="xml_para_classif_"))

# =========================== 3. FILTRO CFOP ============================= #

GROUP_CFOP = {
    'COMBUSTÍVEIS E LUBRIFICANTES': ['5653', '5656', '6653', '6656', '7667'],
    'CONSERTOS': ['5915', '5916', '6915', '6916'],
    'DEMONSTRAÇÕES': ['5912', '5913', '6912', '6913'],
    'DEVOLUÇÕES': ['5201', '5202', '5208', '5209', '5210', '5410', '5411', '5412', '5413', '5553', '5555', '5556', '5918', '5919', '6201', '6202', '6208', '6209', '6210', '6410', '6411', '6412', '6413', '6553', '6555', '6556', '6918', '6919', '7201', '7202', '7210', '7211', '7212'],
    'ENERGIA ELÉTRICA': ['5153', '5207', '5251', '5252', '5253', '5254', '5255', '5256', '5257', '5258', '6153', '6207', '6251', '6252', '6253', '6254', '6255', '6256', '6257', '6258', '7207', '7251'],
    'SERVIÇOS': ['5205', '5301', '5302', '5303', '5304', '5305', '5306', '5307', '5932', '5933', '6205', '6301', '6302', '6303', '6304', '6305', '6306', '6307', '6932', '6933', '7205', '7301'],
    'TRANSPORTE': ['5206', '5351', '5352', '5353', '5354', '5355', '5356', '5357', '5359', '5360', '6206', '6351', '6352', '6353', '6354', '6355', '6356', '6357', '6359', '6360', '7206', '7358'],
    'TRANSFERÊNCIAS': ['5151', '5152', '5155', '5156', '5408', '5409', '5552', '5557', '6151', '6152', '6155', '6156', '6408', '6409', '6552', '6557'],
    'BONIFICAÇÕES E BRINDES': ['5910', '6910'],
    'REMESSAS': ['5920', '6920'],
    'OUTRAS': ['5601', '5602', '5605', '5929', '5949', '6929', '6949', '7949'],
}
_ALL_CFOPS = {cf for lst in GROUP_CFOP.values() for cf in lst}

def _extrair_cfops(xml_path: Path):
    try:
        soup = BeautifulSoup(xml_path.read_text(errors="ignore"), "xml")
        return [t.text.strip() for t in soup.find_all("CFOP")]
    except Exception as e:
        logging.warning("Falha lendo %s: %s", xml_path.name, e)
        return []

def _classificar_cfops(cfops: set[str]):
    if any(c not in _ALL_CFOPS for c in cfops):
        return "PASSAR PARA CLASSIFICADOR", "Regra 1"
    grupos = {g for g, lst in GROUP_CFOP.items() if cfops.intersection(lst)}
    if len(cfops) == 1:
        return (next(iter(grupos)) if grupos else "OUTRAS", "Regra 3")
    if len(grupos) == 1:
        g = next(iter(grupos))
        return (g, "Regra 2-b") if g != "OUTRAS" else ("OUTRAS", "Regra 2-b")
    return "OUTRAS", "Regra 2"

def _copiar(xml_file: Path, destino: str, regra: str, log: list[dict]):
    if destino == "PASSAR PARA CLASSIFICADOR":
        shutil.copy2(xml_file, _tmp_dir / xml_file.name)
    else:
        dst = output_root / destino
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(xml_file, dst / xml_file.name)
    log.append({"arquivo": xml_file.name, "destino": destino, "regra": regra})

def _processar_zip(z: Path, log: list[dict]):
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(z) as zf:
            zf.extractall(td)
        for xml in Path(td).rglob("*.xml"):
            cf = set(_extrair_cfops(xml))
            dest, reg = _classificar_cfops(cf)
            _copiar(xml, dest, reg, log)

def _processar_xml(x: Path, log: list[dict]):
    cf = set(_extrair_cfops(x))
    dest, reg = _classificar_cfops(cf)
    _copiar(x, dest, reg, log)

def filtro_cfop() -> pd.DataFrame:
    inicio = datetime.now()
    zips = list(input_dir.glob("*.zip"))
    xmls = list(input_dir.glob("*.xml"))
    if not zips and not xmls:
        raise FileNotFoundError(f"Nenhum .zip ou .xml em {input_dir}")
    log: list[dict] = []
    for z in zips:   _processar_zip(z, log)
    for x in xmls:   _processar_xml(x, log)
    df = pd.DataFrame(log)
    logging.info("Filtro: %d arquivos em %s", len(df), datetime.now() - inicio)
    if not df.empty:
        print("\n=== Resultados do Filtro CFOP ===")
        print(df.to_csv(index=False))
    return df

# =========================== 4. CLASSIFICADOR =========================== #

def _consulta_periodo(emp: int, ini: str, fim: str):
    # Conexão DSN-less com caminho de biblioteca
    conn = pyodbc.connect(
        f"DRIVER={{{DRIVER_LIB}}};"
        f"SERVER=SRVGO01,2638;"
        f"DATABASE=contabil;"
        f"UID={UID};"
        f"PWD={PWD};"
    )
    sql = """SELECT DISTINCT
                acu.CODI_ACU, acu.NOME_ACU,
                forn.CODI_FOR   AS CODIGO_FORNECEDOR,
                forn.NOME_FOR   AS NOME_FORNECEDOR,
                forn.CGCE_FOR
             FROM bethadba.EFENTRADAS nf
             JOIN bethadba.EFACUMULADOR acu ON acu.CODI_EMP = nf.CODI_EMP AND acu.CODI_ACU = nf.CODI_ACU
             JOIN bethadba.EFACUMULADOR_VIGENCIA vig
               ON vig.CODI_EMP = nf.CODI_EMP AND vig.CODI_ACU = nf.CODI_ACU
              AND vig.LANCAR_SOMENTE_ENTRADA = 'S' AND vig.IDEV_ACU = 'N'
             JOIN bethadba.EFFORNECE forn
               ON forn.CODI_EMP = nf.CODI_EMP AND forn.CODI_FOR = nf.CODI_FOR
             WHERE nf.CODI_EMP = ?
               AND nf.DDOC_ENT BETWEEN DATE(?) AND DATE(?)
               AND nf.CODI_ESP = 36;"""
    df = pd.read_sql(sql, conn, params=(emp, ini, fim))
    conn.close()
    df["CGCE_FOR"] = (
        df["CGCE_FOR"].astype(str)
            .str.replace(r"\D","", regex=True)
            .str.zfill(14)
    )
    return df

def _consulta_fornecedores(emp: int):
    # Conexão DSN-less com caminho de biblioteca
    conn = pyodbc.connect(
        f"DRIVER={{{DRIVER_LIB}}};"
        f"SERVER=SRVGO01,2638;"
        f"DATABASE=contabil;"
        f"UID={UID};"
        f"PWD={PWD};"
    )
    df = pd.read_sql(
        "SELECT CODI_FOR, NOME_FOR, CGCE_FOR FROM bethadba.EFFORNECE WHERE CODI_EMP = ?;",
        conn, params=(emp,)
    )
    conn.close()
    df["CGCE_FOR"] = (
        df["CGCE_FOR"].astype(str)
            .str.replace(r"\D","", regex=True)
            .str.zfill(14)
    )
    return df

class Classificador:
    # ... (restante da classe inalterado) ...
    def __init__(self, base: Path, out: Path,
                 df_periodo: pd.DataFrame,
                 df_full: pd.DataFrame):
        self.base = base
        self.out  = out
        self.temp = Path(tempfile.mkdtemp(prefix="xmlclas_"))
        self.map_per  = self._build_map(df_periodo)
        self.map_full = {
            r.CGCE_FOR: (str(r.CODI_FOR), _clean_name(r.NOME_FOR))
            for _, r in df_full.iterrows()
        }
        self.multi: list[dict] = []

    # ... todo o restante do código permanece igual ...

# =============================== 5. MAIN ================================ #

def main():
    logging.info("Iniciando Empresa %s de %s a %s", EMPRESA, DATA_INI, DATA_FIM)

    try:
        df = filtro_cfop()
    except FileNotFoundError as e:
        logging.error(e)
        sys.exit(1)

    if df.empty:
        logging.info("Nenhum XML após filtro — nada a classificar.")
        print(f"Finalizado. Saída em: {output_root}")
        return

    if (df["destino"]=="PASSAR PARA CLASSIFICADOR").any():
        logging.info("Enviando %d XML(s) para classificador…",
                     (df["destino"]=="PASSAR PARA CLASSIFICADOR").sum())
        df_p = _consulta_periodo(EMPRESA, DATA_INI, DATA_FIM)
        df_f = _consulta_fornecedores(EMPRESA)
        Classificador(_tmp_dir, output_root, df_p, df_f).run()
    else:
        logging.info("Nenhum XML para classificar adicionalmente.")

    shutil.rmtree(_tmp_dir, ignore_errors=True)
    print(f"\nProcesso completo. Resultados em: {output_root}")

if __name__ == "__main__":
    main()
