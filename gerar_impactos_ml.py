import io
import json
import re
import unicodedata
import pandas as pd
import requests

URL_CSV_ML = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWr2yKLLA3zpokmqfZAeHeqUCgK_rtKYX7Fceb0FBI0YqNqYWHOcVklVccOiVvQAYU39T6glLbgK7D/pub?gid=1773072804&single=true&output=csv"
URL_CSV_AMAZON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWr2yKLLA3zpokmqfZAeHeqUCgK_rtKYX7Fceb0FBI0YqNqYWHOcVklVccOiVvQAYU39T6glLbgK7D/pub?gid=134048884&single=true&output=csv"


def remover_acentos(texto):
  if not texto:
    return ""
  return (
      "".join(
          c
          for c in unicodedata.normalize("NFD", str(texto))
          if unicodedata.category(c) != "Mn"
      )
      .upper()
      .strip()
  )


def limpar_identificador(val):
  if pd.isna(val) or val is None:
    return ""
  s = str(val).strip()
  if s.upper() in ["NAN", "NONE", "NAT", "-"]:
    return ""
  if s.endswith(".0"):
    s = s[:-2]
  return s


def limpar_comentario(val):
  if pd.isna(val) or val is None:
    return ""
  s = str(val).strip()
  if s.upper() in ["NAN", "NONE", "NAT", "-"]:
    return ""
  return s


def extrair_marca(produto):
  if not produto:
    return "OUTROS"
  prod_up = remover_acentos(produto)
  marcas = [
      "WAP",
      "MONDIAL",
      "PHILCO",
      "BRITANIA",
      "OSTER",
      "CADENCE",
      "ELECTROLUX",
      "ARNO",
      "BLACK+DECKER",
      "BLACK & DECKER",
      "MIDEA",
      "CONSUL",
      "BRASTEMP",
      "LG",
      "SAMSUNG",
      "PHILIPS",
      "WALITA",
      "MALLORY",
      "VENTISOL",
      "LORENZETTI",
      "TRAMONTINA",
      "STANLEY",
      "DEWALT",
      "MAKITA",
      "BOSCH",
      "VONDER",
      "SCHULZ",
      "KARCHER",
      "JACTO",
      "INTEX",
      "MOR",
      "NAUTIKA",
      "COLEMAN",
      "MULTILASER",
      "MULTI",
      "INTELBRAS",
      "POSITIVO",
      "LENOVO",
      "DELL",
      "HP",
      "ACER",
      "ASUS",
      "JBL",
      "XIAOMI",
      "APPLE",
      "MOTOROLA",
  ]
  for m in marcas:
    if re.search(r"\b" + re.escape(m) + r"\b", prod_up):
      return m
  palavras = [p for p in prod_up.split() if len(p) > 2]
  return palavras[0] if palavras else "OUTROS"


def parse_csv_dinamico(url, palavras_chave_cabecalho):
  resp = requests.get(url, timeout=30)
  resp.encoding = "utf-8"
  linhas = resp.text.splitlines()

  header_idx = 0
  for i, linha in enumerate(linhas[:25]):
    linha_norm = remover_acentos(linha)
    matches = sum(1 for kw in palavras_chave_cabecalho if kw in linha_norm)
    if matches >= 2:
      header_idx = i
      break

  csv_ajustado = "\n".join(linhas[header_idx:])
  df = pd.read_csv(io.StringIO(csv_ajustado), dtype=str)
  df.columns = [str(c).strip() for c in df.columns]
  return df


def encontrar_coluna_exata(df, candidatos):
  cols_norm = {remover_acentos(c): c for c in df.columns}
  for cand in candidatos:
    cand_norm = remover_acentos(cand)
    if cand_norm in cols_norm:
      return cols_norm[cand_norm]
  for cand in candidatos:
    cand_norm = remover_acentos(cand)
    for k, orig in cols_norm.items():
      if cand_norm in k:
        return orig
  return None


