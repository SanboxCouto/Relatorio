import pandas as pd
import json
import re

# URLs das Planilhas Publicadas
URL_CSV_ML = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"
URL_CSV_AMAZON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=134048884&single=true&output=csv"

MARCAS_CONHECIDAS = [
    'MUELLER', 'DAKO', 'ELECTROLUX', 'IMBERA', 'PHILCO', 'ESMALTEC', 
    'ITATIAIA', 'ATLAS', 'WANKE', 'MIDEA', 'PULSE', 'CONSUL', 'BRASTEMP', 
    'SUGGAR', 'VENAX', 'MONDIAL', 'ARNO', 'BRITANIA', 'OSTER'
]

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
        col_str = str(col).lower().strip()
        for nome in nomes_possiveis:
            if nome.lower() in col_str:
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
        valido_clean = str(row[col_status_valido]).strip().upper()
        status_g_clean = str(row[col_status_g]).strip().upper()

        is_valido = bool(re.search(r'VÁLIDO|VALIDO', valido_clean))
        status_afetam = ['EM MEDIAÇÃO', 'EM MEDIACAO', 'REVISÃO RECUSADA', 'REVISAO RECUSADA', 'NÃO SOLICITADA', 'NAO SOLICITADA']
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
    df = pd.read_csv(URL_CSV_AMAZON, skiprows=1)
    df.columns = [str(col).strip() for col in df.columns]

    # Busca específica do ID do Pedido (Evita pegar Data do Pedido na Coluna A)
    col_id_pedido    = buscar_coluna(df, ['id do pedido', 'id_pedido'], 3)
    col_data         = buscar_coluna(df, ['data da reivindicação', 'data da reivindicacao'], 1)
    col_valor        = buscar_coluna(df, ['valor'], 8)
    col_reembolso    = buscar_coluna(df, ['reembolso'], 7)
    col_impacto      = buscar_coluna(df, ['impacto'], 5)
    col_motivo       = buscar_coluna(df, ['motivo'], 6)
    col_produto      = buscar_coluna(df, ['produto da reivindicação', 'produto da reivindicacao', 'produto'], 9)
    col_tempo_imp    = buscar_coluna(df, ['tempo de impacto', 'validação', 'validacao'], 2)
    col_sku          = buscar_coluna(df, ['sku'], 10)
    col_transp       = buscar_coluna(df, ['transportadora', 'transp'], 11)
    col_comentario   = buscar_coluna(df, ['comentário', 'comentario', 'obs', 'observação'], 12)

    registros = []
    for idx, row in df.iterrows():
        tempo_clean = str(row[col_tempo_imp]).strip().upper()
        impacto_clean = str(row[col_impacto]).strip().upper()

        is_valido = bool(re.search(r'VÁLIDO|VALIDO', tempo_clean))
        status_afetam_amz = ['MANTIDO', 'EM CHAMADO PREMIUM', 'EM ANÁLISE', 'EM ANALISE']
        is_afetando = is_valido and (impacto_clean in status_afetam_amz)

        prod_nome = str(row[col_produto])
        coment = str(row[col_comentario]).strip() if pd.notna(row[col_comentario]) else ''
        if coment.lower() == 'nan': coment = ''

        registros.append({
            "id_pedido": str(row[col_id_pedido]).strip(),
            "data_reivindicacao": str(row[col_data]).strip(),
            "valor": str(row[col_valor]).strip(),
            "reembolso": str(row[col_reembolso]).strip(),
            "impacto": str(row[col_impacto]).strip(),
            "motivo": str(row[col_motivo]).strip(),
            "produto": prod_nome,
            "sku": str(row[col_sku]).strip(),
            "transportadora": str(row[col_transp]).strip(),
            "tempo_impacto": str(row[col_tempo_imp]).strip(),
            "marca": extrair_marca(prod_nome),
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
        
    print(f"Processamento concluído! ML: {len(registros_ml)} | Amazon: {len(registros_amazon)}")

if __name__ == "__main__":
    main()
