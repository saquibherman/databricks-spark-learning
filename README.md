# Introduction to Apache Spark

Databricks Academy course *Introduction to Apache Spark* (ASP 1, v3.0.1), set up to be **edited in VS
Code and executed on Azure Databricks**. It covers Spark 4 runtime architecture, DataFrames and Spark SQL,
distributed-systems basics (partitioning, the shuffle) and ETL with the DataFrame API. Clone the repo, run
one script, and the notebooks run in your own workspace. My notes are in [NOTES.md](NOTES.md).

| Section | Contents |
|---|---|
| [00_Course_Overview](00_Course_Overview.ipynb) | Objectives, prerequisites, agenda |
| [01_Demo_Required_Setup](01_Demo_Required_Setup.ipynb) | **Run once first**: `intro_spark` schema, volumes, customer CSVs, synthetic `flights` table |
| [1_Apache_Spark_Runtime_Architecture](1_Apache_Spark_Runtime_Architecture/) | 1.1–1.2 lectures, 1.3 demo: SparkSession, SparkContext, Spark UI |
| [2_Spark_DataFrames_and_SQL](2_Spark_DataFrames_and_SQL/) | 2.1–2.2 lectures, 2.3 demo: reading and writing CSV/Parquet, schemas |
| [3_Distributed_Systems_Programming_Fundamentals](3_Distributed_Systems_Programming_Fundamentals/) | 3.1 lecture: shared-nothing, partitions, shuffle, MapReduce |
| [4_ETL_with_the_DataFrame_API](4_ETL_with_the_DataFrame_API/) | 4.1 lecture, 4.2 flight data ETL demo, 4.3 lab on `samples.bakehouse` |

---

## Quick start

**Prerequisites**
- Azure Databricks workspace with **Unity Catalog** (Premium tier)
- Permission to create a catalog (`labuser_<you>`, shared with the Data_Engineering repos) and a cluster
- Linux, macOS or WSL with `bash`, `curl`, `unzip`, `python3`
- VS Code with the **Databricks** extension (on WSL: install it *in WSL*)
- No Marketplace datasets: the course reads the built-in `samples` catalog (`tpch`, `bakehouse`) and
  generates its flight data

**Setup**

```bash
cd Introduction_to_Apache_Spark
./setup.sh
```

`setup.sh` is safe to re-run. It:
1. installs the Databricks CLI and `uv` into `~/.local/bin` if missing (no sudo);
2. logs in to your workspace (OAuth, profile `azure-de`), asking for the workspace URL once, and writes
   it to the git-ignored `databricks.local.yml` (the VS Code extension needs it in the bundle);
