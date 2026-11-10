SELECT
    cod_propriedade_destino::text AS codigo_da_propriedade,
    MAX(estoque_destino)::integer AS estoque_destino,
    MAX(area_ha)::double precision AS area_ha,
    MAX(data_atualizacao_destino)::timestamp AS data_atualizacao_destino
FROM public.gta_deteccao_fraude
WHERE cod_propriedade_destino IS NOT NULL
GROUP BY cod_propriedade_destino::text;