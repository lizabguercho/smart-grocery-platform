#!/usr/bin/env bash
# Create the PostgreSQL database and apply schema/tables/indexes.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example and set your database credentials:"
  echo "  cp .env.example .env"
  exit 1
fi

# Load DB_* variables from .env (ignore comments and blank lines)
set -a
# shellcheck disable=SC1091
source .env
set +a

: "${DB_HOST:?DB_HOST is not set in .env}"
: "${DB_PORT:?DB_PORT is not set in .env}"
: "${DB_NAME:?DB_NAME is not set in .env}"
: "${DB_USER:?DB_USER is not set in .env}"
: "${DB_PASSWORD:?DB_PASSWORD is not set in .env}"

add_psql_to_path_if_present() {
  local candidate
  local prefixes=()

  if command -v brew >/dev/null 2>&1; then
    prefixes+=(
      "$(brew --prefix libpq 2>/dev/null)"
      "$(brew --prefix postgresql 2>/dev/null)"
      "$(brew --prefix postgresql@17 2>/dev/null)"
      "$(brew --prefix postgresql@16 2>/dev/null)"
      "$(brew --prefix postgresql@15 2>/dev/null)"
      "$(brew --prefix postgresql@14 2>/dev/null)"
    )
  fi

  prefixes+=(
    /opt/homebrew/opt/libpq
    /usr/local/opt/libpq
    /opt/homebrew/opt/postgresql
    /usr/local/opt/postgresql
  )

  for prefix in "${prefixes[@]}"; do
    [[ -n "$prefix" ]] || continue
    candidate="$prefix/bin/psql"
    if [[ -x "$candidate" ]]; then
      export PATH="$(dirname "$candidate"):$PATH"
      return 0
    fi
  done

  return 1
}

install_psql() {
  echo "psql not found — installing PostgreSQL client tools..."

  case "$(uname -s)" in
    Darwin)
      if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is required to install psql on macOS."
        echo "Install it from https://brew.sh and re-run ./install.sh"
        exit 1
      fi
      brew install libpq
      export PATH="$(brew --prefix libpq)/bin:$PATH"
      ;;
    Linux)
      if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y postgresql-client
      elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y postgresql
      elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y postgresql
      elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm postgresql-libs
      else
        echo "Unsupported Linux package manager. Install postgresql-client manually."
        exit 1
      fi
      ;;
    *)
      echo "Unsupported OS: $(uname -s). Install the PostgreSQL client (psql) manually."
      exit 1
      ;;
  esac
}

ensure_psql() {
  if command -v psql >/dev/null 2>&1; then
    return 0
  fi

  if add_psql_to_path_if_present && command -v psql >/dev/null 2>&1; then
    echo "Using psql at: $(command -v psql)"
    return 0
  fi

  install_psql

  if ! command -v psql >/dev/null 2>&1; then
    add_psql_to_path_if_present || true
  fi

  if ! command -v psql >/dev/null 2>&1; then
    echo "psql is still not available after installation."
    echo "On macOS, you may need: export PATH=\"\$(brew --prefix libpq)/bin:\$PATH\""
    exit 1
  fi

  echo "Using psql at: $(command -v psql)"
}

ensure_psql

export PGPASSWORD="$DB_PASSWORD"

PSQL_ADMIN=(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1)
PSQL_DB=(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1)

echo "Installing database: $DB_NAME on $DB_HOST:$DB_PORT ..."

# Create the database if it does not already exist
DB_EXISTS="$("${PSQL_ADMIN[@]}" -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")"
if [[ "$DB_EXISTS" == "1" ]]; then
  echo "Database '$DB_NAME' already exists — skipping create."
else
  echo "Creating database '$DB_NAME' ..."
  "${PSQL_ADMIN[@]}" -c "CREATE DATABASE \"$DB_NAME\";"
fi

SQL_SCRIPTS=(
  sql/01_create_schema.sql
  sql/02_create_tables.sql
  sql/05_indexes.sql
)

for script in "${SQL_SCRIPTS[@]}"; do
  if [[ ! -f "$script" ]]; then
    echo "Missing SQL file: $script"
    exit 1
  fi
  echo "Applying $script ..."
  "${PSQL_DB[@]}" -f "$script"
done

echo "Database installation complete."
echo "Verify with: uv run python -m src.database.test_connection"
