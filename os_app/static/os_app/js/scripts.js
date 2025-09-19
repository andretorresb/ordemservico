// scripts.js - UI + comportamento de objetos (proprietário -> objetos -> detalhes)
// Regras:
// - Se o template definir window.OS_API_OBJETOS_POR_PROPRIETARIO e window.OS_API_OBJETO_DETAIL,
//   o script irá usar essas strings (contendo "/0/" para substituição).
// - Caso contrário, tenta usar caminhos padrão: /os/api/objetos/por-proprietario/<id>/ e /os/api/objetos/<id>/
// - Funciona tanto no abrir_os.html quanto no editar_os.html (pré-preenchimento).
(function() {
  'use strict';

  // ---------- utilitários ----------
  function qs(id) { return document.getElementById(id); }
  function safeText(v) { return (v === null || v === undefined) ? '' : String(v); }
  function replaceZero(urlTemplate, id) {
    if(!urlTemplate) return null;
    // alguns templates usam "/0/" placeholder — substitui esse bloco
    if(urlTemplate.indexOf('/0/') !== -1) return urlTemplate.replace('/0/', '/' + encodeURIComponent(id) + '/');
    // se a URL termina com "0/" ou "0", troca também
    return urlTemplate.replace(/0(\/)?$/, encodeURIComponent(id) + '$1');
  }

  // ---------- configuração de endpoints ----------
  // templates podem definir essas variáveis (recomendado):
  // window.OS_API_OBJETOS_POR_PROPRIETARIO = "{% url 'os_app:api_objetos_por_proprietario' 0 %}";
  // window.OS_API_OBJETO_DETAIL = "{% url 'os_app:api_objeto_detail' 0 %}";
  var API_POR_PROPRIETARIO = window.OS_API_OBJETOS_POR_PROPRIETARIO || '/os/api/objetos/por-proprietario/0/';
  var API_OBJETO_DETAIL = window.OS_API_OBJETO_DETAIL || '/os/api/objetos/0/';

  // ---------- comportamento UI existente (mantido) ----------
  document.addEventListener('DOMContentLoaded', function() {
    // fechar mensagens
    document.querySelectorAll('.message .msg-close').forEach(function(btn){
      btn.addEventListener('click', function(e){
        var msg = btn.closest('.message');
        if(!msg) return;
        msg.style.transition = 'opacity 240ms ease, height 240ms ease, margin 240ms ease';
        msg.style.opacity = '0';
        msg.style.height = '0px';
        msg.style.margin = '0';
        setTimeout(function(){ if(msg && msg.parentNode) msg.parentNode.removeChild(msg); }, 300);
      });
    });

    // realce em campos que tenham erro (Django renders errors as .errors near field)
    document.querySelectorAll('.errors + input, .errors + textarea, .errors + select').forEach(function(inp){
      inp.style.borderColor = '#d9534f';
      inp.style.boxShadow = '0 0 0 4px rgba(217,83,79,0.06)';
    });

    // adicionar confirmação em formulários com class .confirm-delete (se existirem)
    document.querySelectorAll('form.confirm-delete').forEach(function(f){
      f.addEventListener('submit', function(ev){
        if(!confirm('Confirma exclusão? Esta ação não pode ser desfeita.')) {
          ev.preventDefault();
        }
      });
    });

    // foco no primeiro input do form
    (function focusFirst(){
      var first = document.querySelector('form input, form textarea, form select');
      if(first) first.focus();
    })();
  });

  // ---------- funções específicas para OS / objetos ----------
  function montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl){
    var tipo  = tipoEl  && tipoEl.value  ? tipoEl.value.trim()  : '';
    var marca = marcaEl && marcaEl.value ? marcaEl.value.trim() : '';
    var mod  = modeloEl && modeloEl.value ? modeloEl.value.trim() : '';
    var placa = placaEl && placaEl.value ? placaEl.value.trim() : '';
    var partes = [];
    if(tipo) partes.push(tipo);
    if(marca) partes.push(marca);
    if(mod) partes.push(mod);
    var s = partes.join(' - ');
    if(placa) s = (s ? (s + ' - ') : '') + 'PLACA: ' + placa;
    if(descEl) descEl.value = s;
    return s;
  }

  function fetchJson(url) {
    return fetch(url, { credentials: 'same-origin' }).then(function(resp){
      if(!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    });
  }

  // popular select de objetos para um proprietario
  function populateObjectsForOwner(proprietarioId, selectEl) {
    if(!selectEl) return;
    // limpar
    selectEl.innerHTML = '<option value="">(nenhum)</option>';
    if(!proprietarioId) return;

    var url = replaceZero(API_POR_PROPRIETARIO, proprietarioId) || API_POR_PROPRIETARIO.replace('0', encodeURIComponent(proprietarioId));
    fetchJson(url).then(function(data){
      if(data && data.objects && Array.isArray(data.objects)){
        data.objects.forEach(function(o){
          var opt = document.createElement('option');
          opt.value = o.id;
          opt.text  = o.label;
          selectEl.appendChild(opt);
        });
      }
    }).catch(function(err){
      console.error('Erro ao buscar objetos por proprietario:', err);
    });
  }

  // preencher campos do objeto a partir do detalhe
  function fillObjectDetail(objectId, tipoEl, marcaEl, modeloEl, corEl, placaEl, descEl){
    if(!objectId) return Promise.resolve(null);
    var url = replaceZero(API_OBJETO_DETAIL, objectId) || API_OBJETO_DETAIL.replace('0', encodeURIComponent(objectId));
    return fetchJson(url).then(function(data){
      if(data && !data.error){
        if(tipoEl) tipoEl.value   = safeText(data.tipo || '');
        if(marcaEl) marcaEl.value = safeText(data.marca || '');
        if(modeloEl) modeloEl.value = safeText(data.modelo || '');
        if(corEl) corEl.value = safeText(data.cor || '');
        if(placaEl) placaEl.value = safeText(data.placa || '');
        montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl);
        return data;
      }
      return null;
    }).catch(function(err){
      console.error('Erro ao buscar detalhe do objeto:', err);
      return null;
    });
  }

  // bind automático se elementos existirem no DOM
  document.addEventListener('DOMContentLoaded', function(){
    var proprietarioEl = qs('id_proprietario');
    var idobjEl = qs('id_idobjeto') || qs('id_idobjeto_hidden') || qs('id_idobjeto_field'); // tentativa de encontrar
    var tipoEl   = qs('id_tipo_objeto') || qs('id_tipo');
    var marcaEl  = qs('id_marca') || qs('id_marcaa') || qs('id_brand');
    var modeloEl = qs('id_modelo') || qs('id_model');
    var corEl    = qs('id_cor') || qs('id_color');
    var placaEl  = qs('id_placa') || qs('id_plate');
    var descEl   = qs('id_descricaoobjeto') || qs('id_descricao_objeto') || qs('id_descricao');

    // torna descricao readonly se existir
    if(descEl) descEl.readOnly = true;

    // se existir proprietario select -> popular objetos quando mudar
    if(proprietarioEl && idobjEl){
      proprietarioEl.addEventListener('change', function(){
        populateObjectsForOwner(this.value, idobjEl);
      });
      // se houver valor inicial no proprietario, já popula
      if(proprietarioEl.value){
        populateObjectsForOwner(proprietarioEl.value, idobjEl);
      }
    }

    // ao mudar objeto -> preencher campos
    if(idobjEl){
      idobjEl.addEventListener('change', function(){
        var oid = this.value;
        if(!oid){
          if(tipoEl) tipoEl.value = '';
          if(marcaEl) marcaEl.value = '';
          if(modeloEl) modeloEl.value = '';
          if(corEl) corEl.value = '';
          if(placaEl) placaEl.value = '';
          if(descEl) descEl.value = '';
          return;
        }
        fillObjectDetail(oid, tipoEl, marcaEl, modeloEl, corEl, placaEl, descEl);
      });
    }

    // se já existir valor em idobj (ex.: edição), preencher
    var initialId = (idobjEl && idobjEl.value) ? idobjEl.value : null;
    if(!initialId){
      // tentar pegar via variável no template (se definida)
      // templates antigos colocavam "{{ os.idobjeto }}" em JS; tentar buscar elemento hidden com that value
      var hiddenCandidate = document.querySelector('input[name="idobjeto"], input#idobjeto');
      if(hiddenCandidate && hiddenCandidate.value) initialId = hiddenCandidate.value;
    }
    if(initialId){
      fillObjectDetail(initialId, tipoEl, marcaEl, modeloEl, corEl, placaEl, descEl);
      // marcar select se existir
      if(idobjEl) try { idobjEl.value = initialId; } catch(e){}
    } else {
      // montar descricao com campos já preenchidos manualmente
      if(tipoEl || marcaEl || modeloEl || placaEl) montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl);
    }

    // quando usuário digitar em campos do objeto, re-montar descricao
    [tipoEl, marcaEl, modeloEl, placaEl].forEach(function(el){
      if(!el) return;
      el.addEventListener('input', function(){ montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl); });
    });
  });

  // expor funções úteis para debug/uso manual (opcional)
  window.OSUtils = {
    montarDescricao: montarDescricaoFromFields,
    populateObjectsForOwner: populateObjectsForOwner,
    fillObjectDetail: fillObjectDetail
  };

})();
