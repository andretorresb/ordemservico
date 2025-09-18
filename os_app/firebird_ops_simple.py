# os_app/firebird_ops_simple.py
from .firebird_db import fb_connect, CHARSET
from django.conf import settings

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

def _next_id_gen(table, empresa, idcol='IDORDEM', empresacol='EMPRESA'):
    """Gera novo id: usa gen_name em settings se existirem, senão MAX(id)+1 por empresa."""
    gen_name = settings.FIREBIRD_DB.get('gen_name')
    t = table.upper()
    idcol_u = idcol.upper()
    empcol_u = empresacol.upper()

    with fb_connect() as con:
        cur = con.cursor()
        if gen_name:
            # tenta usar generator
            cur.execute(f"SELECT GEN_ID({gen_name}, 1) FROM RDB$DATABASE")
            row = cur.fetchone()
            new_id = row[0] if row else None
            cur.close()
            return new_id
        else:
            # fallback MAX+1 por empresa
            cur.execute(f"SELECT COALESCE(MAX({idcol_u}),0)+1 FROM {t} WHERE {empcol_u} = ?", (empresa,))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else 1

def inserir_ordem(table, data: dict, empresa, idcol='IDORDEM', empresacol='EMPRESA'):
    """
    Insere um registro em `table`.
    - data: dict com chaves nome das colunas (case-insensitive).
    - empresa: valor da coluna EMPRESA (necessário para gerar ID)
    Retorna: id criado (IdOrdem).
    """
    t = table.upper()
    meta = _get_field_metadata(t)
    data_up = {k.upper(): v for k, v in data.items()}

    # garantir EMPRESA e IDORDEM
    idcol_u = idcol.upper()
    empcol_u = empresacol.upper()

    if idcol_u not in data_up:
        new_id = _next_id_gen(t, empresa, idcol=idcol_u, empresacol=empcol_u)
        data_up[idcol_u] = new_id
    else:
        new_id = data_up[idcol_u]

    # garantir empresa presente
    data_up[empcol_u] = empresa

    # montar colunas válidas
    # buscar colunas reais pela metadata
    valid_cols = [c for c in meta.keys() if c in data_up]
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
            # BLOB binário: encode
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
        except Exception:
            con.rollback()
            # tentativa fallback sem RETURNING
            try:
                cur.execute(f"INSERT INTO {t} ({columns_sql}) VALUES ({placeholders})", tuple(params))
                con.commit()
                cur.close()
                return new_id
            except Exception as e:
                cur.close()
                raise

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
