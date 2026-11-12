"""Refresh daily commit and line totals from owned public default branches."""

from datetime import UTC, date, datetime
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOGIN = 'soubhik-biswas'
ACCOUNT_ID = 54506603

VIEWER_QUERY = '''
query { viewer { login databaseId id } }
'''

REPO_QUERY = '''
query ($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id visibility isFork owner { login }
  }
}
'''

HISTORY_QUERY = '''
query ($repo: ID!, $author: ID!, $cursor: String) {
  node(id: $repo) {
    ... on Repository {
      visibility isFork owner { login }
      defaultBranchRef {
        target {
          ... on Commit {
            history(first: 100, after: $cursor, author: {id: $author}) {
              pageInfo { hasNextPage endCursor }
              nodes {
                oid authoredDate additions deletions
                author { user { databaseId } }
              }
            }
          }
        }
      }
    }
  }
}
'''


def graphql(query, **variables):
    result = subprocess.run(
        ['gh', 'api', 'graphql', '--input', '-'],
        input=json.dumps({'query': query, 'variables': variables}),
        capture_output=True, text=True, timeout=45, check=False,
    )
    if result.returncode:
        raise RuntimeError('GitHub GraphQL query failed; keeping the previous snapshot')
    response = json.loads(result.stdout)
    if response.get('errors') or not response.get('data'):
        raise RuntimeError('GitHub returned incomplete GraphQL data; keeping the previous snapshot')
    return response['data']


def verify_repository(repository):
    if (
        not repository
        or repository['visibility'] != 'PUBLIC'
        or repository['owner']['login'] != LOGIN
        or repository['isFork']
    ):
        raise RuntimeError('Repository is outside public snapshot scope; keeping the previous snapshot')


def collect(snapshot):
    viewer = graphql(VIEWER_QUERY)['viewer']
    if viewer['databaseId'] != ACCOUNT_ID or viewer['login'] != LOGIN:
        raise RuntimeError('GitHub account identity changed; keeping the previous snapshot')

    first = date.fromisoformat(snapshot['days'][0]['date'])
    last = date.fromisoformat(snapshot['days'][-1]['date'])
    days = {}
    seen_commits = set()
    repositories = snapshot['repos']
    for entry in repositories:
        repo = graphql(REPO_QUERY, owner=LOGIN, name=entry['name'])['repository']
        verify_repository(repo)
        cursor = None
        while True:
            result = graphql(HISTORY_QUERY, repo=repo['id'], author=viewer['id'], cursor=cursor)['node']
            verify_repository(result)
            branch = result['defaultBranchRef']
            if branch is None:
                break
            history = branch['target']['history']
            for commit in history['nodes']:
                user = (commit.get('author') or {}).get('user') or {}
                day = datetime.fromisoformat(commit['authoredDate']).astimezone(UTC).date()
                if user.get('databaseId') != ACCOUNT_ID or not first <= day <= last:
                    continue
                if commit['oid'] in seen_commits:
                    continue
                seen_commits.add(commit['oid'])
                row = days.setdefault(day.isoformat(), {'commits': 0, 'additions': 0, 'deletions': 0})
                row['commits'] += 1
                row['additions'] += commit['additions']
                row['deletions'] += commit['deletions']
            page = history['pageInfo']
            if not page['hasNextPage']:
                break
            next_cursor = page['endCursor']
            if not next_cursor or next_cursor == cursor:
                raise RuntimeError('Commit history pagination stalled; keeping the previous snapshot')
            cursor = next_cursor
    return {
        'updated': datetime.now(UTC).date().isoformat(),
        'from': first.isoformat(),
        'to': last.isoformat(),
        'repositories': len(repositories),
        'days': dict(sorted(days.items())),
    }


def main():
    snapshot = json.loads((ROOT / 'assets/public-data.json').read_text())
    activity = collect(snapshot)
    destination = ROOT / 'assets/commit-activity.json'
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(activity, indent=2) + '\n')
    temporary.replace(destination)
    print(f"Collected commit totals for {activity['repositories']} public repositories")


if __name__ == '__main__':
    main()
