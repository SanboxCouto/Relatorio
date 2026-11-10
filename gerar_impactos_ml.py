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

    # Mapeamento Dinâmico de Colunas
    col_status_valido = buscar_coluna(df, ['tempo de impacto', 'validação', 'validacao'], 3)
    col_produto       = buscar_coluna(df, ['produto', 'descrição', 'descricao'], 4)
    col_motivo        = buscar_coluna(df, ['motivo da reclamação', 'motivo'], 5)
    col_status_g      = buscar_coluna(df, ['status'], 6)
    col_sku           = buscar_coluna(df, ['sku'], 12)
    col_transportadora= buscar_coluna(df, ['transportadora', 'transp'], 13)
    col_comentario    = buscar_coluna(df, ['comentário', 'comentario', 'observação', 'obs'], 14)

    # Tratamento de textos
    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    status_g_clean = df[col_status_g].astype(str).str.strip().str.upper()

    # Filtro base: apenas pedidos Válidos
    is_valido = valido_clean.str.contains('VÁLIDO|VALIDO', regex=True, na=False)

    # 1. Pedidos Afetando a Reputação (Válidos e Status: "Em Mediação", "Revisão Recusada", "Não Solicitada")
    status_afetam = ['EM MEDIAÇÃO', 'EM MEDIACAO', 'REVISÃO RECUSADA', 'REVISAO RECUSADA', 'NÃO SOLICITADA', 'NAO SOLICITADA']
    is_status_afetando = status_g_clean.isin(status_afetam)
    total_afetando = int((is_valido & is_status_afetando).sum())

    # 2. Total com "Revisão Recusada" (Que estejam Válidos)
    status_recusada = ['REVISÃO RECUSADA', 'REVISAO RECUSADA']
    total_revisao_recusada = int((is_valido & status_g_clean.isin(status_recusada)).sum())

    # 3. Total com "Impacto Removido" (Que estejam Válidos)
    status_removido = ['IMPACTO REMOVIDO', 'REMOVIDO']
    total_impacto_removido = int((is_valido & status_g_clean.isin(status_removido)).sum())

    # Agrupamento com extração de comentários (Coluna O)
    df_valido = df[is_valido].copy()
    df_valido[col_comentario] = df_valido[col_comentario].fillna('').astype(str).str.strip()

    # Comentários por Motivo
    motivos_detalhados = []
    for motivo, group in df_valido.groupby(col_motivo):
        comentarios = [c for c in group[col_comentario].tolist() if c and c.lower() != 'nan']
        motivos_detalhados.append({
            "motivo": str(motivo),
            "quantidade": len(group),
            "comentarios": comentarios
        })
    motivos_detalhados.sort(key=lambda x: x['quantidade'], reverse=True)

    # Comentários por Transportadora
    transportadoras_detalhadas = []
    for transp, group in df_valido.groupby(col_transportadora):
        comentarios = [c for c in group[col_comentario].tolist() if c and c.lower() != 'nan']
        transportadoras_detalhadas.append({
            "transportadora": str(transp),
            "quantidade": len(group),
            "comentarios": comentarios
        })
    transportadoras_detalhadas.sort(key=lambda x: x['quantidade'], reverse=True)

    # Top SKUs e Produtos mais afetados
    sku_produto_df = df_valido.groupby([col_sku, col_produto]).size().reset_index(name='quantidade')
    top_skus = sku_produto_df.sort_values(by='quantidade', ascending=False).to_dict(orient='records')

    dados_impactos_ml = {
        "indicadores_topo": {
            "total_pedidos_afetando": total_afetando,
            "total_revisao_recusada": total_revisao_recusada,
            "total_impacto_removido": total_impacto_removido
        },
        "motivos_detalhados": motivos_detalhados,
        "transportadoras_detalhadas": transportadoras_detalhadas,
        "skus_produtos_impactados": top_skus
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print(f"Processamento concluído! Afetando: {total_afetando} | Recusadas: {total_revisao_recusada} | Removidos: {total_impacto_removido}")

if __name__ == "__main__":
    processar_impactos_ml()
