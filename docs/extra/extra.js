(function () {
  const content = document.querySelector('.md-content');
  content.innerHTML = content.innerHTML
    .replace(/， /g, '，')
    .replace(/。 /g, '。');
  content.classList.add('heti');
  const heti = new Heti('.heti');
  heti.autoSpacing();
})();