def processar_ml():
  df = parse_csv_dinamico(
      URL_CSV_ML,
      ["TEMPO DE IMPACTO", "MOTIVO DA RECLAMACAO", "ACAO TOMADA", "PRODUTO"],
  )
  print("COLUNAS ML:", list(df.columns))

  col_pedido = encontrar_coluna_exata(
      df, ["PEDIDO", "ID PEDIDO", "NUM PEDIDO", "ID DO PEDIDO"]
  )
  col_n_venda = encontrar_coluna_exata(
      df,
      [
          "N° VENDA",
          "Nº VENDA",
          "NO VENDA",
          "N VENDA",
          "N° DA VENDA",
          "Nº DA VENDA",
          "VENDA",
      ],
  )
  col_data_pedido = encontrar_coluna_exata(
      df,
      [
          "DATA DA RECLAMACAO",
          "DATA DA RECLAMAÇÃO",
          "DATA",
          "DATA DA VENDA",
          "DATA DO PEDIDO",
      ],
  )
  col_status_valido = encontrar_coluna_exata(
      df, ["TEMPO DE IMPACTO", "VALIDACAO"]
  )
  col_produto = encontrar_coluna_exata(df, ["PRODUTO", "PRODUTO DA RECLAMACAO"])
  col_motivo = encontrar_coluna_exata(
      df, ["MOTIVO DA RECLAMACAO", "MOTIVO DA RECLAMAÇÃO", "MOTIVO"]
  )
  col_status_g = encontrar_coluna_exata(
      df, ["ACAO TOMADA", "AÇÃO TOMADA", "STATUS", "SITUACAO"]
  )
  col_sku = encontrar_coluna_exata(
      df, ["SKU", "CODIGO SKU", "ID DE RECLAMACAO"]
  )
  col_transportadora = encontrar_coluna_exata(
      df, ["TRANSPORTADORA", "TRANSP", "LOGISTICA"]
  )
  col_comentario = encontrar_coluna_exata(
      df, ["COMENTARIO", "COMENTÁRIO", "OBSERVACAO", "OBSERVAÇÃO", "OBS"]
  )

  registros = []
  for _, row in df.iterrows():
    valido_val = (
        str(row[col_status_valido]).strip()
        if col_status_valido and pd.notna(row[col_status_valido])
        else ""
    )
    status_g_val = (
        str(row[col_status_g]).strip()
        if col_status_g and pd.notna(row[col_status_g])
        else ""
    )

    valido_clean = remover_acentos(valido_val)
    status_g_clean = remover_acentos(status_g_val)

    is_valido = "VALIDO" in valido_clean
    status_afetam = ["EM MEDIACAO", "REVISAO RECUSADA", "NAO SOLICITADA"]
    is_afetando = is_valido and (status_g_clean in status_afetam)

    pedido_val = limpar_identificador(row[col_pedido]) if col_pedido else ""
    n_venda_val = limpar_identificador(row[col_n_venda]) if col_n_venda else ""
    prod_nome = (
        str(row[col_produto]).strip()
        if col_produto and pd.notna(row[col_produto])
        else ""
    )
    coment = limpar_comentario(row[col_comentario]) if col_comentario else ""
    data_ped = (
        str(row[col_data_pedido]).strip()
        if col_data_pedido and pd.notna(row[col_data_pedido])
        else ""
    )

    if not pedido_val and not n_venda_val and not prod_nome:
      continue

    registros.append({
        "pedido": pedido_val,
        "n_venda": n_venda_val,
        "sku": (
            str(row[col_sku]).strip()
            if col_sku and pd.notna(row[col_sku])
            else "N/A"
        ),
        "produto": prod_nome,
        "marca": extrair_marca(prod_nome),
        "motivo": (
            str(row[col_motivo]).strip()
            if col_motivo and pd.notna(row[col_motivo])
            else ""
        ),
        "transportadora": (
            str(row[col_transportadora]).strip()
            if col_transportadora and pd.notna(row[col_transportadora])
            else ""
        ),
        "status": status_g_val,
        "tempo_impacto": valido_val,
        "data_pedido": data_ped,
        "comentario": coment,
        "is_valido": is_valido,
        "is_afetando": is_afetando,
    })
  return registros


