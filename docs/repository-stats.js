export function renderRepositoryStats(snapshot) {
  const { repos, account } = snapshot;
  const totals = {
    "repository-count": repos.length,
    "star-count": repos.reduce((total, repo) => total + repo.stars, 0),
    "fork-count": repos.reduce((total, repo) => total + repo.forks, 0),
    "follower-count": account.followers,
  };
  const format = new Intl.NumberFormat("en-US");
  for (const [id, value] of Object.entries(totals)) {
    const metric = document.getElementById(id);
    metric.textContent = Number.isFinite(value) ? format.format(value) : "—";
  }
}
