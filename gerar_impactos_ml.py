import pandas as pd
import json

# URL CSV da planilha publicadamente exportada
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRH_71QAinoH_JzNzSswCNjswyM6EoMMSSFwbAlm-BPEeNXX5Xm1PKBbqaPQkVysQ/pub?gid=1773072804&single=true&output=csv"

def processar_impactos_ml():
    # Carrega o CSV pulando a 1ª linha (data indicativa) e usando a 2ª linha como cabeçalho
    df = pd.read_csv(URL_CSV, skiprows=1)
    
    # Limpa nomes das colunas removendo espaços extras nas pontas
    df.columns = [col.strip() for col in df.columns]

    # Mapeamento pelas letras das colunas (Índices base zero)
    col_status_valido = df.columns[3]   # Coluna D (Status Validação)
    col_produto       = df.columns[4]   # Coluna E (Produto)
    col_motivo        = df.columns[5]   # Coluna F (Motivo da Reclamação)
    col_status_g      = df.columns[6]   # Coluna G (Status descritos na Col G)
    col_sku           = df.columns[12]  # Coluna M (SKU)
    col_transportadora= df.columns[13]  # Coluna N (Transportadora)

    # 1. Indicador de Pedidos Válidos (Verifica com e sem acento: "VÁLIDO" ou "VALIDO")
    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    total_validos = int((valido_clean.isin(['VÁLIDO', 'VALIDO'])).sum())
    total_registros = len(df)

    # 2. Indicadores de Status (Coluna G)
    status_g_counts = df[col_status_g].value_counts().to_dict()

    # 3. Indicadores por Motivo da Reclamação (Coluna F)
    motivo_counts = df[col_motivo].value_counts().to_dict()

    # 4. Indicadores por Transportadora (Coluna N)
    transportadora_counts = df[col_transportadora].value_counts().to_dict()

    # 5. Top SKUs e Produtos mais afetados (Colunas M e E)
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
        
    print("Processamento concluído com sucesso!")

if __name__ == "__main__":
    processar_impactos_ml()