3. creates `.venv` (Python 3.12) with Databricks Connect 17.3 (must match the cluster's DBR; also works on serverless);
4. creates your course catalog `labuser_<you>`, checks `samples`, and writes `<default catalog>.ops.meta_spark`;
5. creates the classic cluster **Intro to Apache Spark (&lt;you&gt;)** (DBR 17.3 LTS, dedicated, 1 worker,
   `Standard_D4ds_v5`, auto-terminates after 30 min), terminates it right away, and adds its ID to
   `databricks.local.yml` so the VS Code extension uses it;
6. writes `.env` for local runs, pointing Databricks Connect at that cluster;
7. syncs the course to `/Workspace/Users/<you>/.bundle/introduction-to-apache-spark-course/dev/files`.

**Run the course**
1. In the workspace, **Compute → Intro to Apache Spark (&lt;you&gt;) → Start**.
2. Open the synced `01_Demo_Required_Setup`, attach the cluster, **Run all** (once).
3. Work through the sections. Lectures are mostly reading and knowledge checks; the 1.3, 2.3 and 4.2
   demos and the 4.3 lab run code.

The 4.3 lab contains `<FILL_IN>` exercises and is not expected to run unmodified.

### Classic cluster or serverless?

The course asks for a **classic cluster on DBR 17.3 LTS**, because 1.3 uses `sc` (SparkContext) and the
Spark UI, which only a dedicated classic cluster exposes. Everything else also runs on **serverless**
(notebooks are pinned to environment version 4 = Spark 4.0 / Python 3.12), which starts faster and needs
no cluster. To see real worker/executor distribution in the Spark UI, keep the 1-worker cluster; for a
cheaper single-node cluster, edit it in **Compute** (Single node), though the Executors tab then only
shows the driver.

---

## Status

| Check | Result |
|---|---|
| All `%run` targets and `$./` notebook links resolve after renaming | ✅ |
| `setup.sh` end to end | ✅ |
| `01_Demo_Required_Setup` → `Version_Info` (serverless job run) | ✅ |
| `2.3` and `4.2` demos (serverless job run) | ✅ |
| `1.3` demo on the classic cluster: job run in Databricks, and its code locally over Databricks Connect 17.3 | ✅ |

---

## Repository layout

```
.
├── setup.sh              # One-shot setup (tools, login, .venv, UC bootstrap, cluster, .env, sync)
├── databricks.yml        # Databricks Asset Bundle: syncs the repo to the workspace
├── databricks.local.yml  # (git-ignored, written by setup.sh) your workspace host
├── .env.example          # Template for .env (setup.sh fills it in)
├── .vscode/settings.json # .venv interpreter, notebook working dir, Databricks cell markers
├── scripts/
│   ├── set_serverless_env.py   # Pin notebooks to a serverless environment version
│   ├── static_code_blocks.py   # Pre-render JS code blocks so they show in VS Code
│   └── static_widgets.py       # Quizzes, flip cards, tabs as static HTML for VS Code
├── NOTES.md, Version_Info.ipynb
├── 00_Course_Overview.ipynb, 01_Demo_Required_Setup.ipynb
├── 1_Apache_Spark_Runtime_Architecture/     # Section_Overview + 1.1 … 1.3
├── 2_Spark_DataFrames_and_SQL/              # Section_Overview + 2.1 … 2.3
├── 3_Distributed_Systems_Programming_Fundamentals/   # Section_Overview + 3.1
├── 4_ETL_with_the_DataFrame_API/            # Section_Overview + 4.1 … 4.3
└── Includes/             # Classroom-Setup-*.sql (%run by the demos/lab), _common.py
```

---

## How the course was adapted to a regular workspace

| Change | Where | Why |
|---|---|---|
| Course folder flattened into the repo root, top-level `Includes/` merged in, names with spaces/colons/` - ` → underscores, all `%run` and `$./` links updated | all | Same conventions as the other course repos; paths with spaces are awkward in shells and links |
| `.sql`/`.py` source notebooks → `.ipynb` (workspace exporter) | lessons, `Version_Info` | Same as the other repos. `Includes/*` stay source files (`%run` targets) |
| 1.3 demo: SQL-language notebook → Python (its `%python` prefixes removed) | 1.3 | All its code cells were `%python`; as a SQL notebook VS Code can't run them with the Python kernel |
| Serverless environment v4 in notebook metadata | all `.ipynb` (`scripts/set_serverless_env.py`) | Matches DBR 17.3 / Spark 4.0 when a notebook runs on serverless |
| `"0 - Required Setup"` → `01_Demo_Required_Setup` in text and `ensure_setup()` errors | `Includes/Classroom-Setup-Common.sql`, 00, 01, 2.3, 4.2 | Points at the notebook's actual name |
| JavaScript in `%md-sandbox` cells → static HTML: Prism code blocks pre-highlighted (`scripts/static_code_blocks.py`); multiple-choice and true/false knowledge checks, flip cards and Spark UI tabs rewritten with *Show answer* / *Click for more* folds (`scripts/static_widgets.py`) | lectures, labs, 1.3 demo | VS Code doesn't run scripts in markdown, so code collapsed into plain text and quizzes rendered empty; now they look the same in VS Code and Databricks (no score counter, light/dark toggle or Copy button) |
| `restartPython()` only on Databricks | `Includes/_common.py` | `dbutils.library` does not exist over Databricks Connect |
| `DBAcademyHelper` reads `<default catalog>.ops.meta_spark` (was `ops.meta` under `dbacademy`) | `Includes/_common.py`, created by `setup.sh` | `dbacademy` only exists in Academy labs; own table so the other repos' `ops.meta*` aren't overwritten |
| `labuser_<you>` created by `setup.sh` with a `MANAGED LOCATION` | `setup.sh` | The metastore has no storage root, so `Classroom-Setup-Common`'s plain `CREATE CATALOG` would fail; it now finds the catalog existing |
| Classic DBR 17.3 cluster created by `setup.sh` | `setup.sh` | The course requires it for the Spark UI demo |
| Dropped `Includes/QC Automation/` and the course `.gitignore`/`README.md` | — | Academy-internal test runner (writes to `dbacademy`) and authoring files |

---

## Where to run what

| Notebook content | Local (VS Code + Databricks Connect) | Serverless | Classic cluster |
|---|:-:|:-:|:-:|
| Python/PySpark cells in 2.3, 4.2, 4.3 | ✅ (after `%run` setup in the workspace) | ✅ | ✅ |
| `01_Demo_Required_Setup`, SQL cells, `%run` Classroom-Setup | ❌ (SQL-language notebooks, `%run`) | ✅ | ✅ |
| 1.3 demo | ✅ on the cluster (Spark UI in **Compute → cluster → Spark UI**; `sc` is never available over Databricks Connect, the demo handles that) | ❌ (`spark.app.id`, `cache()` fail) | ✅ |

Rule of thumb: **edit locally, run the lessons in the workspace** (from the synced bundle folder).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `The flights table was not found in <catalog>.intro_spark` | Setup notebook not run in this catalog | Run `01_Demo_Required_Setup` once |
| `UC_METASTORE_STORAGE_ROOT_URL_NOT_FOUND_WITH_DEFAULT_STORAGE` in Classroom Setup | `labuser_<you>` doesn't exist yet, so the notebook tried a plain `CREATE CATALOG` | Run `./setup.sh` (creates it with a managed location) |
| `Metadata table <catalog>.ops.meta_spark not found` (Version_Info) | Workspace not bootstrapped | Run `./setup.sh` |
| `sc` is not defined / no Spark UI link | Notebook is on serverless or a standard-access cluster | Attach the dedicated **Intro to Apache Spark** cluster |
| Local run: `CONFIG_NOT_AVAILABLE` for `spark.app.id`, or `cache()` fails | Running on serverless | Use the cluster: `DATABRICKS_CLUSTER_ID` in `.env` (setup.sh writes it) and the cluster selected in the Databricks extension; restart the kernel |
| Local run on the cluster: version or protocol mismatch error | `databricks-connect` newer than DBR 17.3 | `uv pip install --python .venv "databricks-connect==17.3.*"` (setup.sh pins it) |
| Cluster creation failed in `setup.sh` | No cluster-create permission, or node type unavailable | Create one in **Compute**: Dedicated access, 17.3 LTS, then re-run (it is detected by name) |
| VS Code: Databricks sidebar never logs in; `UrlError: Invalid host name` | No `workspace.host` in the bundle | Run `./setup.sh`, then **Developer: Reload Window** |
| Local run: `default auth: metadata-service ... Connection refused` | The extension's auth helper moved to a new port | `DATABRICKS_AUTH_TYPE=databricks-cli` in `.env` (setup.sh writes it); restart the kernel |
| Local run: `cannot configure default credentials`, OAuth token expired | CLI login expired | `databricks auth login -p azure-de` |

---

## Credits

Course notebooks and setup scripts are from **Databricks Academy** (© Databricks, Inc. All rights
reserved), with the adaptations listed above. Notes, `setup.sh`, configuration and scripts are my own.
