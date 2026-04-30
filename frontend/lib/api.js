export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${apiBase}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || 'Request failed');
  return data;
}

export async function post(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export async function get(path, headers = {}) {
  return request(path, { method: 'GET', headers });
}

export async function fetchRepos(githubToken) {
  const auth = await post('/api/auth/token', { github_token: githubToken });
  if (!auth?.token_valid) {
    throw new Error(auth?.error || 'Token invalid');
  }
  const repos = await post('/api/repos/list', { github_token: githubToken });
  return {
    user: auth.user || null,
    repos: repos?.repos || [],
  };
}

export async function generateReadme({ repoUrl, githubToken, options }) {
  return post('/api/generate-readme', { repo_url: repoUrl, github_token: githubToken, options });
}

export async function pollJob(jobId) {
  return get(`/api/job-status/${jobId}`);
}

export async function publishReadme({ repoUrl, readmeMarkdown, githubToken, branch, commitMessage, prTitle, prBody }) {
  return post('/api/publish-readme', {
    repo_url: repoUrl,
    readme_markdown: readmeMarkdown,
    github_token: githubToken,
    branch,
    commit_message: commitMessage,
    pr_title: prTitle,
    pr_body: prBody,
  });
}
