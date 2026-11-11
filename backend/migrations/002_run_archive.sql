-- 研究受理归档：输入快照与幂等指纹。
-- 新库由 SQLAlchemy metadata 直接建表；本脚本用于已部署的 PostgreSQL 增量升级。
ALTER TABLE diversity_runs ADD COLUMN IF NOT EXISTS input_fingerprint VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS uq_diversity_runs_input_fingerprint
 ON diversity_runs(input_fingerprint);
CREATE TABLE IF NOT EXISTS run_archives (
 id SERIAL PRIMARY KEY,
 run_id INTEGER NOT NULL REFERENCES diversity_runs(id),
 input_fingerprint VARCHAR(64) NOT NULL,
 survey_snapshot JSON NOT NULL,
 transect_snapshot JSON NOT NULL,
 config_snapshot JSON NOT NULL,
 artifact_path VARCHAR(255),
 algorithm_version VARCHAR(80) NOT NULL DEFAULT 'individual-rarefaction-multinomial-v1',
 created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_run_archives_run_id ON run_archives(run_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_run_archive_fingerprint ON run_archives(input_fingerprint);
-- 历史研究没有归档：input_fingerprint 保持 NULL，重试端点明确拒绝复算。
