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

def limpar_identificador(valor):
    if pd.isna(valor):
        return ""
    val_str = str(valor).strip()
    if val_str.lower() in ['', 'nan', 'none', '-']:
        return ""
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    return val_str

def parse_csv_dinamico(url, termos_busca):
    res = requests.get(url)
    res.encoding = 'utf-8'
    lines = res.text.splitlines()
    
    header_idx = -1
    for idx, line in enumerate(lines[1:15], start=1):
        line_norm = remover_acentos(line)
        if any(remover_acentos(t) in line_norm for t in termos_busca):
            header_idx = idx
            break
            
    if header_idx != -1:
        df = pd.read_csv(io.StringIO("\n".join(lines[header_idx:])))
    else:
        df = pd.read_csv(io.StringIO("\n".join(lines[1:])))
        
    df.columns = [str(col).replace('"', '').replace("'", "").strip() for col in df.columns]
    return df

def encontrar_coluna_exata(df, nomes_possiveis):
    colunas_map = {remover_acentos(col): col for col in df.columns}
    # 1. Tenta correspondência exata
    for nome in nomes_possiveis:
        nome_norm = remover_acentos(nome)
        if nome_norm in colunas_map:
            return colunas_map[nome_norm]
    # 2. Tenta por inclusão parcial se não achar exato
    for nome in nomes_possiveis:
        nome_norm = remover_acentos(nome)
        for c_norm, c_orig in colunas_map.items():
            if nome_norm in c_norm:
                return c_orig
    return None

def processar_ml():
    df = parse_csv_dinamico(URL_CSV_ML, ['TEMPO DE IMPACTO', 'MOTIVO DA RECLAMACAO', 'ACAO TOMADA', 'PRODUTO'])

    col_pedido        = encontrar_coluna_exata(df, ['PEDIDO'])
    col_n_venda       = encontrar_coluna_exata(df, ['N° VENDA', 'Nº VENDA', 'NO VENDA', 'N° DA VENDA', 'Nº DA VENDA'])
    col_data_pedido   = encontrar_coluna_exata(df, ['DATA DA RECLAMACAO', 'DATA DA RECLAMAÇÃO', 'DATA', 'DATA DA VENDA', 'DATA DO PEDIDO'])
    col_status_valido = encontrar_coluna_exata(df, ['TEMPO DE IMPACTO', 'VALIDACAO'])
    col_produto       = encontrar_coluna_exata(df, ['PRODUTO', 'PRODUTO DA RECLAMACAO'])
    col_motivo        = encontrar_coluna_exata(df, ['MOTIVO DA RECLAMACAO', 'MOTIVO DA RECLAMAÇÃO', 'MOTIVO'])
    col_status_g      = encontrar_coluna_exata(df, ['ACAO TOMADA', 'AÇÃO TOMADA', 'STATUS', 'SITUACAO'])
    col_sku           = encontrar_coluna_exata(df, ['SKU', 'CODIGO SKU', 'ID DE RECLAMACAO'])
    col_transportadora= encontrar_coluna_exata(df, ['TRANSPORTADORA', 'TRANSP', 'LOGISTICA'])
    col_comentario    = encontrar_coluna_exata(df, ['COMENTARIO', 'COMENTÁRIO', 'OBSERVACAO', 'OBSERVAÇÃO', 'OBS'])

    registros = []
    for idx, row in df.iterrows():
        valido_val = str(row[col_status_valido]) if col_status_valido and pd.notna(row[col_status_valido]) else ''
        status_g_val = str(row[col_status_g]) if col_status_g and pd.notna(row[col_status_g]) else ''

        valido_clean = remover_acentos(valido_val)
        status_g_clean = remover_acentos(status_g_val)

        is_valido = 'VALIDO' in valido_clean
        status_afetam = ['EM MEDIACAO', 'REVISAO RECUSADA', 'NAO SOLICITADA']
        is_afetando = is_valido and (status_g_clean in status_afetam)

        pedido_val = limpar_identificador(row[col_pedido]) if col_pedido else ''
        n_venda_val = limpar_identificador(row[col_n_venda]) if col_n_venda else ''
        prod_nome = str(row[col_produto]).strip() if col_produto and pd.notna(row[col_produto]) else ''
        coment = limpar_comentario(row[col_comentario]) if col_comentario else ''
        data_ped = str(row[col_data_pedido]).strip() if col_data_pedido and pd.notna(row[col_data_pedido]) else ''

        registros.append({
            "pedido": pedido_val,
            "n_venda": n_venda_val,
            "sku": str(row[col_sku]).strip() if col_sku and pd.notna(row[col_sku]) else 'N/A',
            "produto": prod_nome,
            "marca": extrair_marca(prod_nome),
            "motivo": str(row[col_motivo]).strip() if col_motivo and pd.notna(row[col_motivo]) else '',
            "transportadora": str(row[col_transportadora]).strip() if col_transportadora and pd.notna(row[col_transportadora]) else '',
            "status": status_g_val,
            "tempo_impacto": valido_val,
            "data_pedido": data_ped,
            "comentario": coment,
            "is_valido": is_valido,
            "is_afetando": is_afetando
        })
    return registros

def processar_amazon():
    df = parse_csv_dinamico(URL_CSV_AMAZON, ['ID DO PEDIDO', 'PRODUTO DA REIVINDICACAO', 'TEMPO DE IMPACTO'])

    col_data_pedido  = encontrar_coluna_exata(df, ['DATA DO PEDIDO', 'DATA PEDIDO'])
    col_data_reiv    = encontrar_coluna_exata(df, ['DATA DA REIVINDICACAO', 'DATA DA REIVINDICAÇÃO'])
    col_tempo_imp    = encontrar_coluna_exata(df, ['TEMPO DE IMPACTO', 'VALIDACAO'])
    col_id_pedido    = encontrar_coluna_exata(df, ['ID DO PEDIDO', 'ID PEDIDO', 'Nº PEDIDO'])
    col_motivo       = encontrar_coluna_exata(df, ['MOTIVO'])
    col_comentario   = encontrar_coluna_exata(df, ['COMENTARIO', 'COMENTÁRIO', 'OBSERVACAO'])
    col_data_solic   = encontrar_coluna_exata(df, ['DATA DA SOLICITACAO', 'DATA DA SOLICITAÇÃO'])
    col_impacto      = encontrar_coluna_exata(df, ['IMPACTO'])
    col_valor        = encontrar_coluna_exata(df, ['VALOR', 'RESULTADO (VALOR)'])
    col_reembolso    = encontrar_coluna_exata(df, ['REEMBOLSO'])
    col_transp       = encontrar_coluna_exata(df, ['TRANSPORTADORA', 'TRANSP'])
    col_sku          = encontrar_coluna_exata(df, ['SKU'])
    col_produto      = encontrar_coluna_exata(df, ['PRODUTO DA REIVINDICACAO', 'PRODUTO DA REIVINDICAÇÃO', 'PRODUTO'])

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
