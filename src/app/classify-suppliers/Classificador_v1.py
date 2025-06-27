# Filtro + Classificador integrados — versão 2025-06-27
# ----------------------------------------------------
# 1. PARÂMETROS via linha de comando
import argparse

parser = argparse.ArgumentParser(description="Classificador de fornecedores")
parser.add_argument("--input-dir", required=True, dest="input_dir",
                    help="Diretório com os arquivos XML ou ZIP")
parser.add_argument("--empresa", required=True, dest="empresa",
                    help="Código da empresa")
parser.add_argument("--data-ini", required=True, dest="data_ini",
                    help="Data inicial (YYYY-MM-DD)")
parser.add_argument("--data-fim", required=True, dest="data_fim",
                    help="Data final (YYYY-MM-DD)")
args = parser.parse_args()

input_dir_path = args.input_dir
output_root    = args.input_dir + "_CLASSIFICADOS"

# 2. PARÂMETROS GERAIS DO CLASSIFICADOR  (inalterados)
import os, re, shutil, zipfile, tempfile, logging, xml.etree.ElementTree as ET, pathlib, pandas as pd
from pathlib import Path
from datetime import datetime
import pyodbc
from bs4 import BeautifulSoup

EMPRESA    = int(args.empresa)
DATA_INI   = args.data_ini
DATA_FIM   = args.data_fim
DSN, UID, PWD = "Contabil_BI", "BI", "4431610"

MAX_PATH = 250   # limite seguro para caminho completo
TRUNC    = 20    # chars quando truncar segmento

# 3. LOG
Path(output_root).mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s",
                    handlers=[logging.StreamHandler()])

# 4. TAMPA PARA OS XML QUE PRECISAM SER CLASSIFICADOS
tmp_classif_dir = Path(tempfile.mkdtemp(prefix="xml_para_classif_"))

# ------------------------- 5.  F I L T R O  CFOP  ------------------------- #
# (código original mantido – apenas 3 linhas adaptadas, marcadas com ###)

# === MAPEAMENTO CFOP → GRUPO ===
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

# ———— Não edite nada abaixo nesta seção ———— #
TODOS_CFOPS = set(cfop for lista in GROUP_CFOP.values() for cfop in lista)

def extrair_cfops(xml_path: pathlib.Path):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    try:
        soup = BeautifulSoup(xml_path.read_text(encoding='utf-8', errors='ignore'), 'xml')
        return [tag.text.strip() for tag in soup.find_all('CFOP')]
    except Exception as e:
        logging.warning("Falha lendo %s: %s", xml_path.name, e)
        return []

def classificar_cfops(set_cfops):
    # Regra 1 — qualquer CFOP fora da lista → passar para classificador
    if any(cfop not in TODOS_CFOPS for cfop in set_cfops):
        return 'PASSAR PARA CLASSIFICADOR', 'Regra 1'
    # Quais grupos surgem?
    grupos_presentes = {g for g,l in GROUP_CFOP.items() if set_cfops.intersection(l)}
    # Regra 3 — só existe 1 CFOP
    if len(set_cfops) == 1:
        return next(iter(grupos_presentes)) if grupos_presentes else 'OUTRAS', 'Regra 3'
    # Regra 2-b — todos CFOPs dentro de um único grupo
    if len(grupos_presentes) == 1:
        g = next(iter(grupos_presentes))
        return g if g != 'OUTRAS' else 'OUTRAS', 'Regra 2-b'
    # Regra 2 — mais de um grupo
    return 'OUTRAS', 'Regra 2'

def processar_zip(zip_path: pathlib.Path, log):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmpdir)
        for xml_file in pathlib.Path(tmpdir).rglob('*.xml'):
            cfops = extrair_cfops(xml_file)
            destino, regra = classificar_cfops(set(cfops))
            if destino == 'PASSAR PARA CLASSIFICADOR':                ### (A)
                shutil.copy2(xml_file, tmp_classif_dir / xml_file.name)### (B)
            else:
                destino_path = Path(output_root, destino)
                destino_path.mkdir(parents=True, exist_ok=True)
                shutil.copy2(xml_file, destino_path / xml_file.name)
            log.append({
                'arquivo': xml_file.name,
                'cfops_distintos': sorted(set(cfops)),
                'destino': destino,
                'regra': regra,
                'zip_origem': zip_path.name
            })

