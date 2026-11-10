import pandas as pd
import json
import re
import unicodedata
import io
import requests

URL_CSV_ML = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"
URL_CSV_AMAZON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=134048884&single=true&output=csv"

MARCAS_CONHECIDAS = [
    'MUELLER', 'DAKO', 'ELECTROLUX', 'IMBERA', 'PHILCO', 'ESMALTEC', 
    'ITATIAIA', 'ATLAS', 'WANKE', 'MIDEA', 'PULSE', 'CONSUL', 'BRASTEMP', 
    'SUGGAR', 'VENAX', 'MONDIAL', 'ARNO', 'BRITANIA', 'OSTER'
]

def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().strip()

def extrair_marca(nome_produto):
    texto = str(nome_produto).upper()
    for marca in MARCAS_CONHECIDAS:
        if marca in texto:
            return marca.capitalize()
    partes = str(nome_produto).split()
    if len(partes) > 1:
        return partes[1].capitalize()
    return "Outras"

def limpar_comentario(texto):
    if pd.isna(texto):
        return ""
    coment = str(texto).strip()
    coment_norm = remover_acentos(coment)
    
    # Filtra textos vazios, 'nan' ou marcadores de 'sem comentário'
    if coment_norm in ['', 'NAN', 'SEM COMENTARIO', 'SEM COMENTARIOS', 'SEM OBSERVACOES', 'SEM OBSERVACAO', 'N/A', '-']:
        return ""
    return coment

def parse_csv_dinamico(url, termos_busca):
    res = requests.get(url)
    res.encoding = 'utf-8'
    lines = res.text.splitlines()
    
    header_idx = -1
    for idx, line in enumerate(lines[:15]):
        line_norm = remover_acentos(line)
        if any(remover_acentos(t) in line_norm for t in termos_busca):
            header_idx = idx
            break
            
    if header_idx != -1:
        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
    else:
        df = pd.read_csv(io.StringIO(res.text))
        
    df.columns = [str(col).replace('"', '').replace("'", "").strip() for col in df.columns]
    return df

def processar_ml():
    df = parse_csv_dinamico(URL_CSV_ML, ['TEMPO DE IMPACTO', 'MOTIVO DA RECLAMACAO', 'STATUS'])

    def get_col(nomes, default_idx):
        for col in df.columns:
            if any(n in remover_acentos(col) for n in nomes):
                return col
        return df.columns[default_idx] if len(df.columns) > default_idx else df.columns[0]

    col_status_valido = get_col(['TEMPO DE IMPACTO', 'VALIDACAO'], 3)
    col_produto       = get_col(['PRODUTO'], 4)
    col_motivo        = get_col(['MOTIVO DA RECLAMACAO', 'MOTIVO'], 5)
    col_status_g      = get_col(['STATUS'], 6)
    col_sku           = get_col(['SKU'], 12)
    col_transportadora= get_col(['TRANSPORTADORA', 'TRANSP'], 13)
    col_comentario    = get_col(['COMENTARIO', 'OBSERVACAO', 'OBS'], 14)

    registros = []
    for idx, row in df.iterrows():
        valido_clean = remover_acentos(str(row[col_status_valido]))
        status_g_clean = remover_acentos(str(row[col_status_g]))

        is_valido = 'VALIDO' in valido_clean
        status_afetam = ['EM MEDIACAO', 'REVISAO RECUSADA', 'NAO SOLICITADA']
        is_afetando = is_valido and (status_g_clean in status_afetam)

        prod_nome = str(row[col_produto]) if pd.notna(row[col_produto]) else ''
        coment = limpar_comentario(row[col_comentario])

        registros.append({
            "sku": str(row[col_sku]).strip() if pd.notna(row[col_sku]) else 'N/A',
            "produto": prod_nome,
            "marca": extrair_marca(prod_nome),
            "motivo": str(row[col_motivo]),
            "transportadora": str(row[col_transportadora]),
            "status": str(row[col_status_g]),
            "tempo_impacto": str(row[col_status_valido]),
            "comentario": coment,
            "is_valido": is_valido,
            "is_afetando": is_afetando
        })
    return registros

def processar_amazon():
    df = parse_csv_dinamico(URL_CSV_AMAZON, ['ID DO PEDIDO', 'TEMPO DE IMPACTO', 'PRODUTO DA REIVINDICACAO'])

    def get_col(nomes, default_idx):
        for col in df.columns:
            col_norm = remover_acentos(col)
            if any(remover_acentos(n) in col_norm for n in nomes):
                return col
        return df.columns[default_idx] if len(df.columns) > default_idx else df.columns[0]

    col_data_pedido  = get_col(['DATA DO PEDIDO'], 0)
    col_data_reiv    = get_col(['DATA DA REIVINDICACAO', 'DATA REIVINDICACAO'], 1)
    col_tempo_imp    = get_col(['TEMPO DE IMPACTO'], 2)
    col_id_pedido    = get_col(['ID DO PEDIDO'], 3)
    col_motivo       = get_col(['MOTIVO'], 4)
    col_comentario   = get_col(['COMENTARIO', 'OBS'], 5)
    col_impacto      = get_col(['IMPACTO'], 6)
    col_valor        = get_col(['VALOR'], 7)
    col_reembolso    = get_col(['REEMBOLSO'], 8)
    col_transp       = get_col(['TRANSPORTADORA'], 9)
    col_produto      = get_col(['PRODUTO DA REIVINDICACAO', 'PRODUTO REIVINDICACAO', 'PRODUTO'], 10)
    col_sku          = get_col(['SKU'], 11)

    registros = []
    for idx, row in df.iterrows():
        id_ped = str(row[col_id_pedido]).strip()
        
        if not id_ped or id_ped.lower() == 'nan' or 'id do pedido' in id_ped.lower():
            continue

        tempo_clean = remover_acentos(str(row[col_tempo_imp]))
        impacto_clean = remover_acentos(str(row[col_impacto]))

        is_valido = 'VALIDO' in tempo_clean
        is_afetando = is_valido and any(st in impacto_clean for st in ['MANTIDO', 'CHAMADO PREMIUM', 'ANALISE'])

        sku_val = str(row[col_sku]).strip() if pd.notna(row[col_sku]) and str(row[col_sku]).strip().lower() != 'nan' else 'N/A'
        prod_val = str(row[col_produto]).strip() if pd.notna(row[col_produto]) and str(row[col_produto]).strip().lower() != 'nan' else f"SKU {sku_val}"
        
        coment = limpar_comentario(row[col_comentario])

        registros.append({
            "id_pedido": id_ped,
            "data_pedido": str(row[col_data_pedido]).strip(),
            "data_reivindicacao": str(row[col_data_reiv]).strip(),
            "valor": str(row[col_valor]).strip(),
            "reembolso": str(row[col_reembolso]).strip(),
            "impacto": str(row[col_impacto]).strip(),
            "motivo": str(row[col_motivo]).strip(),
            "produto": prod_val,
            "sku": sku_val,
            "transportadora": str(row[col_transp]).strip(),
            "tempo_impacto": str(row[col_tempo_imp]).strip(),
            "marca": extrair_marca(prod_val if prod_val != f"SKU {sku_val}" else sku_val),
            "comentario": coment,
            "is_valido": is_valido,
            "is_afetando": is_afetando
        })
    return registros

def main():
    registros_ml = processar_ml()
    registros_amazon = processar_amazon()

    dados = {
        "ml": registros_ml,
        "amazon": registros_amazon
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)
        
    print(f"Sucesso! ML: {len(registros_ml)} | Amazon: {len(registros_amazon)}")

if __name__ == "__main__":
    main()
