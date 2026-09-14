# Install the final GitHub profile portfolio

This version generates its GitHub statistics, activity calendar, streaks, and contribution snake inside your own repository. It does **not** depend on the broken public stats, activity-graph, or trophy endpoints.

## 1. Repository requirement

Use the public profile repository named exactly:

```text
adarsh-pathak-2006
```

Its default branch must be `main`.

## 2. Replace the previous version

Upload the contents of this package to the repository root and preserve this structure:

```text
README.md
SETUP.md
assets/
resume/
.github/scripts/generate_profile_metrics.py
.github/workflows/profile-assets.yml
```

### Important cleanup

Delete the old workflow if it is still present:

```text
.github/workflows/snake.yml
```

The new `profile-assets.yml` workflow generates **both** the self-hosted metrics and the snake. Keeping both workflows could make them overwrite the `output` branch at the same time.

## 3. Allow the workflow to publish images

1. Open the profile repository on GitHub.
2. Select **Settings → Actions → General**.
3. Scroll to **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

No personal access token is required. The workflow uses GitHub's repository token.

## 4. Generate the profile visuals

1. Open the repository's **Actions** tab.
2. Select **Build profile visuals**.
3. Click **Run workflow** and choose `main`.
4. Wait for the green success check.

The workflow creates or refreshes an `output` branch containing:

```text
profile-overview.svg
profile-activity.svg
github-contribution-grid-snake.svg
github-contribution-grid-snake-dark.svg
```

The workflow refreshes these files daily.

## 5. Verify the installation

1. Open the branch selector and confirm that an `output` branch exists.
2. Open that branch and confirm the four SVG files listed above are present.
3. Return to your profile and hard-refresh the page.
4. GitHub image caching can take 1–3 minutes after the first run.

If an image still shows alt text, open its raw URL once and refresh the profile:

```text
https://raw.githubusercontent.com/adarsh-pathak-2006/adarsh-pathak-2006/output/profile-overview.svg
```

## 6. What updates automatically

The workflow reads GitHub's own REST and GraphQL APIs and recalculates:

- Public repositories
- Stars across owned repositories
- Followers
- Contributions during the rolling 12 months
- Current and longest activity streaks
- Active days and best contribution day
- Primary repository languages
- Contribution calendar and snake animation

## 7. Recommended pinned repositories

Pin these in this order:

1. `where_is_my_train_backend`
2. `AI--Interview-System`
3. `Tic-Tac-Toe-Multiplayer`
4. `Ekokintsugi-Website`

Use the remaining two slots for projects that demonstrate different strengths.

## Troubleshooting

### Workflow fails while pushing

Recheck **Settings → Actions → General → Workflow permissions → Read and write permissions**.

### Workflow succeeds but images are missing

Confirm the `output` branch contains the generated SVG files, then wait a few minutes and hard-refresh.

### The old broken images still appear

Confirm the new `README.md` was committed to `main`. Search the README and remove any remaining references to:

```text
github-readme-stats.vercel.app
github-readme-activity-graph.vercel.app
github-profile-trophy.vercel.app
```

### Update the résumé

Replace `resume/Adarsh_Pathak_ATS_Resume.pdf` while keeping the same filename.
