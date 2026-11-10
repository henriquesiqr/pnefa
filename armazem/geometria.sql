UPDATE public.aftosa_propriedade_exploracao ape
SET
    geometry = g.geom,
    latitude = ST_Y(ST_PointOnSurface(g.geom)),
    longitude = ST_X(ST_PointOnSurface(g.geom))
FROM public.locais l
INNER JOIN public.geometrias g
    ON g.id = l.id_geometria
WHERE ape.codigo_da_propriedade = l.codigo
  AND g.geom IS NOT NULL;