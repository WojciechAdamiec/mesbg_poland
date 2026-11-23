document.addEventListener('DOMContentLoaded', function() {
  // Wait a bit for elements to be rendered
  setTimeout(function() {
    const header = document.getElementById('pvw-sort-column');
    if (header) {
      header.style.cursor = 'pointer';
      header.onclick = function() {
        const btn = document.getElementById('pvw-sort-toggle');
        if (btn) {
          btn.click();
        }
      };
    }
  }, 100);
});

// Also attach when table updates
const observer = new MutationObserver(function(mutations) {
  const header = document.getElementById('pvw-sort-column');
  if (header && !header.onclick) {
    header.style.cursor = 'pointer';
    header.onclick = function() {
      const btn = document.getElementById('pvw-sort-toggle');
      if (btn) {
        btn.click();
      }
    };
  }
});

observer.observe(document.body, {
  childList: true,
  subtree: true,
});
