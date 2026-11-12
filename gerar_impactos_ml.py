import json
import pandas as pd
import unicodedata

URL_CSV_ML = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWr2yKLLA3zpokmqfZAeHeqUCgK_rtKYX7Fceb0FBI0YqNqYWHOcVklVccOiVvQAYU39T6glLbgK7D/pub?gid=1773072804&single=true&output=csv"
URL_CSV_AMAZON = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRWr2yKLLA3zpokmqfZAeHeqUCgK_rtKYX7Fceb0FBI0YqNqYWHOcVklVccOiVvQAYU39T6glLbgK7D/pub?gid=134048884&single=true&output=csv"


def normalize_str(val):
  if pd.isna(val) or val is None:
    return ""
  s = str(val).strip()
  if s.upper() in ["NAN", "NONE", "NAT"]:
    return ""
  return s


def remove_accents(s):
  return "".join(
      c
      for c in unicodedata.normalize("NFD", s)
      if unicodedata.category(c) != "Mn"
  )


def normalize_col(col):
  return remove_accents(str(col)).upper().strip()


def find_col(df, candidates):
  norm_cols = {normalize_col(c): c for c in df.columns}
  for cand in candidates:
    cand_norm = normalize_col(cand)
    if cand_norm in norm_cols:
      return norm_cols[cand_norm]
  for cand in candidates:
    cand_norm = normalize_col(cand)
    for k, orig in norm_cols.items():
      if cand_norm in k:
        return orig
  return None


def clean_id(val):
  s = normalize_str(val)
  if s.endswith(".0"):
    s = s[:-2]
  return s


def process_ml(url):
  df = pd.read_csv(url, dtype=str)
  records = []

  col_pedido = find_col(df, ["PEDIDO", "ID DO PEDIDO", "ID PEDIDO"])
  col_nvenda = find_col(
      df, ["N° VENDA", "Nº VENDA", "N DA VENDA", "NUMERO DA VENDA", "VENDA"]
  )
  col_data = find_col(df, ["DATA PEDIDO", "DATA DA VENDA", "DATA"])
  col_sku = find_col(df, ["SKU", "CODIGO"])
  col_marca = find_col(df, ["MARCA"])
  col_produto = find_col(df, ["PRODUTO", "TITULO", "ITEM"])
  col_motivo = find_col(df, ["MOTIVO", "MOTIVO DA RECLAMACAO"])
  col_transp = find_col(df, ["TRANSPORTADORA", "FORMA DE ENVIO", "ENVIO"])
  col_status = find_col(df, ["STATUS", "SITUACAO", "IMPACTO"])
  col_coment = find_col(df, ["COMENTARIO", "COMENTARIOS", "OBSERVACAO", "OBS"])

  for _, row in df.iterrows():
    pedido = clean_id(row[col_pedido]) if col_pedido else ""
    n_venda = clean_id(row[col_nvenda]) if col_nvenda else ""
    if not pedido and not n_venda:
      continue

    status = normalize_str(row[col_status]) if col_status else ""
    status_up = remove_accents(status).upper()

    is_removido = "REMOVIDO" in status_up
    is_valido = status_up != "" and "DESCONSIDERAR" not in status_up
    is_afetando = is_valido and not is_removido

    records.append({
        "pedido": pedido,
        "n_venda": n_venda,
        "data_pedido": normalize_str(row[col_data]) if col_data else "",
        "sku": normalize_str(row[col_sku]) if col_sku else "",
        "marca": normalize_str(row[col_marca]) if col_marca else "",
        "produto": normalize_str(row[col_produto]) if col_produto else "",
        "motivo": normalize_str(row[col_motivo]) if col_motivo else "",
        "transportadora": normalize_str(row[col_transp]) if col_transp else "",
        "status": status,
        "comentario": normalize_str(row[col_coment]) if col_coment else "",
        "is_valido": is_valido,
        "is_afetando": is_afetando,
    })

  return records


def process_amazon(url):
  df = pd.read_csv(url, dtype=str)
  records = []

  col_pedido = find_col(df, ["ID DO PEDIDO", "PEDIDO", "NUMERO DO PEDIDO"])
  col_data_sol = find_col(df, ["DATA SOLICITACAO", "DATA PEDIDO", "DATA"])
  col_data_rei = find_col(df, ["DATA REIVINDICACAO", "REIVINDICACAO"])
  col_sku = find_col(df, ["SKU", "ASIN"])
  col_marca = find_col(df, ["MARCA"])
  col_produto = find_col(df, ["PRODUTO", "TITULO", "ITEM"])
  col_motivo = find_col(df, ["MOTIVO", "MOTIVO DA RECLAMACAO"])
  col_transp = find_col(df, ["TRANSPORTADORA", "ENVIO"])
  col_impacto = find_col(df, ["IMPACTO", "STATUS", "SITUACAO"])
  col_valor = find_col(df, ["RESULTADO", "VALOR"])
  col_reembolso = find_col(df, ["REEMBOLSO", "VALOR REEMBOLSO"])
  col_coment = find_col(df, ["COMENTARIO", "COMENTARIOS", "OBSERVACAO", "OBS"])

  for _, row in df.iterrows():
    pedido = clean_id(row[col_pedido]) if col_pedido else ""
    if not pedido:
      continue

    impacto = normalize_str(row[col_impacto]) if col_impacto else ""
    impacto_up = remove_accents(impacto).upper()

    is_removido = "REMOVIDO" in impacto_up or "NEGADA" in impacto_up
    is_valido = impacto_up != "" and "DESCONSIDERAR" not in impacto_up
    is_afetando = is_valido and not is_removido

    records.append({
        "pedido": pedido,
        "data_solicitacao": (
            normalize_str(row[col_data_sol]) if col_data_sol else ""
        ),
        "data_reivindicacao": (
            normalize_str(row[col_data_rei]) if col_data_rei else ""
        ),
        "sku": normalize_str(row[col_sku]) if col_sku else "",
        "marca": normalize_str(row[col_marca]) if col_marca else "",
        "produto": normalize_str(row[col_produto]) if col_produto else "",
        "motivo": normalize_str(row[col_motivo]) if col_motivo else "",
        "transportadora": normalize_str(row[col_transp]) if col_transp else "",
        "impacto": impacto,
        "valor": normalize_str(row[col_valor]) if col_valor else "",
        "reembolso": normalize_str(row[col_reembolso]) if col_reembolso else "",
        "comentario": normalize_str(row[col_coment]) if col_coment else "",
        "is_valido": is_valido,
        "is_afetando": is_afetando,
    })

  return records


if __name__ == "__main__":
  ml_data = process_ml(URL_CSV_ML)
  amz_data = process_amazon(URL_CSV_AMAZON)

  output = {"ml": ml_data, "amazon": amz_data}

  with open("impactos_ml.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

  print(
      f"JSON gerado com sucesso: {len(ml_data)} registros ML e"
      f" {len(amz_data)} registros Amazon."
  )
