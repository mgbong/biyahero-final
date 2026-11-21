"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { Feature, FeatureCollection, LineString, Point } from "geojson";
import type { Map as LeafletMap, Path, LayerGroup } from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  RouteFeatureProps,
  StopFeatureProps,
} from "@/lib/geo/naga-seed";
import { NAGA_CENTER } from "@/lib/geo/naga-seed";
import {
  verificationBadgeClass,
  verificationLabel,
} from "@/lib/geo/verification";

type NetworkPayload = {
  ok: boolean;
  source: "supabase" | "seed";
  stops: FeatureCollection<Point, StopFeatureProps>;
  routes: FeatureCollection<LineString, RouteFeatureProps>;
};

const ROUTE_COLORS: Record<string, string> = {
  jeepney: "#ff7a00",
  tricycle: "#0d9488",
  bus: "#2563eb",
  walk_link: "#64748b",
};

function formatVerifiedAt(iso: string | null): string {
  if (!iso) return "Not verified yet";
  try {
    return new Date(iso).toLocaleDateString("en-PH", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function TransitMap() {
  const mapId = useId().replace(/:/g, "");
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const [data, setData] = useState<NetworkPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedStop, setSelectedStop] = useState<StopFeatureProps | null>(
    null
  );
  const [selectedRoute, setSelectedRoute] = useState<RouteFeatureProps | null>(
    null
  );
  const [highlightedRouteId, setHighlightedRouteId] = useState<string | null>(
    null
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/geo/network");
        const json = (await res.json()) as NetworkPayload;
        if (!cancelled) {
          if (!json.ok) throw new Error("Bad geo response");
          setData(json);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Could not load map data");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const routeLegend = useMemo(() => {
    if (!data) return [];
    return data.routes.features.map((f) => f.properties);
  }, [data]);

  useEffect(() => {
    if (!containerRef.current || !data || mapRef.current) return;

    let cancelled = false;

    (async () => {
      const L = (await import("leaflet")).default;

      if (cancelled || !containerRef.current) return;

      const map = L.map(containerRef.current, {
        center: NAGA_CENTER,
        zoom: 13,
        scrollWheelZoom: true,
      });
      mapRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      const routeLayerById = new Map<string, LayerGroup>();

      data.routes.features.forEach((feature) => {
        const props = feature.properties;
        const color = ROUTE_COLORS[props.transport_type] ?? "#ff7a00";
        const layer = L.geoJSON(feature as Feature, {
          style: {
            color,
            weight: 5,
            opacity: 0.85,
          },
          onEachFeature: (_f, lyr) => {
            lyr.on("click", () => {
              setSelectedRoute(props);
              setSelectedStop(null);
              setHighlightedRouteId(props.id);
            });
            lyr.bindTooltip(`${props.code ?? ""} ${props.name}`.trim(), {
              sticky: true,
            });
          },
        }).addTo(map);
        routeLayerById.set(props.id, layer);
      });

      const stopLayer = L.geoJSON(data.stops as FeatureCollection, {
        pointToLayer: (_feature, latlng) =>
          L.circleMarker(latlng, {
            radius: 8,
            color: "#0d0c22",
            weight: 2,
            fillColor: "#ffffff",
            fillOpacity: 1,
          }),
        onEachFeature: (feature, lyr) => {
          const props = feature.properties as StopFeatureProps;
          lyr.on("click", () => {
            setSelectedStop(props);
            setSelectedRoute(null);
          });
          lyr.bindTooltip(props.name);
        },
      }).addTo(map);

      const bounds = stopLayer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.2));
      }

      (
        map as LeafletMap & { __routeLayers?: Map<string, LayerGroup> }
      ).__routeLayers = routeLayerById;
    })();

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [data]);

  useEffect(() => {
    const map = mapRef.current as
      | (LeafletMap & { __routeLayers?: Map<string, LayerGroup> })
      | null;
    if (!map?.__routeLayers) return;

    map.__routeLayers.forEach((layer, id) => {
      const active = highlightedRouteId === id;
      const style = {
        weight: active ? 8 : 5,
        opacity: active ? 1 : highlightedRouteId ? 0.35 : 0.85,
      };
      layer.eachLayer((sub) => {
        (sub as Path).setStyle?.(style);
      });
    });
  }, [highlightedRouteId]);

  return (
    <div className="flex w-full max-w-5xl flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text)]">
            Naga routes &amp; stops
          </h1>
          <p className="mt-1 text-sm text-[var(--color-muted)]">
            Tap a line or stop for details. Badges show verification status.
          </p>
        </div>
        {data && (
          <p className="rounded-full bg-[var(--color-accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--color-accent)]">
            Data: {data.source === "seed" ? "local seed" : "Supabase"}
          </p>
        )}
      </div>

      {error && (
        <p className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
          {error}
        </p>
      )}

      <div
        ref={containerRef}
        id={`map-${mapId}`}
        className="h-[min(70vh,560px)] w-full overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[#e8eef0]"
        role="application"
        aria-label="Interactive map of Naga City transit routes and stops"
      />

      <div className="flex flex-wrap gap-4">
        <aside
          className="min-w-[220px] flex-1 rounded-2xl bg-[var(--color-surface)] p-4"
          aria-label="Route list"
        >
          <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
            Routes
          </h2>
          <ul className="mt-3 flex flex-col gap-2">
            {routeLegend.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  className="flex w-full flex-wrap items-center gap-2 rounded-xl border border-transparent px-2 py-2 text-left text-sm hover:border-[var(--color-border)] hover:bg-[var(--color-page)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-accent)]"
                  onClick={() => {
                    setHighlightedRouteId(r.id);
                    setSelectedRoute(r);
                    setSelectedStop(null);
                  }}
                >
                  <span
                    className="inline-block h-2 w-6 rounded-full"
                    style={{
                      background: ROUTE_COLORS[r.transport_type] ?? "#ff7a00",
                    }}
                    aria-hidden
                  />
                  <span className="font-semibold">{r.code}</span>
                  <span className="text-[var(--color-muted)]">{r.name}</span>
                  <span
                    className={`ml-auto rounded-full px-2 py-0.5 text-[10px] font-bold ${verificationBadgeClass(r.verification_status)}`}
                  >
                    {verificationLabel(r.verification_status)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <aside
          className="min-w-[220px] flex-1 rounded-2xl bg-[var(--color-surface)] p-4"
          aria-live="polite"
          aria-label="Selection details"
        >
          <h2 className="text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
            Details
          </h2>
          {!selectedStop && !selectedRoute && (
            <p className="mt-3 text-sm text-[var(--color-muted)]">
              Select a stop marker or route line.
            </p>
          )}
          {selectedStop && (
            <div className="mt-3 flex flex-col gap-2 text-sm">
              <p className="text-lg font-bold">{selectedStop.name}</p>
              <span
                className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-bold ${verificationBadgeClass(selectedStop.verification_status)}`}
              >
                {verificationLabel(selectedStop.verification_status)}
              </span>
              <p className="text-[var(--color-muted)]">
                Last verified: {formatVerifiedAt(selectedStop.last_verified_at)}
              </p>
              {selectedStop.landmark_notes && (
                <p>{selectedStop.landmark_notes}</p>
              )}
            </div>
          )}
          {selectedRoute && (
            <div className="mt-3 flex flex-col gap-2 text-sm">
              <p className="text-lg font-bold">
                {selectedRoute.code} · {selectedRoute.name}
              </p>
              <p className="capitalize text-[var(--color-muted)]">
                {selectedRoute.transport_type.replace("_", " ")}
              </p>
              <span
                className={`w-fit rounded-full px-2 py-0.5 text-[10px] font-bold ${verificationBadgeClass(selectedRoute.verification_status)}`}
              >
                {verificationLabel(selectedRoute.verification_status)}
              </span>
              <p className="text-[var(--color-muted)]">
                Last verified:{" "}
                {formatVerifiedAt(selectedRoute.last_verified_at)}
              </p>
            </div>
          )}
        </aside>
      </div>

      <p className="text-xs text-[var(--color-muted)]">
        Map tiles: OpenStreetMap. Boarding / drop-off / transfer markers for
        itineraries come in Phase 3–4.
      </p>
    </div>
  );
}
