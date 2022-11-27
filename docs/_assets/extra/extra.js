(function () {
  const content = document.querySelector('.md-content');
  content.querySelectorAll('p').forEach(function (p) {
    p.innerHTML = p.innerHTML
      .replace(/\n/g, '')
      .replace(/([，。；：]) /g, '$1');
  });
  content.classList.add('heti');
  const heti = new Heti('.heti');
  heti.autoSpacing();
})();
