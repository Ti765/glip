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

DSN, UID, PWD = "Contabil_BI", "BI", "4431610"
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
    # ... (seu dicionário original de grupos) ...
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

def _clean_name(txt: str, limit: int=80) -> str:
    trans = str.maketrans(
        "ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇç",
        "AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCc"
    )
    s = (txt or "").translate(trans)
    s = re.sub(r"[^A-Za-z0-9 _\-.]", "", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(" .")
    return s[:limit]

def _trunc(txt: str, n: int=TRUNC) -> str:
    return _clean_name(txt)[:n]

def _extrair_emitente(xml_path: Path):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    try:
        root = ET.parse(xml_path).getroot()
        emit = root.find(".//nfe:emit", ns)
        cnpj = re.sub(r"\D", "", emit.find("nfe:CNPJ", ns).text).zfill(14)
        nome = _clean_name(emit.find("nfe:xNome", ns).text)
        return cnpj, nome
    except Exception as e:
        logging.warning("Falha XML %s: %s", xml_path.name, e)
        return None, None

def _consulta_periodo(emp: int, ini: str, fim: str):
    conn = pyodbc.connect(f"DSN={DSN};UID={UID};PWD={PWD}")
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
    conn = pyodbc.connect(f"DSN={DSN};UID={UID};PWD={PWD}")
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

    def _build_map(self, df: pd.DataFrame):
        m = {}
        for _, r in df.iterrows():
            c = r.CGCE_FOR.zfill(14)
            m.setdefault(c, []).append({
                "acu": str(r.CODI_ACU),
                "nacu": _clean_name(r.NOME_ACU),
                "cod": str(r.CODIGO_FORNECEDOR),
                "nfor": _clean_name(r.NOME_FORNECEDOR),
            })
        return m

    def _copy_in(self):
        for p in self.base.rglob("*"):
            if p.suffix.lower()==".zip":
                with zipfile.ZipFile(p) as zf:
                    zf.extractall(self.temp)
            elif p.suffix.lower()==".xml":
                shutil.copy2(p, self.temp)
        self.xmls = list({p.resolve() for p in self.temp.rglob("*.xml")})
        logging.info("Classificador: %d XML(s) carregados", len(self.xmls))

    def _ensure_dir(self, path: Path):
        d = Path(*[seg.rstrip(" .") for seg in path.parts])
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _safe_dst(self, dst: Path):
        if len(str(dst)) < MAX_PATH:
            return dst
        return dst.parent.parent / _trunc(dst.parent.name) / dst.name

    def _move(self, src: Path, dst: Path):
        dst = self._safe_dst(dst)
        dst = self._ensure_dir(dst.parent) / dst.name
        try:
            shutil.move(src, dst)
        except FileNotFoundError:
            shutil.copy2(src, dst)
            src.unlink(missing_ok=True)

    def run(self):
        self._copy_in()
        dirs = {k:self.out / k for k in ("Fornecedores","MultiGrupo","SemGrupo")}
        for d in dirs.values():
            d.mkdir(parents=True, exist_ok=True)

        sem = {}
        for xml in self.xmls:
            cnpj, nome = _extrair_emitente(xml)
            if not cnpj:
                continue
            recs = self.map_per.get(cnpj, [])
            if not recs:
                self._move(xml, dirs["SemGrupo"]/cnpj/xml.name)
                sem[cnpj] = nome
                continue

            grupos = {(r["acu"],r["nacu"]) for r in recs}
            cod, nfor = recs[0]["cod"], recs[0]["nfor"]
            if len(grupos)==1:
                acu,nacu = grupos.pop()
                self._move(xml, dirs["Fornecedores"]/f"{acu}_{nacu}"/f"{cod}_{nfor}"/xml.name)
            else:
                self._move(xml, dirs["MultiGrupo"]/f"{cod}_{nfor}"/xml.name)
                self.multi.append({
                    "CNPJ": cnpj,
                    "Fornecedor": f"{cod}_{nfor}",
                    "Acumuladores": ", ".join(sorted({r["acu"] for r in recs}))
                })

        # renomeia SemGrupo
        for cnpj,nome in sem.items():
            old = dirs["SemGrupo"]/cnpj
            if not old.exists(): continue
            cod,nome_full = self.map_full.get(cnpj,("0000",nome))
            new_base = _clean_name(f"{cod}_{nome_full}")
            new = dirs["SemGrupo"]/new_base
            i = 1
            while new.exists():
                new = dirs["SemGrupo"]/f"{new_base}_{i}"
                i+=1
            try: old.rename(new)
            except Exception as e:
                logging.warning("Falha renomear %s → %s: %s", old, new, e)

        # se multi, exporta planilha
        if self.multi:
            pd.DataFrame(self.multi).drop_duplicates().to_excel(
                self.out/"MultiGrupo_Summary.xlsx", index=False, engine="openpyxl"
            )

        shutil.rmtree(self.temp, ignore_errors=True)
        logging.info("Classificador: finalizado com sucesso")


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
