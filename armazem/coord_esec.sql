UPDATE public.aftosa_propriedade_exploracao ape
SET
    seccional = s.nome,
    coordenadoria = c.nome
FROM public.municipios m
JOIN public.unidades_administrativas ua
    ON ua.id = m.id_uad
JOIN public.seccionais s
    ON s.id = ua.id_seccional
JOIN public.coordenadorias c
    ON c.id = s.id_coordenadoria
WHERE ape.codigo_do_municipio::integer = m.id;