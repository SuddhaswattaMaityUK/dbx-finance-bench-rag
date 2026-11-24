# Setup

Setup steps for the Databricks CLI and Databricks Asset Bundles (DABs).

## Prerequisites

- macOS or Linux
- A Databricks workspace
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/install.html) v0.218+

## 1. Install the Databricks CLI

```bash
brew tap databricks/tap
brew trust databricks/tap   # required: Homebrew refuses to load formulas from untrusted taps
brew install databricks
databricks --version        # expected: v0.218+ (tested with v1.26.0)
```

Without Homebrew:

```bash
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

## 2. Authenticate

```bash
databricks auth login --host https://<your-workspace>.cloud.databricks.com
databricks current-user me   # verify
```

This opens a browser for OAuth and saves a profile in `~/.databrickscfg`.

## 3. Deploy with Databricks Asset Bundles

```bash
databricks bundle validate                # check the config
databricks bundle deploy -t dev           # deploy to the dev target
databricks bundle run <job_name> -t dev   # run a job
databricks bundle destroy -t dev          # tear down
```

## 4. CI/CD with GitHub Actions

| Workflow | Trigger | Action |
| --- | --- | --- |
| [deploy-dev.yml](../.github/workflows/deploy-dev.yml) | Push to any branch except `master` | Validate and deploy to `dev` |
| [deploy-prod.yml](../.github/workflows/deploy-prod.yml) | Push (merge) to `master` | Validate and deploy to `prod` |

### Branch strategy

Trunk-based: `master` is the only long-lived branch and always reflects what is in prod.

1. Branch from `master` using a short-lived name, e.g. `feature/<short-description>` or `fix/<short-description>`.
2. Every push to the branch deploys the bundle to `dev` (deploy-dev.yml).
3. Open a pull request into `master`. Review it and confirm the dev deployment works.
4. Merge to `master`. The merge deploys the bundle to `prod` (deploy-prod.yml).
5. Delete the feature branch.

Never commit directly to `master`.

### One-time setup

1. In Databricks, create a service principal and an OAuth secret for it (Settings > Identity and access > Service principals). Give it access to the workspace and the catalog/schema the bundle uses.
2. In GitHub, create two environments, `dev` and `prod` (Settings > Environments). Add required reviewers to `prod` if you want a manual approval gate.
3. Add these secrets, at repository level or per environment:

| Secret | Value |
| --- | --- |
| `DATABRICKS_HOST` | `https://<your-workspace>.cloud.databricks.com` |
| `DATABRICKS_CLIENT_ID` | Service principal application (client) ID |
| `DATABRICKS_CLIENT_SECRET` | Service principal OAuth secret |

4. Grant the service principal access to Unity Catalog. Run this once in a SQL editor as the catalog owner (use the service principal's **Application ID** in backticks, not its display name):

```sql
-- One schema per layer; the jobs create it if it is missing (CREATE SCHEMA below)
CREATE SCHEMA IF NOT EXISTS workspace.finance_bench_bronze;

GRANT USE CATALOG ON CATALOG workspace TO `<client-id>`;
GRANT USE SCHEMA, CREATE VOLUME, CREATE TABLE
  ON SCHEMA workspace.finance_bench_bronze TO `<client-id>`;
```

   Dev and prod write to the same schema (`finance_bench_bronze`), so these grants cover both targets. The `download` task creates the schema on a fresh workspace (`CREATE SCHEMA IF NOT EXISTS`). For that, the service principal also needs `CREATE SCHEMA` on the catalog:

   ```sql
   GRANT CREATE SCHEMA ON CATALOG workspace TO `<client-id>`;
   ```

   Without these grants the job fails with `PERMISSION_DENIED ... does not have CREATE SCHEMA` or similar. If you change the `catalog` or `bronze_schema` variables in [databricks.yml](../databricks.yml), change them here too.

5. Protect `master` (Settings > Branches) so changes only land through pull requests.
