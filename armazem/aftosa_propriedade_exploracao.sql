SELECT
    l.id_municipio AS codigo_do_municipio,
    m.nome AS descricao_do_municipio,
    l.codigo AS codigo_da_propriedade,
    l.nome AS nome_da_propriedade,
    p.nome AS nome_do_produtor_responsavel,
    p.cpf_cnpj AS cpf_cnpj_do_produtor,
    p.dt_atualizacao AS data_da_atualizacao_cadastral
FROM propriedade_produtores pp
LEFT JOIN produtores p
    ON p.id = pp.produtor_id
LEFT JOIN locais l
    ON l.sidagro_id_propriedade = pp.propriedade_id
LEFT JOIN municipios m
    ON m.id = l.id_municipio
WHERE l.codigo IS NOT NULL;