-- Expose PostGIS geography as GeoJSON for the Next.js map API.
-- Run after 001_init.sql (+ seed).

create or replace view public.stops_geojson as
select
  id,
  name,
  landmark_notes,
  verification_status,
  last_verified_at,
  created_at,
  updated_at,
  ST_AsGeoJSON(geom::geometry)::json as geom_geojson
from public.stops;

create or replace view public.routes_geojson as
select
  id,
  name,
  code,
  transport_type,
  verification_status,
  last_verified_at,
  active,
  created_at,
  updated_at,
  case
    when geom is null then null
    else ST_AsGeoJSON(geom::geometry)::json
  end as geom_geojson
from public.routes;

-- Allow anon read for public map (tighten later with RLS policies as needed)
grant select on public.stops_geojson to anon, authenticated;
grant select on public.routes_geojson to anon, authenticated;
