import pandas as pd
import json

# URL CSV da planilha publicadamente exportada
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"

def buscar_coluna(df, nomes_possiveis, indice_fallback):
    """Procura uma coluna pelo nome aproximado/exato ou usa o índice como fallback."""
    for col in df.columns:
        for nome in nomes_possiveis:
            if nome.lower() in str(col).lower():
                return col
    return df.columns[indice_fallback]

def processar_impactos_ml():
    # Carrega o CSV pulando a 1ª linha (data indicativa) e usando a 2ª linha como cabeçalho
    df = pd.read_csv(URL_CSV, skiprows=1)
    
    # Limpa nomes das colunas removendo espaços extras nas pontas
    df.columns = [str(col).strip() for col in df.columns]

    # Identifica as colunas dinamicamente pelos nomes exatos do cabeçalho da planilha
    col_status_valido = buscar_coluna(df, ['tempo de impacto', 'validação', 'validacao', 'status validação'], 3)
    col_produto       = buscar_coluna(df, ['produto', 'descrição', 'descricao'], 4)
    col_motivo        = buscar_coluna(df, ['motivo', 'motivo da reclamação', 'reclamacao'], 5)
    col_status_g      = buscar_coluna(df, ['status'], 6)
    col_sku           = buscar_coluna(df, ['sku'], 12)
    col_transportadora= buscar_coluna(df, ['transportadora', 'transp'], 13)

    # 1. Indicador de Pedidos Válidos (Busca por qualquer variação de "Válido")
    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    total_validos = int((valido_clean.str.contains('VÁLIDO|VALIDO', regex=True, na=False)).sum())
    total_registros = len(df)

    # 2. Indicadores de Status
    status_g_counts = df[col_status_g].value_counts().to_dict()

    # 3. Indicadores por Motivo da Reclamação
    motivo_counts = df[col_motivo].value_counts().to_dict()

    # 4. Indicadores por Transportadora
    transportadora_counts = df[col_transportadora].value_counts().to_dict()

    # 5. Top SKUs e Produtos mais afetados
    sku_produto_df = df.groupby([col_sku, col_produto]).size().reset_index(name='quantidade')
    top_skus = sku_produto_df.sort_values(by='quantidade', ascending=False).to_dict(orient='records')

    # Estruturação do JSON final
    dados_impactos_ml = {
        "resumo_validacao": {
            "total_pedidos_validos": total_validos,
            "total_registros": total_registros
        },
        "status_coluna_g": status_g_counts,
        "motivos_reclamacao": motivo_counts,
        "transportadoras": transportadora_counts,
        "skus_produtos_impactados": top_skus
    }

    # Salva o arquivo JSON compilado
    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print(f"Processamento concluído! Pedidos válidos encontrados: {total_validos}")

if __name__ == "__main__":
    processar_impactos_ml()
