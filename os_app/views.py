# os_app/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import Http404, JsonResponse
from django.conf import settings
from .forms import OrdemServicoForm
from .firebird_ops_simple import (
    inserir_ordem, listar_ordens, obter_ordem,
    _get_field_metadata, cancelar_ordem
)
from .firebird_db import fb_connect, CHARSET
import json

TABLE_OS = 'TORDEMSERVICO'
TABLE_OBJ = 'TORDEMOBJETO'  # tabela de objetos (veículos)
TABLE_CLIENTE = 'TORDECLIENTE'  # tabela de clientes (tentativa - se existir)
EMPRESA_DEFAULT = getattr(settings, 'EMPRESA_DEFAULT', 1)  # ajuste se necessário
IDCOL = 'IDORDEM'
EMPCOL = 'EMPRESA'


def _is_blob_column(meta_entry: dict) -> bool:
    """
    Heurística: considera BLOB quando RDB$FIELD_TYPE == 261 (BLOB) ou quando houver 'subtype'.
    meta_entry é o dicionário retornado por _get_field_metadata.
    """
    if not meta_entry:
        return False
    t = meta_entry.get('type')
    if t == 261:  # 261 = BLOB no Firebird
        return True
    if 'subtype' in meta_entry:
        return True
    return False


# ----------------------
# APIs AJAX / helpers
# ----------------------
def objetos_por_proprietario(request, cliente_id):
    """
    Retorna JSON com lista de objetos (id + label) pertencentes ao cliente (IDCLIENTE).
    Label montado como "TIPO - MARCA - MODELO - PLACA".
    """
    try:
        with fb_connect() as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT IDOBJETO, TIPO, MARCA, MODELO, PLACA
                FROM {TABLE_OBJ}
                WHERE IDCLIENTE = ?
                ORDER BY IDOBJETO
            """, (cliente_id,))
            rows = cur.fetchall()
            cur.close()

        lista = []
        for r in rows:
            idobj, tipo, marca, modelo, placa = r
            partes = []
            if tipo:
                partes.append(str(tipo))
            if marca:
                partes.append(str(marca))
            if modelo:
                partes.append(str(modelo))
            label = " - ".join(partes)
            if placa:
                label = f"{label} - PLACA: {placa}" if label else f"PLACA: {placa}"
            lista.append({'id': idobj, 'label': label})
        return JsonResponse({'objects': lista})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def objeto_detail(request, pk):
    """
    Retorna JSON com dados do objeto (tipo, marca, modelo, cor, placa).
    """
    try:
        with fb_connect() as con:
            cur = con.cursor()
            cur.execute(f"""
                SELECT IDOBJETO, TIPO, MARCA, MODELO, COR, PLACA
                FROM {TABLE_OBJ}
                WHERE IDOBJETO = ?
            """, (pk,))
            row = cur.fetchone()
            cur.close()

        if not row:
            return JsonResponse({'error': 'not found'}, status=404)
        idobj, tipo, marca, modelo, cor, placa = row
        return JsonResponse({
            'id': idobj,
            'tipo': tipo,
            'marca': marca,
            'modelo': modelo,
            'cor': cor,
            'placa': placa
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ----------------------
# views principais
# ----------------------
def abrir_os(request):
    """Form público para abrir uma ordem — grava no Firebird."""
    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            # montar descrição do objeto a partir de idobjeto ou campos manuais
            idobj = form.cleaned_data.get('idobjeto') or None
            tipo = (form.cleaned_data.get('tipo_objeto') or '').strip()
            marca = (form.cleaned_data.get('marca') or '').strip()
            modelo = (form.cleaned_data.get('modelo') or '').strip()
            placa = (form.cleaned_data.get('placa') or '').strip()

            descricao_final = ''
            if idobj:
                try:
                    with fb_connect() as con:
                        cur = con.cursor()
                        cur.execute(f"SELECT TIPO, MARCA, MODELO, COR, PLACA FROM {TABLE_OBJ} WHERE IDOBJETO = ?", (idobj,))
                        row = cur.fetchone()
                        cur.close()
                    if row:
                        tipo_db, marca_db, modelo_db, cor_db, placa_db = row
                        partes = [p for p in (tipo_db, marca_db, modelo_db) if p]
                        descricao_final = " - ".join(map(str, partes))
                        placa_val = placa_db or placa
                        if placa_val:
                            descricao_final = f"{descricao_final} - PLACA: {placa_val}" if descricao_final else f"PLACA: {placa_val}"
                    else:
                        partes = [p for p in (tipo, marca, modelo) if p]
                        descricao_final = " - ".join(partes)
                        if placa:
                            descricao_final = f"{descricao_final} - PLACA: {placa}" if descricao_final else f"PLACA: {placa}"
                except Exception:
                    partes = [p for p in (tipo, marca, modelo) if p]
                    descricao_final = " - ".join(partes)
                    if placa:
                        descricao_final = f"{descricao_final} - PLACA: {placa}" if descricao_final else f"PLACA: {placa}"
            else:
                partes = [p for p in (tipo, marca, modelo) if p]
                descricao_final = " - ".join(partes)
                if placa:
                    descricao_final = f"{descricao_final} - PLACA: {placa}" if descricao_final else f"PLACA: {placa}"

            descricao_livre = (form.cleaned_data.get('descricaoobjeto') or '').strip()
            if not descricao_final and descricao_livre:
                descricao_final = descricao_livre

            data = {
                'DESCRICAOOBJETO': descricao_final,
                'DEFEITO': form.cleaned_data.get('defeito') or '',
                'SITUACAO': 'REGISTRADA',
                'IDUSUARIO': form.cleaned_data.get('idusuario') or 1,
                'IDOBJETO': idobj,
                'PLACA': placa or (None if placa == '' else placa),
                'NOMECLIENTE': form.cleaned_data.get('nome_cliente') or '',
                'EMAILCLIENTE': form.cleaned_data.get('email_cliente') or '',
                'LOCALIZACAOOBJ': form.cleaned_data.get('localizacao') or '',
                'PROPRIETARIO': form.cleaned_data.get('proprietario') or '',
                'NATUREZA': form.cleaned_data.get('natureza') or '',
                'CONDPAGTO': form.cleaned_data.get('cond_pagto') or '',
                'PREVISAODATA': form.cleaned_data.get('previsao_data') or None,
                'PREVISAOHORA': form.cleaned_data.get('previsao_hora') or None,
                'VENDEDOR': form.cleaned_data.get('vendedor') or '',
                'TECNICO': form.cleaned_data.get('tecnico') or '',
                'PERTENCES': form.cleaned_data.get('pertencentes') or '',
                'OBSERVACOES': form.cleaned_data.get('observacoes') or '',
                'ENTRADA': form.cleaned_data.get('entrada') if form.cleaned_data.get('entrada') not in (None, '') else None,
            }

            # converter strings -> bytes apenas para colunas BLOB
            try:
                meta = _get_field_metadata(TABLE_OS) or {}
                data_encoded = {}
                for col_name, val in data.items():
                    col_upper = col_name.upper()
                    entry = meta.get(col_upper, {})
                    if val is None:
                        data_encoded[col_name] = None
                        continue
                    is_blob = _is_blob_column(entry)
                    if is_blob and isinstance(val, str):
                        try:
                            data_encoded[col_name] = val.encode(CHARSET)
                        except Exception:
                            data_encoded[col_name] = val.encode(CHARSET, errors='replace')
                    else:
                        data_encoded[col_name] = val
            except Exception:
                data_encoded = data

            try:
                new_id = inserir_ordem(TABLE_OS, data_encoded, empresa=EMPRESA_DEFAULT)
            except Exception as e:
                form.add_error(None, f"Erro ao salvar no Firebird: {e}")
                # tentar carregar clients para re-renderizar
                clients = []
                try:
                    with fb_connect() as con:
                        cur = con.cursor()
                        cur.execute(f"SELECT IDCLIENTE, NOME FROM {TABLE_CLIENTE} ORDER BY NOME")
                        rows = cur.fetchall()
                        cur.close()
                        clients = [{'id': r[0], 'nome': r[1]} for r in rows]
                except Exception:
                    clients = []
                return render(request, 'os_app/abrir_os.html', {'form': form, 'clients': clients})
            return redirect(reverse('os_app:sucesso', kwargs={'pk': new_id}))
    else:
        form = OrdemServicoForm()

    # carregar lista de proprietários (clientes) para popular select (se existir)
    clients = []
    try:
        with fb_connect() as con:
            cur = con.cursor()
            cur.execute(f"SELECT IDCLIENTE, NOME FROM {TABLE_CLIENTE} ORDER BY NOME")
            rows = cur.fetchall()
            cur.close()
        clients = [{'id': r[0], 'nome': r[1]} for r in rows]
    except Exception:
        clients = []

    return render(request, 'os_app/abrir_os.html', {'form': form, 'clients': clients})


def sucesso(request, pk):
    """Página de sucesso que mostra a OS criada."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    # pk pronto para uso no template (evita filtros complexos no template)
    edit_pk = item.get('idordem') or item.get('id')

    # também enviar JSON serializado (para uso por scripts se necessário)
    try:
        os_json = json.dumps(item, default=str)
    except Exception:
        os_json = '{}'

    return render(request, 'os_app/sucesso.html', {'os': item, 'edit_pk': edit_pk, 'os_json': os_json})