def filtro_cfop():
    inicio = datetime.now()
    input_dir = Path(input_dir_path)
    log = []
    zips = list(input_dir.glob('*.zip'))
    for zp in zips:
        processar_zip(zp, log)

    xmls = list(input_dir.glob('*.xml'))
    for xml_file in xmls:
        cfops = extrair_cfops(xml_file)
        destino, regra = classificar_cfops(set(cfops))
        if destino == 'PASSAR PARA CLASSIFICADOR':
            shutil.copy2(xml_file, tmp_classif_dir / xml_file.name)
        else:
            destino_path = Path(output_root, destino)
            destino_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(xml_file, destino_path / xml_file.name)
        log.append({
            'arquivo': xml_file.name,
            'cfops_distintos': sorted(set(cfops)),
            'destino': destino,
            'regra': regra,
            'zip_origem': xml_file.name
        })

    if not zips and not xmls:
        raise FileNotFoundError(f'Nenhum .zip ou .xml encontrado em {input_dir}')

    df = pd.DataFrame(log)
    dur = datetime.now() - inicio
    logging.info("Filtro: %d XMLs processados em %s.", len(df), dur)
    return df

# -------------------- 6.  C L A S S I F I C A D O R  --------------------- #
def clean_name(txt: str, limit: int = 80) -> str:
    trans = str.maketrans(
        "ÁÀÂÃÄáàâãäÉÈÊËéèêëÍÌÎÏíìîïÓÒÔÕÖóòôõöÚÙÛÜúùûüÇç",
        "AAAAAaaaaaEEEEeeeeIIIIiiiiOOOOOoooooUUUUuuuuCc"
    )
    txt = (txt or "").translate(trans)
    txt = re.sub(r"[^A-Za-z0-9 _\-.]", "", txt)
    txt = re.sub(r"\s+", " ", txt).strip().rstrip(" .")
    return txt[:limit]

def trunc(txt: str, n: int = TRUNC) -> str:
    return clean_name(txt)[:n]

def extrair_emitente(xml_path: Path):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    try:
        root = ET.parse(xml_path).getroot()
        emit = root.find(".//nfe:emit", ns)
        cnpj = re.sub(r"\D", "", emit.find("nfe:CNPJ", ns).text).zfill(14)
        nome = clean_name(emit.find("nfe:xNome", ns).text)
        return cnpj, nome
    except Exception as e:
        logging.warning("Falha XML %s: %s", xml_path.name, e)
        return None, None

