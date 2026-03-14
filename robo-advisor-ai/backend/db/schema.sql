-- RoboAdvisor AI — Supabase Schema
-- Run this in: Supabase Dashboard → SQL Editor → New Query → Paste → Run

-- ── Sessions ──
CREATE TABLE sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived'))
);

-- ── Messages (conversation history) ──
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);

-- ── Investment Profiles (parsed from user input) ──
CREATE TABLE investment_profiles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    capital NUMERIC NOT NULL,
    risk_tolerance INTEGER NOT NULL CHECK (risk_tolerance BETWEEN 1 AND 10),
    risk_category TEXT NOT NULL,
    horizon_years NUMERIC NOT NULL,
    sector_preferences JSONB DEFAULT '[]',
    constraints JSONB DEFAULT '[]',
    existing_holdings JSONB DEFAULT '{}',
    raw_input TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_session ON investment_profiles(session_id);

-- ── Research Cache (avoid redundant API calls) ──
CREATE TABLE research_cache (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    current_price NUMERIC,
    fundamentals JSONB DEFAULT '{}',
    technicals JSONB DEFAULT '{}',
    sentiment JSONB DEFAULT '{}',
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Deduplication handled in Python (check cache age before inserting)
CREATE INDEX idx_research_ticker ON research_cache(ticker, fetched_at DESC);

-- ── Strategies (BL optimizer output) ──
CREATE TABLE strategies (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    allocations JSONB NOT NULL,
    expected_annual_return NUMERIC,
    expected_volatility NUMERIC,
    sharpe_ratio NUMERIC,
    bl_params JSONB DEFAULT '{}',
    reasoning TEXT,
    tickers_researched JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_strategies_session ON strategies(session_id, created_at DESC);

-- ── Auto-update updated_at on sessions ──
CREATE OR REPLACE FUNCTION update_session_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sessions SET updated_at = NOW() WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_message_update
    AFTER INSERT ON messages
    FOR EACH ROW EXECUTE FUNCTION update_session_timestamp();

CREATE TRIGGER trigger_strategy_update
    AFTER INSERT ON strategies
    FOR EACH ROW EXECUTE FUNCTION update_session_timestamp();
