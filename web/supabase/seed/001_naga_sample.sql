-- BIYAHERO Phase 1 — sample Naga City, Camarines Sur data
-- Run AFTER 001_init.sql. Safe to re-run (deletes prior seed ids first).

begin;

delete from public.route_stops where route_id in (
  'a1000000-0000-4000-8000-000000000001',
  'a1000000-0000-4000-8000-000000000002',
  'a1000000-0000-4000-8000-000000000003',
  'a1000000-0000-4000-8000-000000000004'
);
delete from public.transfers where id in (
  'c1000000-0000-4000-8000-000000000001',
  'c1000000-0000-4000-8000-000000000002',
  'c1000000-0000-4000-8000-000000000003',
  'c1000000-0000-4000-8000-000000000004'
);
delete from public.routes where id in (
  'a1000000-0000-4000-8000-000000000001',
  'a1000000-0000-4000-8000-000000000002',
  'a1000000-0000-4000-8000-000000000003',
  'a1000000-0000-4000-8000-000000000004'
);
delete from public.stops where id in (
  'b1000000-0000-4000-8000-000000000001',
  'b1000000-0000-4000-8000-000000000002',
  'b1000000-0000-4000-8000-000000000003',
  'b1000000-0000-4000-8000-000000000004',
  'b1000000-0000-4000-8000-000000000005',
  'b1000000-0000-4000-8000-000000000006',
  'b1000000-0000-4000-8000-000000000007',
  'b1000000-0000-4000-8000-000000000008'
);
delete from public.fare_rules where id in (
  'd1000000-0000-4000-8000-000000000001',
  'd1000000-0000-4000-8000-000000000002',
  'd1000000-0000-4000-8000-000000000003'
);
delete from public.discount_rules where id in (
  'e1000000-0000-4000-8000-000000000001',
  'e1000000-0000-4000-8000-000000000002',
  'e1000000-0000-4000-8000-000000000003'
);

-- Stops (lon lat for ST_MakePoint)
insert into public.stops (id, name, geom, landmark_notes, verification_status, last_verified_at) values
(
  'b1000000-0000-4000-8000-000000000001',
  'Naga Metropolitan Cathedral',
  ST_SetSRID(ST_MakePoint(123.1851, 13.6198), 4326)::geography,
  'Near Plaza Rizal / downtown core',
  'verified',
  '2026-10-01T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000002',
  'SM City Naga',
  ST_SetSRID(ST_MakePoint(123.2368, 13.6239), 4326)::geography,
  'Mall jeepney bay along CBD II',
  'verified',
  '2026-10-01T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000003',
  'Naga Central Bus Terminal',
  ST_SetSRID(ST_MakePoint(123.1949, 13.6262), 4326)::geography,
  'Main provincial bus / jeep hub',
  'verified',
  '2026-09-15T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000004',
  'Robinsons Place Naga',
  ST_SetSRID(ST_MakePoint(123.2002, 13.6241), 4326)::geography,
  'Along Roxas Avenue',
  'verified',
  '2026-09-15T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000005',
  'University of Nueva Caceres',
  ST_SetSRID(ST_MakePoint(123.1856, 13.6281), 4326)::geography,
  'UNC main gate, Elias Angeles St',
  'pending_verification',
  null
),
(
  'b1000000-0000-4000-8000-000000000006',
  'Magsaysay Avenue Junction',
  ST_SetSRID(ST_MakePoint(123.1904, 13.6212), 4326)::geography,
  'Busy transfer strip toward downtown',
  'verified',
  '2026-08-20T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000007',
  'Concepcion Pequeña Crossing',
  ST_SetSRID(ST_MakePoint(123.2055, 13.6108), 4326)::geography,
  'South corridor jeep stop',
  'potentially_outdated',
  '2025-11-01T00:00:00Z'
),
(
  'b1000000-0000-4000-8000-000000000008',
  'Camaligan Public Market',
  ST_SetSRID(ST_MakePoint(123.1702, 13.6305), 4326)::geography,
  'West of Naga toward Camaligan',
  'pending_verification',
  null
);

