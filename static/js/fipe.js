(() => {
  const form = document.getElementById('fipe-selecao');
  if (!form) return;
  form.querySelectorAll('select, input[type="search"]').forEach(control => {
    control.addEventListener('change', () => {
      (control.dataset.reset || '').split(',').filter(Boolean).forEach(name => {
        const child = form.elements.namedItem(name);
        if (child) child.value = '';
      });
      form.requestSubmit();
    });
  });
})();
