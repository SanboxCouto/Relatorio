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

    # Tratamento de textos
    valido_clean = df[col_status_valido].astype(str).str.strip().str.upper()
    status_g_clean = df[col_status_g].astype(str).str.strip().str.upper()

    # Filtro base: apenas Válidos
    is_valido = valido_clean.str.contains('VÁLIDO|VALIDO', regex=True, na=False)

    # 1. Pedidos Afetando Reputação
    status_afetam = ['EM MEDIAÇÃO', 'EM MEDIACAO', 'REVISÃO RECUSADA', 'REVISAO RECUSADA', 'NÃO SOLICITADA', 'NAO SOLICITADA']
    total_afetando = int((is_valido & status_g_clean.isin(status_afetam)).sum())

    # 2. Em Mediação
    status_mediacao = ['EM MEDIAÇÃO', 'EM MEDIACAO']
    total_em_mediacao = int((is_valido & status_g_clean.isin(status_mediacao)).sum())

    # 3. Revisão Recusada
    status_recusada = ['REVISÃO RECUSADA', 'REVISAO RECUSADA']
    total_revisao_recusada = int((is_valido & status_g_clean.isin(status_recusada)).sum())

    # 4. Impacto Removido
    status_removido = ['IMPACTO REMOVIDO', 'REMOVIDO']
    total_impacto_removido = int((is_valido & status_g_clean.isin(status_removido)).sum())

    df_valido = df[is_valido].copy()
    df_valido[col_comentario] = df_valido[col_comentario].fillna('').astype(str).str.strip()

    # Comentários + Ranking de Transportadoras por Motivo
    motivos_detalhados = []
    for motivo, group in df_valido.groupby(col_motivo):
        comentarios = [c for c in group[col_comentario].tolist() if c and c.lower() != 'nan']
        ranking_transp = group[col_transportadora].value_counts().to_dict()
        motivos_detalhados.append({
            "motivo": str(motivo),
            "quantidade": len(group),
            "ranking_transportadoras": ranking_transp,
            "comentarios": comentarios
        })
    motivos_detalhados.sort(key=lambda x: x['quantidade'], reverse=True)

    # Comentários + Ranking de Motivos por Transportadora
    transportadoras_detalhadas = []
    for transp, group in df_valido.groupby(col_transportadora):
        comentarios = [c for c in group[col_comentario].tolist() if c and c.lower() != 'nan']
        ranking_mot = group[col_motivo].value_counts().to_dict()
        transportadoras_detalhadas.append({
            "transportadora": str(transp),
            "quantidade": len(group),
            "ranking_motivos": ranking_mot,
            "comentarios": comentarios
        })
    transportadoras_detalhadas.sort(key=lambda x: x['quantidade'], reverse=True)

    # SKUs e Produtos com Comentários
    skus_detalhados = []
    for (sku, prod), group in df_valido.groupby([col_sku, col_produto]):
        comentarios = [c for c in group[col_comentario].tolist() if c and c.lower() != 'nan']
        skus_detalhados.append({
            "sku": str(sku),
            "produto": str(prod),
            "quantidade": len(group),
            "comentarios": comentarios
        })
    skus_detalhados.sort(key=lambda x: x['quantidade'], reverse=True)

    dados_impactos_ml = {
        "indicadores_topo": {
            "total_pedidos_afetando": total_afetando,
            "total_em_mediacao": total_em_mediacao,
            "total_revisao_recusada": total_revisao_recusada,
            "total_impacto_removido": total_impacto_removido
        },
        "motivos_detalhados": motivos_detalhados,
        "transportadoras_detalhadas": transportadoras_detalhadas,
        "skus_produtos_impactados": skus_detalhados
    }

    with open("impactos_ml.json", "w", encoding="utf-8") as f:
        json.dump(dados_impactos_ml, f, ensure_ascii=False, indent=4)
        
    print("Processamento concluído com sucesso!")

if __name__ == "__main__":
    processar_impactos_ml()
