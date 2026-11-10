import pandas as pd
import json
import re
import unicodedata

# URLs das Planilhas Publicadas
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

def buscar_coluna(df, nomes_possiveis, indice_fallback=0):
    for col in df.columns:
        col_norm = remover_acentos(str(col))
        for nome in nomes_possiveis:
            if remover_acentos(nome) in col_norm:
                return col
    if len(df.columns) > indice_fallback:
        return df.columns[indice_fallback]
    return df.columns[0]

def processar_ml():
    df = pd.read_csv(URL_CSV_ML, skiprows=1)
    df.columns = [str(col).strip() for col in df.columns]

    col_status_valido = buscar_coluna(df, ['tempo de impacto', 'validação', 'validacao'], 3)
    col_produto       = buscar_coluna(df, ['produto', 'descrição', 'descricao'], 4)
    col_motivo        = buscar_coluna(df, ['motivo da reclamação', 'motivo'], 5)
    col_status_g      = buscar_coluna(df, ['status'], 6)
    col_sku           = buscar_coluna(df, ['sku'], 12)
    col_transportadora= buscar_coluna(df, ['transportadora', 'transp'], 13)
    col_comentario    = buscar_coluna(df, ['comentário', 'comentario', 'observação', 'obs'], 14)

    registros = []
    for idx, row in df.iterrows():
        valido_clean = remover_acentos(row[col_status_valido])
        status_g_clean = remover_acentos(row[col_status_g])

        is_valido = bool(re.search(r'VALIDO', valido_clean))
        status_afetam = ['EM MEDIACAO', 'REVISAO RECUSADA', 'NAO SOLICITADA']
        is_afetando = is_valido and (status_g_clean in status_afetam)

        prod_nome = str(row[col_produto])
        coment = str(row[col_comentario]).strip() if pd.notna(row[col_comentario]) else ''
        if coment.lower() == 'nan': coment = ''

        registros.append({
            "sku": str(row[col_sku]),
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
    # Pula a linha 1 (data de atualização) e lê a linha 2 como cabeçalho
    df = pd.read_csv(URL_CSV_AMAZON, skiprows=1)
    df.columns = [str(col).strip() for col in df.columns]

    # Mapeamento estrito baseado na ordem da imagem 69163f.png:
    # 0: Data do pedido, 1: Data da Reivindicação, 2: Tempo de Impacto, 3: ID do pedido, 
    # 4: Motivo, 5: Comentário, 6: Impacto, 7: Valor, 8: Reembolso, 9: Transportadora, 10: UF, 11: SKU
    col_data_pedido  = buscar_coluna(df, ['data do pedido'], 0)
    col_data_reiv    = buscar_coluna(df, ['data da reivindicacao', 'data da reivindicação'], 1)
    col_tempo_imp    = buscar_coluna(df, ['tempo de impacto'], 2)
    col_id_pedido    = buscar_coluna(df, ['id do pedido'], 3)
    col_motivo       = buscar_coluna(df, ['motivo'], 4)
    col_comentario   = buscar_coluna(df, ['comentario', 'comentário'], 5)
    col_impacto      = buscar_coluna(df, ['impacto'], 6)
    col_valor        = buscar_coluna(df, ['valor'], 7)
    col_reembolso    = buscar_coluna(df, ['reembolso'], 8)
    col_transp       = buscar_coluna(df, ['transportadora'], 9)
    col_sku          = buscar_coluna(df, ['sku'], 11)

    registros = []
    for idx, row in df.iterrows():
        id_ped = str(row[col_id_pedido]).strip()
        
        # Filtra linhas vazias ou de cabeçalho
        if not id_ped or id_ped.lower() == 'nan' or 'id do pedido' in id_ped.lower():
            continue

        tempo_clean = remover_acentos(row[col_tempo_imp])
        impacto_clean = remover_acentos(row[col_impacto])

        # Tempo de Impacto: VÁLIDO vs EXPIRADO
        is_valido = 'VALIDO' in tempo_clean
        
        # Pedidos Afetando Reputação: VÁLIDO + (MANTIDO OU CHAMADO PREMIUM OU ANALISE)
        is_afetando = is_valido and any(st in impacto_clean for st in ['MANTIDO', 'CHAMADO PREMIUM', 'ANALISE'])

        sku_val = str(row[col_sku]).strip() if pd.notna(row[col_sku]) else 'N/A'
        coment = str(row[col_comentario]).strip() if pd.notna(row[col_comentario]) else ''
        if coment.lower() == 'nan': coment = ''

        registros.append({
            "id_pedido": id_ped,
            "data_pedido": str(row[col_data_pedido]).strip(),
            "data_reivindicacao": str(row[col_data_reiv]).strip(),
            "valor": str(row[col_valor]).strip(),
            "reembolso": str(row[col_reembolso]).strip(),
            "impacto": str(row[col_impacto]).strip(),
            "motivo": str(row[col_motivo]).strip(),
            "produto": f"Produto SKU {sku_val}",
            "sku": sku_val,
            "transportadora": str(row[col_transp]).strip(),
            "tempo_impacto": str(row[col_tempo_imp]).strip(),
            "marca": extrair_marca(sku_val),
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
