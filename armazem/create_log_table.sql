CREATE TABLE IF NOT EXISTS public.aftosa_logs_execucao (
    id BIGSERIAL PRIMARY KEY,

    usuario TEXT NOT NULL,

    sessao_inicio TIMESTAMP WITHOUT TIME ZONE,
    sessao_fim TIMESTAMP WITHOUT TIME ZONE,
    duracao_segundos INTEGER,

    seccional TEXT,
    coordenadoria TEXT,

    iteracoes_monte_carlo INTEGER,
    distribuicao TEXT,
    percentual_melhoria_distancia DOUBLE PRECISION,

    status_convergencia TEXT,

    tempo_montagem_matriz_ms INTEGER,
    tempo_solver_milp_ms INTEGER,

    configuracoes_cenario JSONB,
    pesos_risco JSONB,
    cenarios_relevantes JSONB,
    sensibilidade_unitaria JSONB,
    sensibilidade_componentes JSONB,
    risco_ajustado JSONB,
    performance_algoritmo JSONB,
    log_completo JSONB NOT NULL,

    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.aftosa_logs_execucao (
    id BIGSERIAL PRIMARY KEY,

    usuario TEXT NOT NULL,

    sessao_inicio TIMESTAMP WITHOUT TIME ZONE,
    sessao_fim TIMESTAMP WITHOUT TIME ZONE,
    duracao_segundos INTEGER,

    seccional TEXT,
    coordenadoria TEXT,

    iteracoes_monte_carlo INTEGER,
    distribuicao TEXT,
    percentual_melhoria_distancia DOUBLE PRECISION,

    status_convergencia TEXT,

    tempo_montagem_matriz_ms INTEGER,
    tempo_solver_milp_ms INTEGER,

    configuracoes_cenario JSONB,
    pesos_risco JSONB,
    cenarios_relevantes JSONB,
    sensibilidade_unitaria JSONB,
    sensibilidade_componentes JSONB,
    risco_ajustado JSONB,
    performance_algoritmo JSONB,
    log_completo JSONB NOT NULL,

    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aftosa_logs_usuario
ON public.aftosa_logs_execucao (usuario);

CREATE INDEX IF NOT EXISTS idx_aftosa_logs_sessao_inicio
ON public.aftosa_logs_execucao (sessao_inicio);

CREATE INDEX IF NOT EXISTS idx_aftosa_logs_seccional
ON public.aftosa_logs_execucao (seccional);

CREATE INDEX IF NOT EXISTS idx_aftosa_logs_coordenadoria
ON public.aftosa_logs_execucao (coordenadoria);

CREATE INDEX IF NOT EXISTS idx_aftosa_logs_log_completo_gin
ON public.aftosa_logs_execucao
USING GIN (log_completo);