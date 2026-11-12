const format = new Intl.NumberFormat("en-US");

async function renderInventory() {
  const response = await fetch(new URL("repository-inventory.json", import.meta.url));
  if (!response.ok) return;
  const data = await response.json();
  const keys = ["total", "public", "private", "internal"];
  if (!keys.every(key => Number.isInteger(data[key]) && data[key] >= 0)
      || data.public + data.private + data.internal !== data.total
      || !/^\d{4}-\d{2}-\d{2}$/.test(data.updated)) return;
  const asOf = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" })
    .format(new Date(data.updated + "T00:00:00Z"));
  for (const key of keys) {
    document.getElementById("inventory-" + key).textContent = format.format(data[key]);
  }
  document.getElementById("inventory-internal-metric").hidden = data.internal === 0;
  document.getElementById("inventory-date").textContent = "Owner-verified inventory as of " + asOf + ".";
  document.getElementById("repository-inventory").hidden = false;
}

export function renderRepositoryStats(snapshot) {
  const { repos, account } = snapshot;
  const totals = {
    "repository-count": repos.length,
    "star-count": repos.reduce((total, repo) => total + repo.stars, 0),
    "fork-count": repos.reduce((total, repo) => total + repo.forks, 0),
    "follower-count": account?.followers,
  };
  for (const [id, value] of Object.entries(totals)) {
    const metric = document.getElementById(id);
    metric.textContent = Number.isFinite(value) ? format.format(value) : "—";
  }
  void renderInventory().catch(() => {});
}