def listar_os(request):
    """Painel público que lista ordens da empresa."""
    ords = listar_ordens(TABLE_OS, EMPRESA_DEFAULT)
    return render(request, 'os_app/listar_os.html', {'ordens': ords})


def editar_os(request, pk):
    """Editar OS: GET = preenche form, POST = atualiza no Firebird."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            updates = {}

            mapping = {
                'descricaoobjeto': 'DESCRICAOOBJETO',
                'defeito': 'DEFEITO',
                'idusuario': 'IDUSUARIO',
                'nome_cliente': 'NOMECLIENTE',
                'email_cliente': 'EMAILCLIENTE',
                'placa': 'PLACA',
                'localizacao': 'LOCALIZACAOOBJ',
                'proprietario': 'PROPRIETARIO',
                'natureza': 'NATUREZA',
                'cond_pagto': 'CONDPAGTO',
                'previsao_data': 'PREVISAODATA',
                'previsao_hora': 'PREVISAOHORA',
                'vendedor': 'VENDEDOR',
                'tecnico': 'TECNICO',
                'pertencentes': 'PERTENCES',
                'observacoes': 'OBSERVACOES',
                'entrada': 'ENTRADA',
                'idobjeto': 'IDOBJETO',
            }

            for fkey, colname in mapping.items():
                if fkey in form.cleaned_data:
                    val = form.cleaned_data.get(fkey)
                    if val is not None and (not (isinstance(val, str) and val == '')):
                        updates[colname] = val

            if not updates:
                form.add_error(None, "Nenhum campo para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

            meta = _get_field_metadata(TABLE_OS) or {}

            set_parts = []
            params = []
            for col_upper, val in ((k.upper(), v) for k, v in updates.items()):
                if col_upper in (IDCOL.upper(), EMPCOL.upper()):
                    continue

                entry = meta.get(col_upper, {})
                is_blob = _is_blob_column(entry)

                if val is None:
                    param_val = None
                else:
                    if is_blob and isinstance(val, str):
                        try:
                            param_val = val.encode(CHARSET)
                        except Exception:
                            param_val = val.encode(CHARSET, errors='replace')
                    else:
                        param_val = val

                set_parts.append(f"{col_upper} = ?")
                params.append(param_val)

            if not set_parts:
                form.add_error(None, "Nenhuma coluna válida para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

            params.append(EMPRESA_DEFAULT)
            params.append(pk)
            sql = f"UPDATE {TABLE_OS} SET {', '.join(set_parts)} WHERE {EMPCOL} = ? AND {IDCOL} = ?"

            try:
                with fb_connect() as con:
                    cur = con.cursor()
                    cur.execute(sql, tuple(params))
                    affected = cur.rowcount
                    con.commit()
                    cur.close()
                if not affected:
                    form.add_error(None, "Nenhuma linha foi atualizada.")
                    return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})
                return redirect('os_app:listar_os')
            except Exception as e:
                form.add_error(None, f"Erro ao atualizar: {e}")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

    else:
        init = {
            'descricaoobjeto': item.get('descricaoobjeto'),
            'defeito': item.get('defeito'),
            'idusuario': item.get('idusuario'),
            'nome_cliente': item.get('nomecliente') or item.get('nome_cliente'),
            'email_cliente': item.get('emailcliente') or item.get('email_cliente'),
            'placa': item.get('placa'),
            'localizacao': item.get('localizacaoobj') or item.get('localizacao_obj'),
            'proprietario': item.get('proprietario'),
            'natureza': item.get('natureza'),
            'cond_pagto': item.get('condpagto') or item.get('cond_pagto'),
            'previsao_data': item.get('previsao_data') or item.get('previsaodata') or item.get('previsaodata'),
            'previsao_hora': item.get('previsao_hora') or item.get('previsaohora') or item.get('previsaohora'),
            'vendedor': item.get('vendedor'),
            'tecnico': item.get('tecnico'),
            'pertencentes': item.get('pertences'),
            'observacoes': item.get('observacoes'),
            'entrada': item.get('entrada'),
            'idobjeto': item.get('idobjeto') or item.get('id_objeto'),
        }

        # se existir idobjeto, tentar buscar dados do objeto pra preencher marca/modelo/placa/tipo
        try:
            objid = init.get('idobjeto')
            if objid:
                with fb_connect() as con:
                    cur = con.cursor()
                    cur.execute(f"SELECT TIPO, MARCA, MODELO, COR, PLACA FROM {TABLE_OBJ} WHERE IDOBJETO = ?", (objid,))
                    r = cur.fetchone()
                    cur.close()
                if r:
                    tipo_db, marca_db, modelo_db, cor_db, placa_db = r
                    init['tipo_objeto'] = tipo_db
                    init['marca'] = marca_db
                    init['modelo'] = modelo_db
                    init['cor'] = cor_db
                    if not init.get('placa') and placa_db:
                        init['placa'] = placa_db
        except Exception:
            pass

        form = OrdemServicoForm(initial=init)

    return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})


def cancelar_os(request, pk):
    """Cancelar (marcar como 'CANCELADA') a OS via POST (confirmação)."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        try:
            # usa helper cancelamento caso queira lógica mais completa
            cancelar_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, usuario_id=None, motivo=None)
            return redirect('os_app:listar_os')
        except Exception as e:
            return render(request, 'os_app/confirmar_remocao.html', {'os': item, 'error': str(e)})

    return render(request, 'os_app/confirmar_remocao.html', {'os': item})
