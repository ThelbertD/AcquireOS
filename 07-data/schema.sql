-- =====================================================================================
-- Outbound prospect pipeline — Postgres schema
--
-- Postgres 14 or later.
--
--   psql "$DATABASE_URL" -f schema.sql
--
-- Idempotent: safe to run repeatedly. Every object uses IF NOT EXISTS or is guarded.
--
-- Shape of the pipeline:
--
--   raw_import  ->  contact  ->  enrichment  ->  cadence_enrolment  ->  send_event
--       |                                                          \->  reply_event
--       \-> import_rejection                    suppression -------------^ (blocks)
--
-- Nothing is deleted on the way through. A row rejected at ingestion is written to
-- import_rejection with its reason and its original content, because "the list is smaller
-- than expected" is a question you will be asked and cannot answer from a silent drop.
-- =====================================================================================

-- citext gives case-insensitive email comparison at the type level rather than relying on
-- every query remembering to lower(). Requires privileges to create an extension.
CREATE EXTENSION IF NOT EXISTS citext;

-- =====================================================================================
-- Enumerated types
-- =====================================================================================

DO $$ BEGIN
    CREATE TYPE cadence_state AS ENUM (
        'pending',                -- enrolled, first node not yet sent
        'active',                 -- in the main sequence
        'interrupted',            -- in the follow-through branch
        'replied',                -- terminal
        'bounced',                -- terminal
        'unsubscribed',           -- terminal
        'completed-no-response'   -- terminal
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE consent_basis AS ENUM (
        'can-spam-optout',        -- US: no basis needed before first contact
        'legitimate-interest',    -- UK/EU: requires a documented balancing test
        'express-consent',        -- CASL and elsewhere
        'implied-consent'         -- CASL: has an expiry, which must be set
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE channel AS ENUM ('email', 'sms');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE suppression_reason AS ENUM (
        'unsubscribed',
        'hard-bounce',
        'complaint',
        'existing-customer',
        'competitor',
        'partner',
        'manual',
        'role-address',
        'no-lawful-basis',
        'data-subject-request'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE send_status AS ENUM (
        'queued', 'sent', 'delivered', 'soft-bounce', 'hard-bounce', 'blocked', 'skipped'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE reply_sentiment AS ENUM (
        'positive', 'neutral', 'not-interested', 'referral', 'unsubscribe-request',
        'auto-reply', 'unclassified'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================================
-- 1. Raw imports
--
-- Every row from every source file, exactly as it arrived. Never edited, never deleted.
-- This is the audit trail: when a contact turns out to have no lawful basis, or a batch
-- bounces at 9%, the question is always "where did this come from", and the answer has to
-- survive every transformation downstream.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS import_batch (
    id              BIGSERIAL PRIMARY KEY,
    source_name     TEXT        NOT NULL,
    source_detail   TEXT,
    file_name       TEXT,
    file_sha256     TEXT,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    imported_by     TEXT,
    row_count       INTEGER,
    accepted_count  INTEGER,
    rejected_count  INTEGER,
    jurisdiction    TEXT,
    consent_basis   consent_basis,
    consent_note    TEXT,
    verified        BOOLEAN     NOT NULL DEFAULT FALSE,
    verified_at     TIMESTAMPTZ,
    notes           TEXT,

    -- A batch cannot be marked verified without a date. "Verified" with no date is the
    -- claim that gets made in a hurry and cannot be checked later.
    CONSTRAINT import_batch_verified_has_date
        CHECK (verified = FALSE OR verified_at IS NOT NULL)
);

COMMENT ON TABLE import_batch IS
    'One row per source file loaded. The unit at which list quality is assessed and, when a '
    'batch turns out to be bad, the unit at which it is quarantined.';

CREATE TABLE IF NOT EXISTS raw_import (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        BIGINT      NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
    row_number      INTEGER     NOT NULL,
    payload         JSONB       NOT NULL,
    contact_id      BIGINT,     -- set once normalised; FK added after contact exists
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON COLUMN raw_import.payload IS
    'The source row as a JSON object, keys as they appeared in the file. Never normalised.';

CREATE INDEX IF NOT EXISTS raw_import_batch_idx      ON raw_import (batch_id);
CREATE INDEX IF NOT EXISTS raw_import_contact_idx    ON raw_import (contact_id);
CREATE INDEX IF NOT EXISTS raw_import_payload_gin    ON raw_import USING GIN (payload);

CREATE TABLE IF NOT EXISTS import_rejection (
    id              BIGSERIAL PRIMARY KEY,
    batch_id        BIGINT      NOT NULL REFERENCES import_batch(id) ON DELETE CASCADE,
    row_number      INTEGER     NOT NULL,
    payload         JSONB       NOT NULL,
    reason_code     TEXT        NOT NULL,
    reason_detail   TEXT,
    rejected_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE import_rejection IS
    'Every row that did not become a contact, with why. Nothing is dropped silently: a list '
    'that is smaller than expected must be explainable row by row.';

CREATE INDEX IF NOT EXISTS import_rejection_batch_idx  ON import_rejection (batch_id);
CREATE INDEX IF NOT EXISTS import_rejection_reason_idx ON import_rejection (reason_code);

-- =====================================================================================
-- 2. Accounts and contacts
-- =====================================================================================

CREATE TABLE IF NOT EXISTS account (
    id                  BIGSERIAL PRIMARY KEY,
    domain              CITEXT      NOT NULL UNIQUE,
    name                TEXT,
    employee_count      INTEGER,
    employee_band       TEXT,
    industry            TEXT,
    country             TEXT,
    region              TEXT,
    website             TEXT,
    enriched_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE account IS
    'One row per company, keyed on the email domain. Account-level attributes live here so '
    'segment routing and scoring do not have to be recomputed per contact.';

CREATE INDEX IF NOT EXISTS account_band_idx    ON account (employee_band);
CREATE INDEX IF NOT EXISTS account_country_idx ON account (country);

CREATE TABLE IF NOT EXISTS contact (
    id                  BIGSERIAL PRIMARY KEY,
    email               CITEXT      NOT NULL UNIQUE,
    email_domain        CITEXT      NOT NULL,
    account_id          BIGINT      REFERENCES account(id) ON DELETE SET NULL,

    first_name          TEXT,
    last_name           TEXT,
    full_name           TEXT,
    job_title           TEXT,
    seniority           TEXT,
    department          TEXT,
    phone               TEXT,
    linkedin_url        TEXT,
    country             TEXT,
    timezone            TEXT,

    -- Routing and scoring
    segment_value       TEXT,       -- the raw value the router reads
    lane                TEXT,       -- the lane assigned at enrolment; written once
    fit_score           SMALLINT,
    score_calculated_at TIMESTAMPTZ,

    -- Compliance. Not optional metadata: the entry gate reads these.
    jurisdiction        TEXT,
    consent_basis       consent_basis,
    consent_recorded_at TIMESTAMPTZ,
    consent_expires_at  TIMESTAMPTZ,
    consent_source      TEXT,
    sms_consent         BOOLEAN     NOT NULL DEFAULT FALSE,
    sms_consent_source  TEXT,
    lia_reference       TEXT,

    -- Provenance
    source_name         TEXT        NOT NULL,
    first_batch_id      BIGINT      REFERENCES import_batch(id) ON DELETE SET NULL,

    verified_at         TIMESTAMPTZ,
    verification_result TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_contacted_at   TIMESTAMPTZ,

    -- Implied consent under CASL expires. A row claiming implied consent with no expiry is
    -- a row that will still be claiming it in three years.
    CONSTRAINT contact_implied_consent_expires
        CHECK (consent_basis IS DISTINCT FROM 'implied-consent' OR consent_expires_at IS NOT NULL),

    -- Legitimate interest requires a documented balancing test. The reference is the proof
    -- that one exists.
    CONSTRAINT contact_legitimate_interest_has_lia
        CHECK (consent_basis IS DISTINCT FROM 'legitimate-interest' OR lia_reference IS NOT NULL),

    -- Score is a 0-100 scale. Anything else is a bug in the scorer, not a valid score.
    CONSTRAINT contact_score_range
        CHECK (fit_score IS NULL OR (fit_score >= 0 AND fit_score <= 100)),

    -- Cheap syntactic guard. Real validation happens in list_pipeline.py; this stops a
    -- direct INSERT from putting something unusable in the table.
    CONSTRAINT contact_email_shape
        CHECK (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')
);

COMMENT ON TABLE contact IS
    'The normalised contact. One row per email address, enforced by the unique constraint on '
    'email, which is CITEXT so case differences do not create duplicates.';

CREATE INDEX IF NOT EXISTS contact_account_idx     ON contact (account_id);
CREATE INDEX IF NOT EXISTS contact_domain_idx      ON contact (email_domain);
CREATE INDEX IF NOT EXISTS contact_lane_idx        ON contact (lane);
CREATE INDEX IF NOT EXISTS contact_source_idx      ON contact (source_name);
CREATE INDEX IF NOT EXISTS contact_score_idx       ON contact (fit_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS contact_jurisdiction_idx ON contact (jurisdiction);

-- Contacts whose implied consent has expired, or expires soon. This is a query that has to
-- run before every send, so it gets its own index.
CREATE INDEX IF NOT EXISTS contact_consent_expiry_idx
    ON contact (consent_expires_at)
    WHERE consent_expires_at IS NOT NULL;

-- Now that contact exists, close the loop from raw_import.
DO $$ BEGIN
    ALTER TABLE raw_import
        ADD CONSTRAINT raw_import_contact_fk
        FOREIGN KEY (contact_id) REFERENCES contact(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================================
-- 3. Enrichment
--
-- Append-only. Each run writes a new row rather than overwriting, so a scoring change can
-- be explained by comparing the enrichment that produced it against the one before.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS enrichment (
    id              BIGSERIAL PRIMARY KEY,
    contact_id      BIGINT      NOT NULL REFERENCES contact(id) ON DELETE CASCADE,
    provider        TEXT        NOT NULL,
    provider_ref    TEXT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'pending',
    fields          JSONB       NOT NULL DEFAULT '{}'::JSONB,
    confidence      NUMERIC(4,3),
    cost_credits    NUMERIC(10,4),
    error_detail    TEXT,

    CONSTRAINT enrichment_confidence_range
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

COMMENT ON TABLE enrichment IS
    'Append-only enrichment results, one row per provider call. Never overwritten, so the '
    'input to any score can be reconstructed.';

CREATE INDEX IF NOT EXISTS enrichment_contact_idx  ON enrichment (contact_id);
CREATE INDEX IF NOT EXISTS enrichment_provider_idx ON enrichment (provider, requested_at DESC);
CREATE INDEX IF NOT EXISTS enrichment_fields_gin   ON enrichment USING GIN (fields);

CREATE TABLE IF NOT EXISTS score_run (
    id              BIGSERIAL PRIMARY KEY,
    contact_id      BIGINT      NOT NULL REFERENCES contact(id) ON DELETE CASCADE,
    enrichment_id   BIGINT      REFERENCES enrichment(id) ON DELETE SET NULL,
    rubric_version  TEXT        NOT NULL,
    score           SMALLINT    NOT NULL,
    components      JSONB       NOT NULL DEFAULT '{}'::JSONB,
    threshold       SMALLINT    NOT NULL,
    passed          BOOLEAN     NOT NULL,
    scored_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT score_run_range CHECK (score >= 0 AND score <= 100)
);

COMMENT ON TABLE score_run IS
    'Every scoring decision, with the rubric version and the per-component breakdown. Makes '
    '"why was this contact excluded" answerable without rerunning anything.';

CREATE INDEX IF NOT EXISTS score_run_contact_idx ON score_run (contact_id, scored_at DESC);

-- =====================================================================================
-- 4. Suppression
--
-- The most important table here. Everything else can be rebuilt from source files; this
-- cannot, and losing it means contacting people who told you not to.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS suppression (
    id              BIGSERIAL PRIMARY KEY,
    email           CITEXT      UNIQUE,
    email_domain    CITEXT,
    reason          suppression_reason NOT NULL,
    reason_detail   TEXT,
    channel         channel,     -- NULL means every channel
    source          TEXT,
    suppressed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    suppressed_by   TEXT,
    permanent       BOOLEAN     NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ,

    -- Either an address or a whole domain, not neither.
    CONSTRAINT suppression_target_present
        CHECK (email IS NOT NULL OR email_domain IS NOT NULL),

    -- Permanent means permanent. An expiry on a permanent suppression is a contradiction
    -- that becomes a compliance breach the day it expires.
    CONSTRAINT suppression_permanent_never_expires
        CHECK (permanent = FALSE OR expires_at IS NULL)
);

COMMENT ON TABLE suppression IS
    'Addresses and domains that must never be sent to. Checked at send time, not at '
    'enrolment time. Survives every other table; back it up separately.';

COMMENT ON COLUMN suppression.channel IS
    'NULL suppresses every channel, which is the correct default. A prospect who says stop '
    'has said stop, not "stop on email only".';

CREATE UNIQUE INDEX IF NOT EXISTS suppression_domain_uniq
    ON suppression (email_domain)
    WHERE email IS NULL AND email_domain IS NOT NULL;

CREATE INDEX IF NOT EXISTS suppression_domain_idx  ON suppression (email_domain);
CREATE INDEX IF NOT EXISTS suppression_reason_idx  ON suppression (reason);
CREATE INDEX IF NOT EXISTS suppression_expiry_idx
    ON suppression (expires_at) WHERE expires_at IS NOT NULL;

-- A single lookup covering both address-level and domain-level suppression.
CREATE OR REPLACE VIEW active_suppression AS
    SELECT email, email_domain, reason, channel, suppressed_at
      FROM suppression
     WHERE permanent = TRUE
        OR expires_at IS NULL
        OR expires_at > now();

COMMENT ON VIEW active_suppression IS
    'Suppressions currently in force. Query this, not the base table, at send time.';

-- =====================================================================================
-- 5. Cadences and enrolment
--
-- The constraint that prevents one contact entering two active cadences lives here. It is
-- a partial unique index rather than application logic, because application logic is what
-- was supposed to prevent it in every system where it happened anyway.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS cadence (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT        NOT NULL UNIQUE,
    segment_field   TEXT,
    length_days     SMALLINT,
    channels        TEXT[]      NOT NULL DEFAULT ARRAY['email'],
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cadence_node (
    id              BIGSERIAL PRIMARY KEY,
    cadence_id      BIGINT      NOT NULL REFERENCES cadence(id) ON DELETE CASCADE,
    node_key        TEXT        NOT NULL,   -- N1, N2, F1 ...
    lane            TEXT,                   -- NULL for follow-through nodes, shared across lanes
    day_offset      SMALLINT    NOT NULL,
    channel         channel     NOT NULL,
    purpose         TEXT,
    is_followthrough BOOLEAN    NOT NULL DEFAULT FALSE,

    UNIQUE (cadence_id, node_key, lane)
);

CREATE INDEX IF NOT EXISTS cadence_node_cadence_idx ON cadence_node (cadence_id, day_offset);

CREATE TABLE IF NOT EXISTS cadence_enrolment (
    id                  BIGSERIAL PRIMARY KEY,
    contact_id          BIGINT      NOT NULL REFERENCES contact(id) ON DELETE CASCADE,
    cadence_id          BIGINT      NOT NULL REFERENCES cadence(id) ON DELETE CASCADE,
    lane                TEXT        NOT NULL,
    state               cadence_state NOT NULL DEFAULT 'pending',
    current_node        TEXT,
    enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    entered_state_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,

    interrupt_trigger   TEXT,
    interrupt_at        TIMESTAMPTZ,
    interrupt_pending_node TEXT,

    reentry_count       SMALLINT    NOT NULL DEFAULT 0,
    previous_enrolment_id BIGINT    REFERENCES cadence_enrolment(id) ON DELETE SET NULL,

    -- Re-entry is capped at one, ever. See cadence-spec.md, re-entry rules.
    CONSTRAINT enrolment_reentry_cap CHECK (reentry_count >= 0 AND reentry_count <= 1),

    -- A terminal state must have a completion timestamp. Without this, "when did this
    -- contact finish" is unanswerable and every funnel metric is approximate.
    CONSTRAINT enrolment_terminal_has_completed_at
        CHECK (
            state IN ('pending', 'active', 'interrupted')
            OR completed_at IS NOT NULL
        ),

    -- An interrupted enrolment records what interrupted it.
    CONSTRAINT enrolment_interrupted_has_trigger
        CHECK (state <> 'interrupted' OR interrupt_trigger IS NOT NULL)
);

COMMENT ON TABLE cadence_enrolment IS
    'One row per contact per cadence entry. The partial unique index below is what actually '
    'prevents a contact being in two active cadences at once.';

-- ---------------------------------------------------------------------------------------
-- THE CONSTRAINT.
--
-- A contact may have many enrolments over time, but at most one that is not terminal. A
-- prospect receiving two unrelated cold sequences from the same company complains at
-- several times the base rate, and it is invariably caused by two enrolments nobody
-- noticed rather than by a decision anyone made.
--
-- Enforced in the database because every system where this happened had application logic
-- that was supposed to prevent it.
-- ---------------------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS enrolment_one_active_per_contact
    ON cadence_enrolment (contact_id)
    WHERE state IN ('pending', 'active', 'interrupted');

CREATE INDEX IF NOT EXISTS enrolment_cadence_idx ON cadence_enrolment (cadence_id, state);
CREATE INDEX IF NOT EXISTS enrolment_state_idx   ON cadence_enrolment (state, entered_state_at);
CREATE INDEX IF NOT EXISTS enrolment_lane_idx    ON cadence_enrolment (cadence_id, lane, state);

-- =====================================================================================
-- 6. Send events
--
-- Every attempt, including the ones that were skipped and the ones that failed. The
-- columns here are exactly the dimensions the cadence spec requires to be analysable:
-- node, lane, sending domain, source batch, channel.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS send_event (
    id                  BIGSERIAL PRIMARY KEY,
    contact_id          BIGINT      NOT NULL REFERENCES contact(id) ON DELETE CASCADE,
    enrolment_id        BIGINT      REFERENCES cadence_enrolment(id) ON DELETE SET NULL,
    cadence_id          BIGINT      REFERENCES cadence(id) ON DELETE SET NULL,

    node_key            TEXT        NOT NULL,
    lane                TEXT,
    channel             channel     NOT NULL,
    variant             TEXT,       -- which copy variant, for A/B analysis

    sending_domain      CITEXT,
    sending_mailbox     CITEXT,
    source_name         TEXT,

    status              send_status NOT NULL,
    status_detail       TEXT,
    skip_reason         TEXT,       -- why a node did not send: no sms_consent, suppressed, ...

    queued_at           TIMESTAMPTZ,
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    message_id          TEXT,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- A skipped send records why. A skip with no reason is indistinguishable from a bug.
    CONSTRAINT send_event_skip_has_reason
        CHECK (status <> 'skipped' OR skip_reason IS NOT NULL)
);

COMMENT ON TABLE send_event IS
    'Every send attempt, including skips and failures. The dimension columns (node, lane, '
    'sending_domain, source_name, channel) are what make the programme analysable at all.';

CREATE INDEX IF NOT EXISTS send_event_contact_idx  ON send_event (contact_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS send_event_node_idx     ON send_event (cadence_id, node_key, lane);
CREATE INDEX IF NOT EXISTS send_event_domain_idx   ON send_event (sending_domain, sent_at DESC);
CREATE INDEX IF NOT EXISTS send_event_mailbox_idx  ON send_event (sending_mailbox, sent_at DESC);
CREATE INDEX IF NOT EXISTS send_event_status_idx   ON send_event (status, sent_at DESC);
CREATE INDEX IF NOT EXISTS send_event_source_idx   ON send_event (source_name, status);
CREATE INDEX IF NOT EXISTS send_event_variant_idx
    ON send_event (cadence_id, node_key, variant) WHERE variant IS NOT NULL;

-- Per-mailbox daily volume, which is the unit the sending ceiling is expressed in. Indexed
-- on the raw timestamp rather than a cast to date: casting timestamptz to date depends on
-- the session timezone and is not immutable, so it cannot be indexed.
CREATE INDEX IF NOT EXISTS send_event_mailbox_day_idx
    ON send_event (sending_mailbox, sent_at)
    WHERE status IN ('sent', 'delivered');

-- =====================================================================================
-- 7. Reply events
-- =====================================================================================

CREATE TABLE IF NOT EXISTS reply_event (
    id                  BIGSERIAL PRIMARY KEY,
    contact_id          BIGINT      NOT NULL REFERENCES contact(id) ON DELETE CASCADE,
    enrolment_id        BIGINT      REFERENCES cadence_enrolment(id) ON DELETE SET NULL,
    send_event_id       BIGINT      REFERENCES send_event(id) ON DELETE SET NULL,

    -- Denormalised from the send event so a reply is analysable even when the originating
    -- send cannot be matched, which happens whenever a prospect replies from a different
    -- address or forwards to a colleague.
    node_key            TEXT,
    lane                TEXT,
    channel             channel     NOT NULL,
    sending_domain      CITEXT,

    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    from_address        CITEXT,
    is_auto_reply       BOOLEAN     NOT NULL DEFAULT FALSE,
    sentiment           reply_sentiment NOT NULL DEFAULT 'unclassified',
    classified_at       TIMESTAMPTZ,
    classified_by       TEXT,
    triggered_interrupt BOOLEAN     NOT NULL DEFAULT FALSE,
    body_excerpt        TEXT,
    notes               TEXT,

    -- An auto-reply must never have fired the interrupt. Out-of-office cancelling a
    -- sequence and notifying a human for nothing is a specific, common bug, and this makes
    -- it impossible to record without noticing.
    CONSTRAINT reply_auto_does_not_interrupt
        CHECK (is_auto_reply = FALSE OR triggered_interrupt = FALSE)
);

COMMENT ON TABLE reply_event IS
    'Every inbound message matched to a contact, including auto-replies, which are recorded '
    'but must never fire the interrupt.';

CREATE INDEX IF NOT EXISTS reply_event_contact_idx   ON reply_event (contact_id, received_at DESC);
CREATE INDEX IF NOT EXISTS reply_event_node_idx      ON reply_event (node_key, lane);
CREATE INDEX IF NOT EXISTS reply_event_sentiment_idx ON reply_event (sentiment, received_at DESC);
CREATE INDEX IF NOT EXISTS reply_event_domain_idx    ON reply_event (sending_domain, received_at DESC);

-- =====================================================================================
-- 8. Bounce events
--
-- Separate from send_event status because a bounce arrives asynchronously, sometimes days
-- later, and a block response is a domain-level event that must not be recorded as a
-- contact-level failure.
-- =====================================================================================

CREATE TABLE IF NOT EXISTS bounce_event (
    id                  BIGSERIAL PRIMARY KEY,
    contact_id          BIGINT      REFERENCES contact(id) ON DELETE CASCADE,
    send_event_id       BIGINT      REFERENCES send_event(id) ON DELETE SET NULL,
    sending_domain      CITEXT,
    sending_mailbox     CITEXT,
    source_name         TEXT,
    bounce_type         TEXT        NOT NULL,   -- hard | soft | block
    smtp_code           TEXT,
    diagnostic          TEXT,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT bounce_type_known CHECK (bounce_type IN ('hard', 'soft', 'block'))
);

COMMENT ON COLUMN bounce_event.bounce_type IS
    'hard: suppress the contact permanently. soft: retry, 3 in 7 days becomes hard. '
    'block: the receiving server refused the message - a sending-domain problem, not a '
    'contact problem. Never suppress a contact for a block.';

CREATE INDEX IF NOT EXISTS bounce_event_contact_idx ON bounce_event (contact_id, received_at DESC);
CREATE INDEX IF NOT EXISTS bounce_event_domain_idx  ON bounce_event (sending_domain, received_at DESC);
CREATE INDEX IF NOT EXISTS bounce_event_source_idx  ON bounce_event (source_name, bounce_type);
CREATE INDEX IF NOT EXISTS bounce_event_type_idx    ON bounce_event (bounce_type, received_at DESC);

-- =====================================================================================
-- 9. Operational views
--
-- The questions asked most often, and the ones that catch problems early.
-- =====================================================================================

-- Contacts eligible to be enrolled: not suppressed, scored above threshold, with a lawful
-- basis that has not expired, and not already in an active cadence.
CREATE OR REPLACE VIEW eligible_contact AS
    SELECT c.*
      FROM contact c
     WHERE NOT EXISTS (
               SELECT 1 FROM active_suppression s
                WHERE s.email = c.email
                   OR (s.email IS NULL AND s.email_domain = c.email_domain)
           )
       AND NOT EXISTS (
               SELECT 1 FROM cadence_enrolment e
                WHERE e.contact_id = c.id
                  AND e.state IN ('pending', 'active', 'interrupted')
           )
       AND c.consent_basis IS NOT NULL
       AND (c.consent_expires_at IS NULL OR c.consent_expires_at > now());

COMMENT ON VIEW eligible_contact IS
    'Contacts that pass gates G1, G2 and G4. G3, the fit score threshold, is applied by the '
    'caller because the threshold is per-client.';

-- Deliverability by sending domain over the last 30 days. The first thing to look at when
-- something is wrong.
CREATE OR REPLACE VIEW domain_health_30d AS
    SELECT
        se.sending_domain,
        COUNT(*) FILTER (WHERE se.status IN ('sent', 'delivered'))       AS sent,
        COUNT(*) FILTER (WHERE se.status = 'hard-bounce')                AS hard_bounces,
        COUNT(*) FILTER (WHERE se.status = 'soft-bounce')                AS soft_bounces,
        COUNT(*) FILTER (WHERE se.status = 'blocked')                    AS blocked,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE se.status = 'hard-bounce')
            / NULLIF(COUNT(*) FILTER (WHERE se.status IN ('sent', 'delivered', 'hard-bounce')), 0),
            2
        ) AS hard_bounce_pct
      FROM send_event se
     WHERE se.sent_at > now() - INTERVAL '30 days'
     GROUP BY se.sending_domain;

-- Reply rate by node and lane. Which node earns its place.
CREATE OR REPLACE VIEW node_performance AS
    SELECT
        se.cadence_id,
        se.node_key,
        se.lane,
        se.variant,
        COUNT(DISTINCT se.id) FILTER (WHERE se.status IN ('sent', 'delivered')) AS sent,
        COUNT(DISTINCT re.id) FILTER (WHERE re.is_auto_reply = FALSE)           AS replies,
        ROUND(
            100.0 * COUNT(DISTINCT re.id) FILTER (WHERE re.is_auto_reply = FALSE)
            / NULLIF(COUNT(DISTINCT se.id) FILTER (WHERE se.status IN ('sent', 'delivered')), 0),
            2
        ) AS reply_pct
      FROM send_event se
      LEFT JOIN reply_event re ON re.send_event_id = se.id
     GROUP BY se.cadence_id, se.node_key, se.lane, se.variant;

-- Bounce rate by source batch. Which import was not verified.
CREATE OR REPLACE VIEW source_quality AS
    SELECT
        se.source_name,
        COUNT(*) FILTER (WHERE se.status IN ('sent', 'delivered')) AS sent,
        COUNT(*) FILTER (WHERE se.status = 'hard-bounce')          AS hard_bounces,
        ROUND(
            100.0 * COUNT(*) FILTER (WHERE se.status = 'hard-bounce')
            / NULLIF(COUNT(*) FILTER (WHERE se.status IN ('sent', 'delivered', 'hard-bounce')), 0),
            2
        ) AS hard_bounce_pct
      FROM send_event se
     GROUP BY se.source_name;

-- The canary. Enrolments that are active but have nothing scheduled and nothing recent are
-- stuck: a branch condition matched nothing and the contact fell out of the flow. The
-- correct result is zero rows, every time. Run it weekly.
CREATE OR REPLACE VIEW stuck_enrolment AS
    SELECT
        e.id,
        e.contact_id,
        e.cadence_id,
        e.lane,
        e.state,
        e.current_node,
        e.entered_state_at,
        now() - e.entered_state_at AS stuck_for
      FROM cadence_enrolment e
     WHERE e.state IN ('pending', 'active', 'interrupted')
       AND e.entered_state_at < now() - INTERVAL '14 days';

COMMENT ON VIEW stuck_enrolment IS
    'Enrolments sitting in a non-terminal state for longer than any cadence runs. Should '
    'always be empty; anything here is a branch that matched nothing.';

-- Contacts whose lawful basis has expired or expires within 30 days.
CREATE OR REPLACE VIEW consent_expiring AS
    SELECT id, email, jurisdiction, consent_basis, consent_expires_at,
           (consent_expires_at <= now()) AS already_expired
      FROM contact
     WHERE consent_expires_at IS NOT NULL
       AND consent_expires_at <= now() + INTERVAL '30 days'
     ORDER BY consent_expires_at;

-- Contacts past the retention period, which must be deleted rather than merely stopped.
CREATE OR REPLACE VIEW retention_due AS
    SELECT id, email, source_name, created_at, last_contacted_at
      FROM contact
     WHERE COALESCE(last_contacted_at, created_at) < now() - INTERVAL '730 days';

COMMENT ON VIEW retention_due IS
    'Contacts past the default retention window. Replace 730 with the client''s '
    '{{DATA_RETENTION_DAYS}} value. Deletion is an obligation, not housekeeping.';

-- =====================================================================================
-- 10. updated_at maintenance
-- =====================================================================================

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER contact_touch_updated_at
        BEFORE UPDATE ON contact
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TRIGGER account_touch_updated_at
        BEFORE UPDATE ON account
        FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================================
-- Notes for whoever operates this
--
-- 1. Back up `suppression` separately and more often than everything else. Every other
--    table can be rebuilt from source files and platform exports. This one cannot, and
--    losing it means contacting people who told you not to.
--
-- 2. `stuck_enrolment` should return zero rows. Check it weekly. It is the cheapest
--    detector for a branch that matched nothing, which is the most common cadence bug and
--    the one that produces no error.
--
-- 3. `enrolment_one_active_per_contact` will reject a second enrolment. That rejection is
--    the constraint working. Handle it in the application; do not drop the index.
--
-- 4. Replace the 730-day interval in `retention_due` with the client's
--    {{DATA_RETENTION_DAYS}}.
--
-- 5. Nothing here stores message bodies beyond `reply_event.body_excerpt`. Keep it short,
--    and treat it as personal data subject to the same retention rules as everything else.
-- =====================================================================================