-- Routes with simplified LineStrings through stop order
insert into public.routes (
  id, name, code, transport_type, geom, verification_status, last_verified_at, active
) values
(
  'a1000000-0000-4000-8000-000000000001',
  'Cathedral – SM City Jeep',
  'NGA-01',
  'jeepney',
  ST_SetSRID(
    ST_MakeLine(ARRAY[
      ST_MakePoint(123.1851, 13.6198),
      ST_MakePoint(123.1904, 13.6212),
      ST_MakePoint(123.2002, 13.6241),
      ST_MakePoint(123.2368, 13.6239)
    ]),
    4326
  )::geography,
  'verified',
  '2026-10-01T00:00:00Z',
  true
),
(
  'a1000000-0000-4000-8000-000000000002',
  'Terminal – Robinsons – Concepcion',
  'NGA-02',
  'jeepney',
  ST_SetSRID(
    ST_MakeLine(ARRAY[
      ST_MakePoint(123.1949, 13.6262),
      ST_MakePoint(123.2002, 13.6241),
      ST_MakePoint(123.2055, 13.6108)
    ]),
    4326
  )::geography,
  'verified',
  '2026-09-15T00:00:00Z',
  true
),
(
  'a1000000-0000-4000-8000-000000000003',
  'UNC – Cathedral – Camaligan Tricycle',
  'NGA-TRI-01',
  'tricycle',
  ST_SetSRID(
    ST_MakeLine(ARRAY[
      ST_MakePoint(123.1856, 13.6281),
      ST_MakePoint(123.1851, 13.6198),
      ST_MakePoint(123.1702, 13.6305)
    ]),
    4326
  )::geography,
  'pending_verification',
  null,
  true
),
(
  'a1000000-0000-4000-8000-000000000004',
  'Terminal – SM Express Bus Shuttle',
  'NGA-BUS-01',
  'bus',
  ST_SetSRID(
    ST_MakeLine(ARRAY[
      ST_MakePoint(123.1949, 13.6262),
      ST_MakePoint(123.2002, 13.6241),
      ST_MakePoint(123.2368, 13.6239)
    ]),
    4326
  )::geography,
  'potentially_outdated',
  '2025-12-01T00:00:00Z',
  true
);

insert into public.route_stops (route_id, stop_id, sequence) values
-- NGA-01
('a1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000001', 1),
('a1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000006', 2),
('a1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000004', 3),
('a1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000002', 4),
-- NGA-02
('a1000000-0000-4000-8000-000000000002', 'b1000000-0000-4000-8000-000000000003', 1),
('a1000000-0000-4000-8000-000000000002', 'b1000000-0000-4000-8000-000000000004', 2),
('a1000000-0000-4000-8000-000000000002', 'b1000000-0000-4000-8000-000000000007', 3),
-- NGA-TRI-01
('a1000000-0000-4000-8000-000000000003', 'b1000000-0000-4000-8000-000000000005', 1),
('a1000000-0000-4000-8000-000000000003', 'b1000000-0000-4000-8000-000000000001', 2),
('a1000000-0000-4000-8000-000000000003', 'b1000000-0000-4000-8000-000000000008', 3),
-- NGA-BUS-01
('a1000000-0000-4000-8000-000000000004', 'b1000000-0000-4000-8000-000000000003', 1),
('a1000000-0000-4000-8000-000000000004', 'b1000000-0000-4000-8000-000000000004', 2),
('a1000000-0000-4000-8000-000000000004', 'b1000000-0000-4000-8000-000000000002', 3);

-- Walking transfers between nearby hubs
insert into public.transfers (
  id, from_stop_id, to_stop_id, walking_distance_m, estimated_walk_seconds
) values
(
  'c1000000-0000-4000-8000-000000000001',
  'b1000000-0000-4000-8000-000000000001',
  'b1000000-0000-4000-8000-000000000006',
  650, 480
),
(
  'c1000000-0000-4000-8000-000000000002',
  'b1000000-0000-4000-8000-000000000006',
  'b1000000-0000-4000-8000-000000000001',
  650, 480
),
(
  'c1000000-0000-4000-8000-000000000003',
  'b1000000-0000-4000-8000-000000000003',
  'b1000000-0000-4000-8000-000000000004',
  900, 660
),
(
  'c1000000-0000-4000-8000-000000000004',
  'b1000000-0000-4000-8000-000000000004',
  'b1000000-0000-4000-8000-000000000003',
  900, 660
);

-- Configurable fare matrix (illustrative Naga-style numbers for testing)
insert into public.fare_rules (
  id, transport_type, base_fare, per_km_rate, min_fare, currency, active, effective_from
) values
(
  'd1000000-0000-4000-8000-000000000001',
  'jeepney', 13.00, 1.80, 13.00, 'PHP', true, '2026-01-01T00:00:00Z'
),
(
  'd1000000-0000-4000-8000-000000000002',
  'tricycle', 20.00, 5.00, 20.00, 'PHP', true, '2026-01-01T00:00:00Z'
),
(
  'd1000000-0000-4000-8000-000000000003',
  'bus', 15.00, 2.20, 15.00, 'PHP', true, '2026-01-01T00:00:00Z'
);

-- Discount rows exist but are inactive until admin enables / validates scope
insert into public.discount_rules (
  id, type, percent, requires_validation, active, notes
) values
(
  'e1000000-0000-4000-8000-000000000001',
  'student', 20.00, true, false,
  'Enable only when student discount is in project scope'
),
(
  'e1000000-0000-4000-8000-000000000002',
  'senior', 20.00, true, false,
  'Enable only when senior discount is in project scope'
),
(
  'e1000000-0000-4000-8000-000000000003',
  'pwd', 20.00, true, false,
  'Enable only when PWD discount is in project scope'
);

commit;
