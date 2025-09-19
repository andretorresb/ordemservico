// scripts.js - UI + comportamento de objetos (proprietário -> objetos -> detalhes)
// Versão final que lê URLs de <div id="os-api-urls" data-*> ou de window.* e tem proteção contra double-init.
(function() {
  'use strict';

  // evita inicializar duas vezes caso o script seja carregado novamente
  if (window.OS_SCRIPTS_LOADED) return;
  window.OS_SCRIPTS_LOADED = true;

  // ---------- utilitários ----------
  function qs(id) { return document.getElementById(id); }
  function safeText(v) { return (v === null || v === undefined) ? '' : String(v); }
  function replaceZero(urlTemplate, id) {
    if(!urlTemplate) return null;
    if(urlTemplate.indexOf('/0/') !== -1) return urlTemplate.replace('/0/', '/' + encodeURIComponent(id) + '/');
    // termina em 0/ ou 0
    return urlTemplate.replace(/0(\/)?$/, encodeURIComponent(id) + '$1');
  }

  function fetchJson(url) {
    return fetch(url, { credentials: 'same-origin' }).then(function(resp){
      if(!resp.ok) throw new Error('HTTP ' + resp.status);
      return resp.json();
    });
  }

  // ---------- obter configuração (div#os-api-urls > data-*) ----------
  var apiDiv = qs('os-api-urls');
  var API_POR_PROPRIETARIO = null;
  var API_OBJETO_DETAIL = null;
  var INITIAL_OS_IDOBJ = null;

  if(apiDiv) {
    API_POR_PROPRIETARIO = apiDiv.getAttribute('data-por-proprietario') || apiDiv.dataset.porProprietario || null;
    API_OBJETO_DETAIL = apiDiv.getAttribute('data-obj-detail') || apiDiv.dataset.objDetail || null;
    INITIAL_OS_IDOBJ = apiDiv.getAttribute('data-os-id') || apiDiv.dataset.osId || null;
  }

  // fallback para variáveis globais definidas via template
  API_POR_PROPRIETARIO = API_POR_PROPRIETARIO || window.OS_API_OBJETOS_POR_PROPRIETARIO || '/os/api/objetos/por-proprietario/0/';
  API_OBJETO_DETAIL = API_OBJETO_DETAIL || window.OS_API_OBJETO_DETAIL || '/os/api/objetos/0/';

  // ---------- comportamento UI (genéricos) ----------
  document.addEventListener('DOMContentLoaded', function() {
    // fechar mensagens (se houver .message .msg-close)
    document.querySelectorAll('.message .msg-close').forEach(function(btn){
      btn.addEventListener('click', function(){
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

    // confirmação para forms com class .confirm-delete
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
    var mod   = modeloEl && modeloEl.value ? modeloEl.value.trim() : '';
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

  function populateObjectsForOwner(proprietarioId, selectEl) {
    if(!selectEl) return;
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

  function fillObjectDetail(objectId, tipoEl, marcaEl, modeloEl, corEl, placaEl, descEl){
    if(!objectId) return Promise.resolve(null);
    var url = replaceZero(API_OBJETO_DETAIL, objectId) || API_OBJETO_DETAIL.replace('0', encodeURIComponent(objectId));
    return fetchJson(url).then(function(data){
      if(data && !data.error){
        if(tipoEl) tipoEl.value   = safeText(data.tipo || '');
        if(marcaEl) marcaEl.value = safeText(data.marca || '');
        if(modeloEl) modeloEl.value = safeText(data.modelo || '');
        if(corEl) corEl.value     = safeText(data.cor || '');
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

  // ---------- auto-bind ao carregar DOM ----------
  document.addEventListener('DOMContentLoaded', function(){
    var proprietarioEl = qs('id_proprietario');
    var idobjEl = qs('id_idobjeto') || qs('id_idobjeto_hidden') || qs('id_idobjeto_field');
    var tipoEl   = qs('id_tipo_objeto') || qs('id_tipo');
    var marcaEl  = qs('id_marca') || qs('id_marcaa') || qs('id_brand');
    var modeloEl = qs('id_modelo') || qs('id_model');
    var corEl    = qs('id_cor') || qs('id_color');
    var placaEl  = qs('id_placa') || qs('id_plate');
    var descEl   = qs('id_descricaoobjeto') || qs('id_descricao_objeto') || qs('id_descricao');

    if(descEl) descEl.readOnly = true;

    // proprietario -> popula objetos
    if(proprietarioEl && idobjEl){
      proprietarioEl.addEventListener('change', function(){
        populateObjectsForOwner(this.value, idobjEl);
      });
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

    // detectar id inicial do objeto (edição)
    var initialId = (idobjEl && idobjEl.value) ? idobjEl.value : null;
    if(!initialId){
      // 1) tentar a data no div#os-api-urls
      if(INITIAL_OS_IDOBJ) initialId = INITIAL_OS_IDOBJ;
      // 2) tentar campo hidden input[name="idobjeto"]
      if(!initialId){
        var hiddenCandidate = document.querySelector('input[name="idobjeto"], input#idobjeto, input[name="id_objeto"]');
        if(hiddenCandidate && hiddenCandidate.value) initialId = hiddenCandidate.value;
      }
    }

    if(initialId){
      fillObjectDetail(initialId, tipoEl, marcaEl, modeloEl, corEl, placaEl, descEl);
      if(idobjEl) try { idobjEl.value = initialId; } catch(e){}
    } else {
      // monta descricao a partir de campos já preenchidos manualmente
      if(tipoEl || marcaEl || modeloEl || placaEl) montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl);
    }

    // re montar descrição ao editar campos
    [tipoEl, marcaEl, modeloEl, placaEl].forEach(function(el){
      if(!el) return;
      el.addEventListener('input', function(){ montarDescricaoFromFields(tipoEl, marcaEl, modeloEl, placaEl, descEl); });
    });
  });

  // expor utilitários
  window.OSUtils = window.OSUtils || {};
  window.OSUtils.montarDescricao = montarDescricaoFromFields;
  window.OSUtils.populateObjectsForOwner = populateObjectsForOwner;
  window.OSUtils.fillObjectDetail = fillObjectDetail;

  // deixa também as URLs publicamente acessíveis se alguém quiser sobrescrever
  window.OS_API_OBJETOS_POR_PROPRIETARIO = window.OS_API_OBJETOS_POR_PROPRIETARIO || API_POR_PROPRIETARIO;
  window.OS_API_OBJETO_DETAIL = window.OS_API_OBJETO_DETAIL || API_OBJETO_DETAIL;

})();
