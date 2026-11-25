#!/usr/bin/env bash
# One-shot setup: tools, Databricks login, local .venv, Unity Catalog bootstrap, classic cluster, .env, sync.
# Safe to re-run. Usage:
#   ./setup.sh                       # interactive (asks for workspace URL on first run)
#   DATABRICKS_HOST=https://adb-....azuredatabricks.net ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

PROFILE="azure-de"          # OAuth profile (shared with Data_Engineering): CLI, bundle, VS Code, local runs
SPARK_VERSION="17.3.x-scala2.13"   # DBR 17.3 LTS (Apache Spark 4.0), what the course was tested on
NODE_TYPE="Standard_D4ds_v5"       # 4 cores / 16 GB; driver + 1 worker
export PATH="$HOME/.local/bin:$PATH"

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 1. tools
say "Checking tools"
if ! command -v databricks >/dev/null; then
  echo "Installing Databricks CLI into ~/.local/bin (no sudo)"
  mkdir -p "$HOME/.local/bin"; tmp=$(mktemp -d)
  V=$(curl -fsSL https://api.github.com/repos/databricks/cli/releases/latest | grep -m1 '"tag_name"' | cut -d'"' -f4 | sed 's/^v//')
  case "$(uname -m)" in x86_64) ARCH=amd64;; aarch64|arm64) ARCH=arm64;; *) warn "unsupported CPU"; exit 1;; esac
  OS=$(uname -s | tr '[:upper:]' '[:lower:]')
  F="databricks_cli_${V}_${OS}_${ARCH}.zip"
  curl -fsSL -o "$tmp/$F" "https://github.com/databricks/cli/releases/download/v${V}/$F"
  curl -fsSL -o "$tmp/sums" "https://github.com/databricks/cli/releases/download/v${V}/databricks_cli_${V}_SHA256SUMS"
  (cd "$tmp" && grep " $F\$" sums | sha256sum -c -)
  unzip -q -o "$tmp/$F" -d "$tmp/out" && install -m 755 "$tmp/out/databricks" "$HOME/.local/bin/databricks"
  rm -rf "$tmp"
fi
if ! command -v uv >/dev/null; then
  echo "Installing uv into ~/.local/bin"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
fi
databricks -v; uv --version

# ---------------------------------------------------------------- 2. login
say "Databricks authentication (profile: $PROFILE)"
if ! databricks current-user me -p "$PROFILE" >/dev/null 2>&1; then
  HOST="${DATABRICKS_HOST:-}"
  [ -z "$HOST" ] && read -rp "Workspace URL (e.g. https://adb-123.4.azuredatabricks.net): " HOST
  databricks auth login --host "$HOST" --profile "$PROFILE"
fi
USER_EMAIL=$(databricks current-user me -p "$PROFILE" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)["userName"])')
HOST=$(databricks auth describe -p "$PROFILE" -o json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("details",{}).get("host") or d.get("host"))')
echo "Logged in as $USER_EMAIL on $HOST"

# The VS Code Databricks extension needs workspace.host in the bundle ("Invalid host name" otherwise).
# Keep it in a git-ignored file that databricks.yml includes, so the repo has no host.
cat > databricks.local.yml <<EOF
# Machine-specific bundle settings, git-ignored. Written by setup.sh.
targets:
  dev:
    workspace:
      host: ${HOST%/}
EOF
echo "Wrote databricks.local.yml (workspace host for the bundle and VS Code extension)"

# ---------------------------------------------------------------- 3. local venv
say "Local Python environment (.venv, Python 3.12 = DBR 17.3 / serverless env v4)"
[ -d .venv ] || uv venv .venv --python 3.12
# databricks-connect must match the cluster's DBR (17.3); this client also works on serverless.
uv pip install --python .venv -q pip nbformat ipykernel "databricks-connect==17.3.*" databricks-sdk pandas
echo "Installed: $(.venv/bin/python -c 'from importlib.metadata import version as v;print("databricks-connect",v("databricks-connect"))')"

