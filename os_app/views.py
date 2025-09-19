# os_app/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import Http404
from django.conf import settings
from .forms import OrdemServicoForm
from .firebird_ops_simple import inserir_ordem, listar_ordens, obter_ordem, _get_field_metadata, cancelar_ordem
from .firebird_db import fb_connect, CHARSET

TABLE_OS = 'TORDEMSERVICO'
EMPRESA_DEFAULT = getattr(settings, 'EMPRESA_DEFAULT', 1)  # ajuste se necessário
IDCOL = 'IDORDEM'
EMPCOL = 'EMPRESA'


def _is_blob_column(meta_entry: dict) -> bool:
    """
    Heurística para detectar se uma coluna é BLOB a partir do metadata retornado
    por _get_field_metadata. meta_entry é o dicionário para a coluna.
    """
    if not meta_entry:
        return False
    t = meta_entry.get('type')
    if t and str(t).upper() == 'BLOB':
        return True
    # se existir 'subtype' no metadata, quase sempre indica BLOB/text blob
    if 'subtype' in meta_entry:
        return True
    return False


def abrir_os(request):
    """Form público para abrir uma ordem — grava no Firebird."""
    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            # mapeamento do form para colunas do banco (use nomes em maiúsculas conforme o DB)
            data = {
                'DESCRICAOOBJETO': form.cleaned_data.get('descricaoobjeto') or '',
                'DEFEITO': form.cleaned_data.get('defeito') or '',
                'SITUACAO': 'REGISTRADA',
                'IDUSUARIO': form.cleaned_data.get('idusuario') or 1,
                # campos adicionais
                'NOMECLIENTE': form.cleaned_data.get('nome_cliente') or '',
                'EMAILCLIENTE': form.cleaned_data.get('email_cliente') or '',
                'PLACA': form.cleaned_data.get('placa') or '',
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

            # tentar obter metadata e converter strings -> bytes para colunas BLOB
            try:
                meta = _get_field_metadata(TABLE_OS) or {}
                data_encoded = {}
                for col_name, val in data.items():
                    col_upper = col_name.upper()
                    entry = meta.get(col_upper, {})
                    if val is None:
                        data_encoded[col_name] = None
                        continue
                    # detecta BLOB
                    if _is_blob_column(entry) and isinstance(val, str):
                        try:
                            data_encoded[col_name] = val.encode(CHARSET)
                        except Exception:
                            data_encoded[col_name] = val.encode(CHARSET, errors='replace')
                    else:
                        data_encoded[col_name] = val
            except Exception:
                # se metadata falhar, usa os dados originais (fallback)
                data_encoded = data

            # inserir no Firebird
            try:
                new_id = inserir_ordem(TABLE_OS, data_encoded, empresa=EMPRESA_DEFAULT)
            except Exception as e:
                # reportar erro no form
                form.add_error(None, f"Erro ao salvar no Firebird: {e}")
                return render(request, 'os_app/abrir_os.html', {'form': form})
            # redireciona para a página de sucesso usando pk (id gerado)
            return redirect(reverse('os_app:sucesso', kwargs={'pk': new_id}))
    else:
        form = OrdemServicoForm()
    return render(request, 'os_app/abrir_os.html', {'form': form})


def sucesso(request, pk):
    """Página de sucesso que mostra a OS criada."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")
    # item é um dict (chaves minúsculas) vindo do helper — passamos direto como 'os'
    return render(request, 'os_app/sucesso.html', {'os': item})


def listar_os(request):
    """Painel público que lista ordens da empresa."""
    ords = listar_ordens(TABLE_OS, EMPRESA_DEFAULT)
    return render(request, 'os_app/listar_os.html', {'ordens': ords})


def editar_os(request, pk):
    """Editar OS: GET = preenche form, POST = atualiza no Firebird."""
    # obter registro atual (item será um dict com chaves minúsculas)
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            # montar updates apenas com colunas válidas (em maiúsculas para o DB)
            updates = {}

            # campos que permitimos atualizar pelo form
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
            }

            for fkey, colname in mapping.items():
                if fkey in form.cleaned_data:
                    val = form.cleaned_data.get(fkey)
                    # evitar inserir '' em campos numéricos ou None problemático
                    if val is not None and (not (isinstance(val, str) and val == '')):
                        updates[colname] = val

            if not updates:
                form.add_error(None, "Nenhum campo para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

            # metadata para detectar BLOB subtypes
            meta = _get_field_metadata(TABLE_OS) or {}

            set_parts = []
            params = []
            for col_upper, val in ((k.upper(), v) for k, v in updates.items()):
                # ignore PK / EMPRESA por segurança
                if col_upper in (IDCOL.upper(), EMPCOL.upper()):
                    continue

                # detectar se coluna é BLOB via metadata
                entry = meta.get(col_upper, {})
                is_blob = _is_blob_column(entry)

                # tratar valores conforme tipo
                if val is None:
                    param_val = None
                else:
                    # Se for BLOB e for string -> encode para bytes
                    if is_blob and isinstance(val, str):
                        try:
                            param_val = val.encode(CHARSET)
                        except Exception:
                            param_val = val.encode(CHARSET, errors='replace')
                    else:
                        # se não for BLOB (ou já é bytes), passa direto
                        param_val = val

                set_parts.append(f"{col_upper} = ?")
                params.append(param_val)

            if not set_parts:
                form.add_error(None, "Nenhuma coluna válida para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

            # ordem dos params: valores..., EMPRESA_DEFAULT, pk
            params.append(EMPRESA_DEFAULT)
            params.append(pk)
            sql = f"UPDATE {TABLE_OS} SET {', '.join(set_parts)} WHERE {EMPCOL} = ? AND {IDCOL} = ?"

            # executar update via fb_connect
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
        # inicializar form com valores do registro (chaves do item são minúsculas)
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
        }
        form = OrdemServicoForm(initial=init)

    return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})


def cancelar_os(request, pk):
    """Cancelar (marcar como 'CANCELADA') a OS via POST (confirmação)."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        sql = f"UPDATE {TABLE_OS} SET SITUACAO = ? WHERE {EMPCOL} = ? AND {IDCOL} = ?"
        try:
            with fb_connect() as con:
                cur = con.cursor()
                cur.execute(sql, ('CANCELADA', EMPRESA_DEFAULT, pk))
                affected = cur.rowcount
                con.commit()
                cur.close()
            # opcional: você pode querer manter a OS visível no painel, por isso apenas atualizamos SITUACAO
            return redirect('os_app:listar_os')
        except Exception as e:
            return render(request, 'os_app/confirmar_remocao.html', {'os': item, 'error': str(e)})

    # se GET, mostrar a mesma tela de confirmação (reutiliza o template)
    return render(request, 'os_app/confirmar_remocao.html', {'os': item})

