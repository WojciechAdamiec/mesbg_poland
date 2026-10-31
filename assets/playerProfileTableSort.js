// Click-to-sort for tables with class "pp-sortable" (delegated, so it survives Dash re-renders).
document.addEventListener("click", function (event) {
  var th = event.target.closest && event.target.closest("table.pp-sortable th");
  if (!th) return;

  var table = th.closest("table");
  var tbody = table.querySelector("tbody");
  var index = Array.prototype.indexOf.call(th.parentNode.children, th);
  var descending = th.dataset.sortDir === "asc";

  Array.prototype.forEach.call(th.parentNode.children, function (cell) {
    delete cell.dataset.sortDir;
    cell.textContent = cell.textContent.replace(/ [▲▼]$/, "");
  });
  th.dataset.sortDir = descending ? "desc" : "asc";
  th.textContent += descending ? " ▼" : " ▲";

  var value = function (row) {
    var text = row.children[index].textContent.trim().replace("%", "");
    var number = parseFloat(text);
    return isNaN(number) || !/^-?[\d.]+$/.test(text) ? text.toLowerCase() : number;
  };

  var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
  rows.sort(function (a, b) {
    var x = value(a), y = value(b);
    var result = x < y ? -1 : x > y ? 1 : 0;
    return descending ? -result : result;
  });
  rows.forEach(function (row) { tbody.appendChild(row); });
});

(function () {
  var style = document.createElement("style");
  style.textContent = "table.pp-sortable th { cursor: pointer; user-select: none; }";
  document.head.appendChild(style);
})();
