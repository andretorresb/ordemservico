// scripts.js - pequenas melhorias de UI
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
