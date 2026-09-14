var dmcfuncs = window.dashMantineFunctions = window.dashMantineFunctions || {};
var dmc = window.dash_mantine_components;

dmcfuncs.armyListWinrateTooltip = ({ payload }) => {
  if (!payload || payload.length === 0) return null;

  var point = payload[0].payload;

  return React.createElement(
    dmc.Paper,
    { px: "md", py: "sm", withBorder: true, shadow: "md", radius: "md", bg: "dark.7", c: "white" },
    [
      React.createElement(
        dmc.Text,
        { key: "name", fw: 700, fz: "md", mb: 4 },
        point.army
      ),
      React.createElement(
        dmc.Text,
        { key: "winrate", fz: "md" },
        `Winrate: ${point.winrate.toFixed(1)}%`
      ),
      React.createElement(
        dmc.Text,
        { key: "games", fz: "md" },
        `Games: ${point.games}`
      ),
    ]
  );
};
