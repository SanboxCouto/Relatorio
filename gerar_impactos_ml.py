import pandas as pd
import json

URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"

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

    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    status_g_clean = df[col_status_g].astype(str).str.strip().str.upper()

    # Filtro base: Válidos
    is_valido = valido_clean.str.contains('VÁLIDO|VALIDO', regex=True, na=False)
    df_valido = df[is_valido].copy()

    status_afetam = ['EM MEDIAÇÃO', 'EM MEDIACAO', 'REVISÃO RECUSADA', 'REVISAO RECUSADA', 'NÃO SOLICITADA', 'NAO SOLICITADA']
    df_valido['is_afetando'] = status_g_clean[is_valido].isin(status_afetam)

    df_valido[col_comentario] = df_valido[col_comentario].fillna('').astype(str).str.strip()

    # Constrói o banco de dados detalhado registro por registro
    registros = []
    for idx, row in df_valido.iterrows():
        registros.append({
            "sku": str(row[col_sku]),
            "produto": str(row[col_produto]),
            "motivo": str(row[col_motivo]),
            "transportadora": str(row[col_transportadora]),
            "status": str(row[col_status_g]),
            "comentario": str(row[col_comentario]) if str(row[col_comentario]).lower() != 'nan' else '',
            "is_afetando": bool(row['is_afetando'])
        })

    dados_impactos_ml = {
        "registros": registros
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print(f"Processamento concluído com {len(registros)} registros!")

if __name__ == "__main__":
    processar_impactos_ml()
