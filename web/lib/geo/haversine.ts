/** Earth distance helpers (WGS84 approx). */

const R_M = 6371000;

function toRad(deg: number) {
  return (deg * Math.PI) / 180;
}

/** Distance in meters between two [lon, lat] points. */
export function haversineMeters(
  a: [number, number],
  b: [number, number]
): number {
  const [lon1, lat1] = a;
  const [lon2, lat2] = b;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const x =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R_M * Math.asin(Math.min(1, Math.sqrt(x)));
}

/** Rough walk time: 1.4 m/s (~5 km/h). */
export function walkSeconds(meters: number): number {
  return Math.round(meters / 1.4);
}

/** Rough vehicle speed by mode (m/s). */
export function vehicleSpeedMps(
  type: "jeepney" | "tricycle" | "bus" | "walk_link"
): number {
  switch (type) {
    case "tricycle":
      return 6; // ~22 km/h city
    case "jeepney":
      return 7; // ~25 km/h
    case "bus":
      return 9; // ~32 km/h
    default:
      return 1.4;
  }
}
