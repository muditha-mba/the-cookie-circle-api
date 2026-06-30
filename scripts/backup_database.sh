#!/usr/bin/env bash
# Create a PostgreSQL logical backup (pg_dump custom format) and optionally upload to S3.
#
# Layer 2 (nightly): GitHub Actions calls this with --prefix production/daily
# Layer 3 (manual):   run before migrations with --prefix production/manual
#
# Examples:
#   export DATABASE_URL="postgresql+psycopg://..."
#   ./scripts/backup_database.sh --prefix production/manual
#
#   ./scripts/backup_database.sh \
#     --database-url "$DATABASE_URL" \
#     --prefix production/daily \
#     --bucket the-cookie-circle-db-backups

set -euo pipefail

PREFIX="production/daily"
BUCKET="${S3_BACKUP_BUCKET:-the-cookie-circle-db-backups}"
DATABASE_URL_INPUT="${DATABASE_URL:-}"
LOCAL_ONLY=false
LABEL="production"

usage() {
  cat <<'EOF'
Usage: backup_database.sh [options]

Options:
  --database-url URL   Neon connection string (default: DATABASE_URL env)
  --prefix PATH        S3 key prefix, e.g. production/daily or production/manual
  --bucket NAME        S3 bucket (default: S3_BACKUP_BUCKET or the-cookie-circle-db-backups)
  --label NAME         Filename label (default: production)
  --local-only         Write dump locally only; do not upload to S3
  -h, --help           Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --database-url)
      DATABASE_URL_INPUT="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    --bucket)
      BUCKET="$2"
      shift 2
      ;;
    --label)
      LABEL="$2"
      shift 2
      ;;
    --local-only)
      LOCAL_ONLY=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$DATABASE_URL_INPUT" ]]; then
  echo "DATABASE_URL is required (env or --database-url)." >&2
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump not found. Install PostgreSQL client tools." >&2
  exit 1
fi

# pg_dump expects postgresql://, not SQLAlchemy's postgresql+psycopg://
PG_URL="${DATABASE_URL_INPUT/postgresql+psycopg/postgresql}"

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
FILENAME="cookie_circle_${LABEL}_${TIMESTAMP}.dump"
WORKDIR="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
DUMP_PATH="${WORKDIR}/${FILENAME}"

echo "Creating backup: ${DUMP_PATH}"
pg_dump "$PG_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="$DUMP_PATH"

DUMP_BYTES="$(wc -c <"$DUMP_PATH" | tr -d ' ')"
echo "Backup size: ${DUMP_BYTES} bytes"

if [[ "$LOCAL_ONLY" == true ]]; then
  echo "Local backup complete: ${DUMP_PATH}"
  exit 0
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI not found. Re-run with --local-only or install AWS CLI." >&2
  exit 1
fi

S3_KEY="${PREFIX}/${FILENAME}"
S3_URI="s3://${BUCKET}/${S3_KEY}"

echo "Uploading to ${S3_URI}"
aws s3 cp "$DUMP_PATH" "$S3_URI" \
  --only-show-errors \
  --sse AES256

echo "Upload complete: ${S3_URI}"
