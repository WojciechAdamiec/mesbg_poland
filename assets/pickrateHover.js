document.addEventListener('DOMContentLoaded', function() {
  // Delegate hover events for army rows
  document.addEventListener('mouseenter', function(e) {
    if (e.target.closest('.pvw-army-row')) {
      const row = e.target.closest('.pvw-army-row');
      const armyName = row.querySelector('td')?.textContent || '';
      highlightDotOnChart(armyName);
    }
  }, true);
  
  document.addEventListener('mouseleave', function(e) {
    if (e.target.closest('.pvw-army-row')) {
      clearDotHighlight();
    }
  }, true);
});

function highlightDotOnChart(armyName) {
  // Find all circles (dots) in the scatter chart
  const circles = document.querySelectorAll('#pvw-chart circle');
  
  circles.forEach(circle => {
    // Look for the army name in nearby text elements
    const parentGroup = circle.closest('g');
    if (parentGroup) {
      const textElement = parentGroup.querySelector('text');
      if (textElement && textElement.textContent.includes(armyName)) {
        // Highlight this dot
        circle.style.r = '10';
        circle.style.filter = 'drop-shadow(0 0 8px #00ffff)';
        circle.style.opacity = '1';
      } else {
        // Dim other dots
        circle.style.opacity = '0.3';
      }
    }
  });
}

function clearDotHighlight() {
  const circles = document.querySelectorAll('#pvw-chart circle');
  circles.forEach(circle => {
    circle.style.r = '6';
    circle.style.filter = 'none';
    circle.style.opacity = '1';
  });
}