def processar_amazon():
  df = parse_csv_dinamico(
      URL_CSV_AMAZON, ["PEDIDO", "IMPACTO", "MOTIVO", "PRODUTO"]
  )
  print("COLUNAS AMAZON:", list(df.columns))

  col_pedido = encontrar_coluna_exata(
      df, ["ID DO PEDIDO", "PEDIDO", "NUMERO DO PEDIDO"]
  )
  col_data_sol = encontrar_coluna_exata(
      df, ["DATA SOLICITACAO", "DATA DA SOLICITACAO", "DATA PEDIDO", "DATA"]
  )
  col_data_rei = encontrar_coluna_exata(
      df, ["DATA REIVINDICACAO", "DATA DA REIVINDICACAO", "REIVINDICACAO"]
  )
  col_sku = encontrar_coluna_exata(df, ["SKU", "ASIN"])
  col_produto = encontrar_coluna_exata(df, ["PRODUTO", "TITULO", "ITEM"])
  col_motivo = encontrar_coluna_exata(
      df, ["MOTIVO", "MOTIVO DA RECLAMACAO", "MOTIVO DA REIVINDICACAO"]
  )
  col_transp = encontrar_coluna_exata(df, ["TRANSPORTADORA", "ENVIO"])
  col_impacto = encontrar_coluna_exata(df, ["IMPACTO", "STATUS", "SITUACAO"])
  col_valor = encontrar_coluna_exata(df, ["RESULTADO", "VALOR"])
  col_reembolso = encontrar_coluna_exata(
      df, ["REEMBOLSO", "VALOR REEMBOLSO", "VALOR DO REEMBOLSO"]
  )
  col_comentario = encontrar_coluna_exata(
      df, ["COMENTARIO", "COMENTARIOS", "OBSERVACAO", "OBS"]
  )

  registros = []
  for _, row in df.iterrows():
    pedido_val = limpar_identificador(row[col_pedido]) if col_pedido else ""
    if not pedido_val:
      continue

    impacto_val = (
        str(row[col_impacto]).strip()
        if col_impacto and pd.notna(row[col_impacto])
        else ""
    )
    impacto_clean = remover_acentos(impacto_val)

    is_removido = "REMOVIDO" in impacto_clean or "NEGADA" in impacto_clean
    is_valido = impacto_clean != "" and "DESCONSIDERAR" not in impacto_clean
    is_afetando = is_valido and not is_removido

    prod_nome = (
        str(row[col_produto]).strip()
        if col_produto and pd.notna(row[col_produto])
        else ""
    )

    registros.append({
        "pedido": pedido_val,
        "data_solicitacao": (
            str(row[col_data_sol]).strip()
            if col_data_sol and pd.notna(row[col_data_sol])
            else ""
        ),
        "data_reivindicacao": (
            str(row[col_data_rei]).strip()
            if col_data_rei and pd.notna(row[col_data_rei])
            else ""
        ),
        "sku": (
            str(row[col_sku]).strip()
            if col_sku and pd.notna(row[col_sku])
            else "N/A"
        ),
        "marca": extrair_marca(prod_nome),
        "produto": prod_nome,
        "motivo": (
            str(row[col_motivo]).strip()
            if col_motivo and pd.notna(row[col_motivo])
            else ""
        ),
        "transportadora": (
            str(row[col_transp]).strip()
            if col_transp and pd.notna(row[col_transp])
            else ""
        ),
        "impacto": impacto_val,
        "valor": (
            str(row[col_valor]).strip()
            if col_valor and pd.notna(row[col_valor])
            else ""
        ),
        "reembolso": (
            str(row[col_reembolso]).strip()
            if col_reembolso and pd.notna(row[col_reembolso])
            else ""
        ),
        "comentario": (
            limpar_comentario(row[col_comentario]) if col_comentario else ""
        ),
        "is_valido": is_valido,
        "is_afetando": is_afetando,
    })
  return registros


if __name__ == "__main__":
  ml_data = processar_ml()
  amz_data = processar_amazon()

  output = {"ml": ml_data, "amazon": amz_data}

  with open("impactos_ml.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

  print(f"Concluído: {len(ml_data)} ML | {len(amz_data)} Amazon")