# ========== 4. CONSULTAS SQL (corrigidas) ==========
def consulta_periodo(emp, ini, fim):
    conn = pyodbc.connect(f"DSN={DSN};UID={UID};PWD={PWD}")
    sql = """
        SELECT DISTINCT
               acu.CODI_ACU,
               acu.NOME_ACU,
               forn.CODI_FOR AS CODIGO_FORNECEDOR,
               forn.NOME_FOR AS NOME_FORNECEDOR,
               forn.CGCE_FOR
        FROM bethadba.EFENTRADAS nf
        JOIN bethadba.EFACUMULADOR acu
             ON acu.CODI_EMP = nf.CODI_EMP
            AND acu.CODI_ACU = nf.CODI_ACU
        JOIN bethadba.EFACUMULADOR_VIGENCIA vig
             ON vig.CODI_EMP = nf.CODI_EMP
            AND vig.CODI_ACU = nf.CODI_ACU
            AND vig.LANCAR_SOMENTE_ENTRADA = 'S'
            AND vig.IDEV_ACU = 'N'
        JOIN bethadba.EFFORNECE forn
             ON forn.CODI_EMP = nf.CODI_EMP
            AND forn.CODI_FOR = nf.CODI_FOR
        WHERE nf.CODI_EMP = ?
          AND nf.DDOC_ENT BETWEEN DATE(?) AND DATE(?)
          AND nf.CODI_ESP = 36;
    """
    df = pd.read_sql(sql, conn, params=(emp, ini, fim))
    conn.close()
    df["CGCE_FOR"] = (
        df["CGCE_FOR"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(14)
    )
    return df


def consulta_fornecedores(emp):
    conn = pyodbc.connect(f"DSN={DSN};UID={UID};PWD={PWD}")
    sql = """
        SELECT CODI_FOR,
               NOME_FOR,
               CGCE_FOR
        FROM bethadba.EFFORNECE
        WHERE CODI_EMP = ?;
    """
    df = pd.read_sql(sql, conn, params=(emp,))
    conn.close()
    df["CGCE_FOR"] = (
        df["CGCE_FOR"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(14)
    )
    return df

class Classificador:
    def __init__(self, base, out, df_per, df_full):
        self.base, self.out = base, out
        self.temp = Path(tempfile.mkdtemp(prefix="xmlclas_"))
        self.map_per = self._build_map(df_per)
        self.map_full = {r.CGCE_FOR: (str(r.CODI_FOR), clean_name(r.NOME_FOR)) for _,r in df_full.iterrows()}
        self.multi=[]

    def _build_map(self, df):
        out={}
        for _,r in df.iterrows():
            cnpj=r.CGCE_FOR.zfill(14)
            out.setdefault(cnpj,[]).append(dict(
                acu=str(r.CODI_ACU), nacu=clean_name(r.NOME_ACU),
                cod=str(r.CODIGO_FORNECEDOR), nfor=clean_name(r.NOME_FORNECEDOR)))
        return out

    # --- helpers --- #
    def _copy_in(self):
        for p in self.base.rglob("*"):
            if p.suffix.lower()==".zip":
                with zipfile.ZipFile(p) as z: z.extractall(self.temp)
            elif p.suffix.lower()==".xml":
                shutil.copy2(p, self.temp)
        self.xmls=list({p.resolve() for p in self.temp.rglob("*.xml")})
        logging.info("Classificador: XMLs prontos: %d", len(self.xmls))

    def _ensure_dir(self, path: Path):
        fixed=Path(*[seg.rstrip(" .") for seg in path.parts])
        fixed.mkdir(parents=True, exist_ok=True)
        return fixed

    def _safe_dst(self, dst: Path):
        return dst if len(str(dst))<MAX_PATH else dst.parent.parent/trunc(dst.parent.name)/dst.name

    def _move(self, src: Path, dst: Path):
        dst=self._safe_dst(dst)
        dst=self._ensure_dir(dst.parent)/dst.name
        try: shutil.move(src, dst)
        except FileNotFoundError:
            shutil.copy2(src, dst); src.unlink(missing_ok=True)

    # --- núcleo --- #
    def run(self):
        self._copy_in()
        dirF,dirM,dirS=[self.out/p for p in ("Fornecedores","MultiGrupo","SemGrupo")]
        for d in (dirF,dirM,dirS): d.mkdir(parents=True, exist_ok=True)
        sem={}
        for xml in self.xmls:
            cnpj, nome=extrair_emitente(xml)
            if not cnpj: continue
            recs=self.map_per.get(cnpj,[])
            if not recs:
                self._move(xml, dirS/cnpj/xml.name)
                sem.setdefault(cnpj, nome)
                continue
            grupos={(r['acu'],r['nacu']) for r in recs}
            cod,nfor=recs[0]['cod'], recs[0]['nfor']
            if len(grupos)==1:
                acu,nacu=grupos.pop()
                self._move(xml, dirF/f"{acu}_{nacu}"/f"{cod}_{nfor}"/xml.name)
            else:
                self._move(xml, dirM/f"{cod}_{nfor}"/xml.name)
                self.multi.append(dict(
                    CNPJ=cnpj,
                    Fornecedor=f"{cod}_{nfor}",
                    Acumuladores=", ".join(sorted({r['acu'] for r in recs}))
                ))
        # Renomeia SemGrupo
        for cnpj,nome_xml in sem.items():
            old=dirS/cnpj
            if not old.exists(): continue
            cod,nome_full=self.map_full.get(cnpj,("0000",nome_xml))
            new_base=f"{cod}_{nome_full}"
            new=dirS/clean_name(new_base)
            i=1
            while new.exists():
                new=dirS/f"{clean_name(new_base)}_{i}"; i+=1
            try: old.rename(new)
            except Exception as e: logging.warning("Rename falhou %s -> %s: %s", old.name, new.name, e)
        # Planilha MultiGrupo
        if self.multi:
            pd.DataFrame(self.multi).drop_duplicates().to_excel(
                self.out/"MultiGrupo_Summary.xlsx", index=False, engine="openpyxl")
        shutil.rmtree(self.temp, ignore_errors=True)
        logging.info("Classificador: Processo finalizado")

# -------------------------- 7.  R U N  --------------------------- #
if __name__ == "__main__":
    # 1º passo: Filtro
    df_log = filtro_cfop()

    # 2º passo: Classificador (somente se houver XMLs para isso)
    if any(df_log['destino'] == 'PASSAR PARA CLASSIFICADOR'):
        logging.info("Enviando %d XML(s) para o Classificador…",
                     (df_log['destino'] == 'PASSAR PARA CLASSIFICADOR').sum())
        BASE_DIR  = tmp_classif_dir            # sobrepõe o caminho de entrada
        OUTPUT_DIR = Path(output_root)         # saída é a mesma do filtro
        df_periodo = consulta_periodo(EMPRESA, DATA_INI, DATA_FIM)
        df_fullfor = consulta_fornecedores(EMPRESA)
        Classificador(Path(BASE_DIR), OUTPUT_DIR, df_periodo, df_fullfor).run()
    else:
        logging.info("Nenhum XML precisava de classificação adicional.")

    # Limpeza do diretório temporário
    shutil.rmtree(tmp_classif_dir, ignore_errors=True)
    print("\n✅ Processo completo. Resultados em:", output_root)