# ---------------------------------------------------------------- 4. Unity Catalog bootstrap
say "Unity Catalog bootstrap"
DEFAULT_CATALOG=$(databricks settings default-namespace get -p "$PROFILE" -o json 2>/dev/null \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["namespace"]["value"])' 2>/dev/null || echo workspace)
WAREHOUSE=$(databricks warehouses list -p "$PROFILE" -o json | python3 -c '
import json,sys;w=json.load(sys.stdin)
w.sort(key=lambda x:(x.get("state")!="RUNNING", not x.get("enable_serverless_compute",False)))
print(w[0]["id"] if w else "")')
[ -n "$WAREHOUSE" ] || { warn "No SQL warehouse found; create one (Serverless, 2X-Small) and re-run."; exit 1; }
echo "Default catalog: $DEFAULT_CATALOG | SQL warehouse: $WAREHOUSE"

run_sql() {
  databricks api post /api/2.0/sql/statements -p "$PROFILE" --json "$(python3 -c '
import json,sys;print(json.dumps({"warehouse_id":sys.argv[1],"statement":sys.argv[2],"wait_timeout":"50s"}))' "$WAREHOUSE" "$1")" \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);s=d["status"]
if s["state"]!="SUCCEEDED": sys.exit("SQL failed: "+s.get("error",{}).get("message",""))'
}

# Per-user course catalog, named exactly as Includes/Classroom-Setup-Common does: labuser_<user[:19]>.
# Shared with the Data_Engineering repos; this course only adds the intro_spark schema to it.
USER_CATALOG=$(python3 -c '
import re,sys;u=re.sub(r"_+","_",re.sub(r"[^a-z0-9_]","_",sys.argv[1].split("@")[0].strip().lower())).strip("_") or "user"
print("labuser_"+u[:19])' "$USER_EMAIL")
# Metastores without a storage root (Azure "Default Storage") reject the plain CREATE CATALOG in
# Classroom-Setup-Common, so the catalog is created here with the default catalog's storage root.
ROOT=$(databricks catalogs get "$DEFAULT_CATALOG" -p "$PROFILE" -o json | python3 -c 'import json,sys;print(json.load(sys.stdin).get("storage_root") or "")')
LOCATION=""; [ -n "$ROOT" ] && LOCATION="MANAGED LOCATION '$ROOT'"
run_sql "CREATE CATALOG IF NOT EXISTS $USER_CATALOG $LOCATION COMMENT 'Databricks Academy courses'" \
  && echo "  [ok]      catalog $USER_CATALOG" \
  || warn "Could not create catalog $USER_CATALOG (see error above). Create it in Catalog Explorer, then re-run."

# Datasets: the built-in samples catalog (tpch for 01 setup, bakehouse for the 4.3 lab). The flight
# data is generated by 01_Demo_Required_Setup.
if databricks tables get samples.bakehouse.sales_transactions -p "$PROFILE" >/dev/null 2>&1 \
   && databricks tables get samples.tpch.customer -p "$PROFILE" >/dev/null 2>&1; then
  echo "  [ok]      samples.tpch, samples.bakehouse"
else
  warn "samples.tpch / samples.bakehouse not readable; the setup notebook and the 4.3 lab need them"
fi

# Metadata for DBAcademyHelper (Includes/_common.py, used by Version_Info). Own table, so the ML and
# Data_Engineering setups (ops.meta, ops.meta_de, ops.meta_ade) aren't overwritten.
run_sql "CREATE SCHEMA IF NOT EXISTS $DEFAULT_CATALOG.ops COMMENT 'DBAcademy course metadata'"
run_sql "CREATE OR REPLACE TABLE $DEFAULT_CATALOG.ops.meta_spark (key STRING, value STRING)"
run_sql "INSERT INTO $DEFAULT_CATALOG.ops.meta_spark VALUES ('username','$USER_EMAIL'),('catalog_name','$USER_CATALOG'),('schema_name','intro_spark'),('datasets.samples','samples')"
echo "Wrote $DEFAULT_CATALOG.ops.meta_spark"

# ---------------------------------------------------------------- 5. classic cluster
# The demos use the Spark UI and sc (SparkContext), which only a dedicated-access classic cluster
# exposes. Created once and terminated straight away; start it from Compute when you need it.
say "Classic cluster (DBR 17.3 LTS, dedicated)"
CLUSTER_NAME="Intro to Apache Spark ($(cut -d@ -f1 <<<"$USER_EMAIL"))"
CLUSTER_ID=$(databricks clusters list -p "$PROFILE" -o json | python3 -c '
import json,sys;n=sys.argv[1];print(next((c["cluster_id"] for c in json.load(sys.stdin) if c.get("cluster_name")==n),""))' "$CLUSTER_NAME")
if [ -z "$CLUSTER_ID" ]; then
  SPEC=$(python3 -c '
import json,sys;n,v,t,u=sys.argv[1:]
print(json.dumps({"cluster_name":n,"spark_version":v,"node_type_id":t,"num_workers":1,
  "autotermination_minutes":30,"data_security_mode":"SINGLE_USER","single_user_name":u,
  "runtime_engine":"STANDARD","custom_tags":{"course":"introduction-to-apache-spark"}}))' \
    "$CLUSTER_NAME" "$SPARK_VERSION" "$NODE_TYPE" "$USER_EMAIL")
  if CLUSTER_ID=$(databricks clusters create --json "$SPEC" --no-wait -p "$PROFILE" -o json \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["cluster_id"])'); then
    databricks clusters delete "$CLUSTER_ID" --no-wait -p "$PROFILE" >/dev/null   # = terminate, not delete
    echo "  [created] $CLUSTER_NAME ($CLUSTER_ID), terminated until you start it"
  else
    warn "Could not create the cluster (see error above). Create one in Compute: Dedicated, $SPARK_VERSION, then re-run."
  fi
else
  echo "  [ok]      $CLUSTER_NAME ($CLUSTER_ID)"
fi
# Let the VS Code extension (and Run File as Workflow) use this cluster by default.
if [ -n "$CLUSTER_ID" ]; then
  printf '    cluster_id: %s\n' "$CLUSTER_ID" >> databricks.local.yml
  echo "  [ok]      cluster_id added to databricks.local.yml"
fi

# ---------------------------------------------------------------- 6. .env
say "Local run configuration"
sed -e "s#^DATABRICKS_CONFIG_PROFILE=.*#DATABRICKS_CONFIG_PROFILE=$PROFILE#" \
    -e "s#^DATABRICKS_CLUSTER_ID=.*#DATABRICKS_CLUSTER_ID=$CLUSTER_ID#" .env.example > .env
echo "Wrote .env (profile $PROFILE, cluster $CLUSTER_ID)"

# ---------------------------------------------------------------- 7. sync
say "Syncing course to the workspace"
databricks bundle validate >/dev/null
databricks bundle sync --full | tail -1
echo "Files: /Workspace/Users/$USER_EMAIL/.bundle/introduction-to-apache-spark-course/dev/files"

say "Done. In the Databricks UI: start the '$CLUSTER_NAME' cluster, open the synced
    01_Demo_Required_Setup notebook, attach the cluster and run it once; then work through the sections."
