# os_app/firebird_ops_simple.py
from .firebird_db import fb_connect, CHARSET
from django.conf import settings
import time

def _get_field_metadata(table):
    """Retorna dict {COLNAME: {'type': RDB$FIELD_TYPE, 'subtype': FIELD_SUB_TYPE}}"""
    table = table.upper()
    sql = """
    SELECT TRIM(RF.RDB$FIELD_NAME) AS FIELD_NAME,
           F.RDB$FIELD_TYPE, COALESCE(F.RDB$FIELD_SUB_TYPE, 0) AS FIELD_SUB_TYPE
    FROM RDB$RELATION_FIELDS RF
    JOIN RDB$FIELDS F ON RF.RDB$FIELD_SOURCE = F.RDB$FIELD_NAME
    WHERE RF.RDB$RELATION_NAME = ?
    ORDER BY RF.RDB$FIELD_POSITION
    """
    with fb_connect() as con:
        cur = con.cursor()
        cur.execute(sql, (table,))
        rows = cur.fetchall()
        cur.close()
    meta = {}
    for r in rows:
        name = r[0].strip().upper()
        meta[name] = {'type': r[1], 'subtype': int(r[2])}
    return meta

def _next_id_max(table, empresa, idcol='IDORDEM', empresacol='EMPRESA'):
    """Gera próximo id usando SELECT COALESCE(MAX(id),0)+1 (com filtro por empresa)."""
    t = table.upper()
    idcol_u = idcol.upper()
    empcol_u = empresacol.upper()
    with fb_connect() as con:
        cur = con.cursor()
        cur.execute(f"SELECT COALESCE(MAX({idcol_u}),0)+1 FROM {t} WHERE {empcol_u} = ?", (empresa,))
        row = cur.fetchone()
        cur.close()
    return int(row[0]) if row and row[0] is not None else 1

def inserir_ordem(table, data: dict, empresa, idcol='IDORDEM', empresacol='EMPRESA', max_retries=5, retry_delay=0.05):
    """
    Insere um registro em `table` usando NEXT ID = SELECT MAX+1.
    - data: dict com chaves nome das colunas (case-insensitive).
    - empresa: valor da coluna EMPRESA (necessário para gerar ID)
    - retorna: id criado (IdOrdem)
    Tenta re-gerar e reinserir até max_retries em caso de erro (ex.: PK duplicada).
    """
    t = table.upper()
    meta = _get_field_metadata(t)
    data_up = {k.upper(): v for k, v in data.items()}

    idcol_u = idcol.upper()
    empcol_u = empresacol.upper()

    # garantir empresa presente
    data_up[empcol_u] = empresa

    # montar colunas válidas
    valid_cols_all = [c for c in meta.keys()]
    # We'll set id dynamically if not provided
    if idcol_u in data_up and data_up[idcol_u]:
        # Se usuário já forneceu ID, usa direto (sem gerar)
        start_ids = [int(data_up[idcol_u])]
    else:
        # vamos gerar ids dinamicamente nas tentativas
        start_ids = []

    attempt = 0
    last_exception = None
    while attempt < max_retries:
        attempt += 1

        if not start_ids:
            new_id = _next_id_max(t, empresa, idcol=idcol_u, empresacol=empcol_u)
        else:
            new_id = start_ids[0]

        # assegura valor
        data_up[idcol_u] = new_id

        # montar colunas que realmente existem na tabela e tem valor em data_up
        valid_cols = [c for c in valid_cols_all if c in data_up]
        if not valid_cols:
            raise RuntimeError("Nenhuma coluna válida para inserção.")

        placeholders = ", ".join(["?"] * len(valid_cols))
        columns_sql = ", ".join(valid_cols)

        # preparar params convertendo strings para bytes quando BLOB binário (subtype 0)
        params = []
        for c in valid_cols:
            val = data_up.get(c)
            field_meta = meta.get(c, {})
            subtype = field_meta.get('subtype', 0)
            if subtype == 0 and isinstance(val, str):
                try:
                    val = val.encode(CHARSET)
                except Exception:
                    val = val.encode(CHARSET, errors='replace')
            params.append(val)

        sql = f"INSERT INTO {t} ({columns_sql}) VALUES ({placeholders}) RETURNING {idcol_u}"
        with fb_connect() as con:
            cur = con.cursor()
            try:
                cur.execute(sql, tuple(params))
                row = cur.fetchone()
                con.commit()
                cur.close()
                return row[0] if row and row[0] is not None else new_id
            except Exception as e:
                # captura exceção e decide retry se for conflito de PK/unique
                con.rollback()
                cur.close()
                last_exception = e
                errstr = str(e).upper()
                # heurística: se parecer violação de PK/UNIQUE/CONSTRAINT, tentamos novamente
                if ("UNIQUE" in errstr) or ("CONSTRAINT" in errstr) or ("DUPLICAT" in errstr) or ("VIOLATION" in errstr) or ("-803" in errstr):
                    # espera um pouco e tenta novo MAX+1
                    time.sleep(retry_delay)
                    # limpa o id fornecido para gerar novo na próxima iteração
                    if start_ids:
                        # se o id veio do usuário, não vamos ficar em loop - abortar
                        break
                    continue
                else:
                    # erro diferente: aborta imediatamente
                    raise
    # se sair do loop sem sucesso, propaga último erro
    if last_exception:
        raise last_exception
    raise RuntimeError("Falha desconhecida ao inserir registro.")

def listar_ordens(table, empresa, empresacol='EMPRESA', order_by='ABERTURADATA', limit=None):
    t = table.upper()
    empcol_u = empresacol.upper()
    sql = f"SELECT * FROM {t} WHERE {empcol_u} = ?"
    if order_by:
        sql += f" ORDER BY {order_by} DESC"
    if limit:
        sql += f" ROWS 1 TO {limit}"
    with fb_connect() as con:
        cur = con.cursor()
        cur.execute(sql, (empresa,))
        rows = cur.fetchall()
        cols = [c[0].strip().upper() for c in cur.description]
        cur.close()
    results = []
    for r in rows:
        d = {}
        for i, col in enumerate(cols):
            val = r[i]
            # decode bytes if necessary
            if isinstance(val, bytes):
                try:
                    val = val.decode(CHARSET)
                except Exception:
                    pass
            d[col.lower()] = val
        results.append(d)
    return results

def obter_ordem(table, empresa, idordem, idcol='IDORDEM', empresacol='EMPRESA'):
    t = table.upper()
    idcol_u = idcol.upper()
    empcol_u = empresacol.upper()
    sql = f"SELECT * FROM {t} WHERE {empcol_u} = ? AND {idcol_u} = ?"
    with fb_connect() as con:
        cur = con.cursor()
        cur.execute(sql, (empresa, idordem))
        row = cur.fetchone()
        if not row:
            cur.close()
            return None
        cols = [c[0].strip().upper() for c in cur.description]
        cur.close()
    d = {}
    for i, col in enumerate(cols):
        val = row[i]
        if isinstance(val, bytes):
            try:
                val = val.decode(CHARSET)
            except Exception:
                pass
        d[col.lower()] = val
    return d
