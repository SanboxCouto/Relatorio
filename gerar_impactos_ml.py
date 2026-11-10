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

    col_data_pedido    = get_col(['DATA DO PEDIDO', 'DATA'], 0)
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
        data_ped = str(row[col_data_pedido]).strip() if col_data_pedido and pd.notna(row[col_data_pedido]) else ''

        registros.append({
            "sku": str(row[col_sku]).strip() if pd.notna(row[col_sku]) else 'N/A',
            "produto": prod_nome,
            "marca": extrair_marca(prod_nome),
            "motivo": str(row[col_motivo]),
            "transportadora": str(row[col_transportadora]),
            "status": str(row[col_status_g]),
            "tempo_impacto": str(row[col_status_valido]),
            "data_pedido": data_ped,
            "comentario": coment,
            "is_valido": is_valido,
            "is_afetando": is_afetando
        })
    return registros

def processar_amazon():
    df = parse_csv_dinamico(URL_CSV_AMAZON, ['ID DO PEDIDO', 'PRODUTO DA REIVINDICACAO', 'TEMPO DE IMPACTO'])

    def get_col(nome_exato):
        for col in df.columns:
            if remover_acentos(col) == remover_acentos(nome_exato):
                return col
        for col in df.columns:
            if remover_acentos(nome_exato) in remover_acentos(col):
                return col
        return None

    col_data_pedido  = get_col('Data do pedido')
    col_data_reiv    = get_col('Data da Reivindicação')
    col_tempo_imp    = get_col('Tempo de Impacto')
    col_id_pedido    = get_col('ID do pedido')
    col_motivo       = get_col('Motivo')
    col_comentario   = get_col('Comentário')
    col_data_solic   = get_col('Data da Solicitação')
    col_impacto      = get_col('Impacto')
    col_valor        = get_col('Valor')
    col_reembolso    = get_col('Reembolso')
    col_transp       = get_col('Transportadora')
    col_sku          = get_col('SKU')
    col_produto      = get_col('Produto da Reivindicação')

    registros = []
    for idx, row in df.iterrows():
        id_ped = str(row[col_id_pedido]).strip() if col_id_pedido and pd.notna(row[col_id_pedido]) else ''
        
        if not id_ped or id_ped.lower() == 'nan' or 'id do pedido' in id_ped.lower():
            continue

        tempo_val = str(row[col_tempo_imp]).strip() if col_tempo_imp and pd.notna(row[col_tempo_imp]) else ''
        impacto_val = str(row[col_impacto]).strip() if col_impacto and pd.notna(row[col_impacto]) else ''

        tempo_clean = remover_acentos(tempo_val)
        impacto_clean = remover_acentos(impacto_val)

        is_valido = 'VALIDO' in tempo_clean
        is_afetando = is_valido and any(st in impacto_clean for st in ['MANTIDO', 'CHAMADO PREMIUM', 'ANALISE'])

        sku_val = str(row[col_sku]).strip() if col_sku and pd.notna(row[col_sku]) and str(row[col_sku]).strip().lower() != 'nan' else 'N/A'
        
        prod_val = ''
        if col_produto and pd.notna(row[col_produto]):
            prod_val = str(row[col_produto]).strip()
        if not prod_val or prod_val.lower() == 'nan':
            prod_val = f"SKU {sku_val}"

        coment_val = str(row[col_comentario]) if col_comentario and pd.notna(row[col_comentario]) else ''
        data_solic_val = str(row[col_data_solic]).strip() if col_data_solic and pd.notna(row[col_data_solic]) else ''

        registros.append({
            "id_pedido": id_ped,
            "data_pedido": str(row[col_data_pedido]).strip() if col_data_pedido and pd.notna(row[col_data_pedido]) else '',
            "data_reivindicacao": str(row[col_data_reiv]).strip() if col_data_reiv and pd.notna(row[col_data_reiv]) else '',
            "data_solicitacao": data_solic_val,
            "valor": str(row[col_valor]).strip() if col_valor and pd.notna(row[col_valor]) else '',
            "reembolso": str(row[col_reembolso]).strip() if col_reembolso and pd.notna(row[col_reembolso]) else '',
            "impacto": impacto_val,
            "motivo": str(row[col_motivo]).strip() if col_motivo and pd.notna(row[col_motivo]) else '',
            "produto": prod_val,
            "sku": sku_val,
            "transportadora": str(row[col_transp]).strip() if col_transp and pd.notna(row[col_transp]) else '',
            "tempo_impacto": tempo_val,
            "marca": extrair_marca(prod_val if prod_val != f"SKU {sku_val}" else sku_val),
            "comentario": limpar_comentario(coment_val),
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
