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

    # Identificação flexível das colunas pelo cabeçalho
    col_status_valido = buscar_coluna(df, ['tempo de impacto', 'validação', 'validacao'], 3)
    col_produto       = buscar_coluna(df, ['produto', 'descrição', 'descricao'], 4)
    col_motivo        = buscar_coluna(df, ['motivo da reclamação', 'motivo'], 5)
    col_status_g      = buscar_coluna(df, ['status'], 6)
    col_sku           = buscar_coluna(df, ['sku'], 12)
    col_transportadora= buscar_coluna(df, ['transportadora', 'transp'], 13)

    # Tratamento de texto para comparações insensíveis a maiúsculas/espaços
    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    status_g_clean = df[col_status_g].astype(str).str.strip().str.upper()

    # 1. Filtro de Válido
    is_valido = valido_clean.str.contains('VÁLIDO|VALIDO', regex=True, na=False)

    # 2. Status que afetam a reputação: "Em Mediação", "Revisão Recusada", "Não Solicitada"
    status_afetam = ['EM MEDIAÇÃO', 'EM MEDIACAO', 'REVISÃO RECUSADA', 'REVISAO RECUSADA', 'NÃO SOLICITADA', 'NAO SOLICITADA']
    is_status_afetando = status_g_clean.isin(status_afetam)

    # Contabilidade dos Indicadores
    total_afetando = int((is_valido & is_status_afetando).sum())
    total_validos = int(is_valido.sum())
    total_registros = len(df)

    # Indicadores por agrupamento
    status_g_counts = df[col_status_g].value_counts().to_dict()
    motivo_counts = df[col_motivo].value_counts().to_dict()
    transportadora_counts = df[col_transportadora].value_counts().to_dict()

    # Top SKUs e Produtos
    sku_produto_df = df.groupby([col_sku, col_produto]).size().reset_index(name='quantidade')
    top_skus = sku_produto_df.sort_values(by='quantidade', ascending=False).head(20).to_dict(orient='records')

    dados_impactos_ml = {
        "resumo_validacao": {
            "total_pedidos_afetando": total_afetando,
            "total_pedidos_validos": total_validos,
            "total_registros": total_registros
        },
        "status_coluna_g": status_g_counts,
        "motivos_reclamacao": motivo_counts,
        "transportadoras": transportadora_counts,
        "skus_produtos_impactados": top_skus
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print(f"Processamento concluído! Afetando: {total_afetando} | Válidos: {total_validos}")

if __name__ == "__main__":
    processar_impactos_ml()
