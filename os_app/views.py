# os_app/views.py
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import Http404
from django.conf import settings
from .forms import OrdemServicoForm
from .firebird_ops_simple import inserir_ordem, listar_ordens, obter_ordem, _get_field_metadata
from .firebird_db import fb_connect, CHARSET

TABLE_OS = 'TORDEMSERVICO'
EMPRESA_DEFAULT = getattr(settings, 'EMPRESA_DEFAULT', 1)  # ajuste se necessário
IDCOL = 'IDORDEM'
EMPCOL = 'EMPRESA'


def abrir_os(request):
    """Form público para abrir uma ordem — grava no Firebird."""
    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            # mapeamento mínimo do form para colunas do banco
            data = {
                'DESCRICAOOBJETO': form.cleaned_data.get('descricaoobjeto') or '',
                'DEFEITO': form.cleaned_data.get('defeito') or '',
                'SITUACAO': 'REGISTRADA',
                'IDUSUARIO': form.cleaned_data.get('idusuario') or 1,
            }
            # inserir no Firebird (inserir_ordem fará encode de BLOB binário quando necessário)
            try:
                new_id = inserir_ordem(TABLE_OS, data, empresa=EMPRESA_DEFAULT)
            except Exception as e:
                # reportar erro no form
                form.add_error(None, f"Erro ao salvar no Firebird: {e}")
                return render(request, 'os_app/abrir_os.html', {'form': form})
            return redirect(reverse('os_app:sucesso', kwargs={'pk': new_id}))
    else:
        form = OrdemServicoForm()
    return render(request, 'os_app/abrir_os.html', {'form': form})


def sucesso(request, pk):
    """Página de sucesso que mostra a OS criada."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")
    return render(request, 'os_app/sucesso.html', {'os': item})


def listar_os(request):
    """Painel público que lista ordens da empresa."""
    ords = listar_ordens(TABLE_OS, EMPRESA_DEFAULT)
    return render(request, 'os_app/listar_os.html', {'ordens': ords})


def editar_os(request, pk):
    """Editar OS: GET = preenche form, POST = atualiza no Firebird."""
    # obter registro atual
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST)
        if form.is_valid():
            # montar updates apenas com colunas válidas
            updates = {}
            # mapeie os campos do form para nomes de coluna do DB
            if 'descricaoobjeto' in form.cleaned_data:
                updates['DESCRICAOOBJETO'] = form.cleaned_data.get('descricaoobjeto')
            if 'defeito' in form.cleaned_data:
                updates['DEFEITO'] = form.cleaned_data.get('defeito')
            if 'idusuario' in form.cleaned_data and form.cleaned_data.get('idusuario') is not None:
                updates['IDUSUARIO'] = form.cleaned_data.get('idusuario')
            # se quiser permitir alterar SITUACAO via form, adicione aqui

            if not updates:
                form.add_error(None, "Nenhum campo para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

            # usar metadata para tratar BLOBs binários
            meta = _get_field_metadata(TABLE_OS)
            set_parts = []
            params = []
            for col_upper, val in ((k.upper(), v) for k, v in updates.items()):
                # ignore PK / EMPRESA
                if col_upper in (IDCOL.upper(), EMPCOL.upper()):
                    continue
                # se coluna BLOB binária -> encode str->bytes
                subtype = meta.get(col_upper, {}).get('subtype', 0)
                if subtype == 0 and isinstance(val, str):
                    try:
                        val = val.encode(CHARSET)
                    except Exception:
                        val = val.encode(CHARSET, errors='replace')
                set_parts.append(f"{col_upper} = ?")
                params.append(val)

            if not set_parts:
                form.add_error(None, "Nenhuma coluna válida para atualizar.")
                return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})

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
        }
        form = OrdemServicoForm(initial=init)

    return render(request, 'os_app/editar_os.html', {'form': form, 'os': item})


def remover_os(request, pk):
    """Remover OS via POST (confirmação)."""
    item = obter_ordem(TABLE_OS, EMPRESA_DEFAULT, pk, idcol=IDCOL, empresacol=EMPCOL)
    if not item:
        raise Http404("Ordem não encontrada")

    if request.method == 'POST':
        sql = f"DELETE FROM {TABLE_OS} WHERE {EMPCOL} = ? AND {IDCOL} = ?"
        try:
            with fb_connect() as con:
                cur = con.cursor()
                cur.execute(sql, (EMPRESA_DEFAULT, pk))
                affected = cur.rowcount
                con.commit()
                cur.close()
            return redirect('os_app:listar_os')
        except Exception as e:
            return render(request, 'os_app/confirmar_remocao.html', {'os': item, 'error': str(e)})

    return render(request, 'os_app/confirmar_remocao.html', {'os': item})
