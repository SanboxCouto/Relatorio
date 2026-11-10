import pandas as pd
import json
import re

URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"

# Lista de marcas conhecidas para identificação no texto do produto
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
    # Se não encontrar na lista, tenta pegar a segunda palavra (ex: Fogão Mueller -> Mueller)
    partes = str(nome_produto).split()
    if len(partes) > 1:
        return partes[1].capitalize()
    return "Outras"

def buscar_coluna(df, nomes_possiveis, indice_fallback):
    for col in df.columns:
        for nome in nomes_possiveis:
            if nome.lower() in str(col).lower():
                return col
    return df.columns[indice_fallback]

def processar_impactos_ml():
    df = pd.read_csv(URL_CSV, skiprows=1)
    df.columns = [str(col).strip() for col in df.columns]

    # Mapeamento de Colunas
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
        marca = extrair_marca(prod_nome)

        coment = str(row[col_comentario]).strip() if pd.notna(row[col_comentario]) else ''
        if coment.lower() == 'nan':
            coment = ''

        registros.append({
            "sku": str(row[col_sku]),
            "produto": prod_nome,
            "marca": marca,
            "motivo": str(row[col_motivo]),
            "transportadora": str(row[col_transportadora]),
            "status": str(row[col_status_g]),
            "tempo_impacto": str(row[col_status_valido]),
            "comentario": coment,
            "is_valido": is_valido,
            "is_afetando": is_afetando
        })

    dados_impactos_ml = {
        "registros": registros
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print(f"Processamento concluído com {len(registros)} registros!")

if __name__ == "__main__":
    processar_impactos_ml()
