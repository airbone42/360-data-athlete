"""Overpass API client for surface detection per lap midpoint."""

from __future__ import annotations

import httpx

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"

SURFACE_MAP: dict[str, str] = {
    "asphalt": "asphalt",
    "compacted": "forest path",
    "gravel": "gravel",
    "dirt": "dirt path",
    "grass": "grass",
    "unpaved": "natural path (unpaved)",
    "paved": "paved",
    "fine_gravel": "fine gravel",
    "ground": "dirt path",
    "sand": "sand",
}

HIGHWAY_FALLBACK: dict[str, str] = {
    "track": "field path / forest path",
    "path": "natural path",
    "footway": "footway",
    "cycleway": "cycleway",
    "residential": "asphalt (residential)",
    "primary": "asphalt (main road)",
    "secondary": "asphalt (road)",
    "service": "asphalt (service road)",
}


async def get_surface_for_point(lat: float, lon: float) -> str:
    """Query Overpass API for the surface type at a given coordinate.

    Returns a human-readable surface label (English).
    """
    query = f"[out:json][timeout:10];\nway(around:30,{lat},{lon})[highway];\nout tags;"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
            )
            response.raise_for_status()
            elements = response.json().get("elements", [])
    except Exception:
        return "unknown"

    surface = "unknown"
    source: str | None = None

    for el in elements:
        tags = el.get("tags", {})
        if tags.get("surface") and SURFACE_MAP.get(tags["surface"]):
            surface = SURFACE_MAP[tags["surface"]]
            source = "surface"
            break
        if tags.get("highway") and HIGHWAY_FALLBACK.get(tags["highway"]) and source != "surface":
            surface = HIGHWAY_FALLBACK[tags["highway"]]
            source = "highway"

    return surface


async def query_surface_bbox(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> list[dict]:
    """Fetch all highway ways with geometry within a bounding box via Overpass."""
    query = (
        f"[out:json][timeout:25];\n"
        f"way[\"highway\"]({min_lat},{min_lon},{max_lat},{max_lon});\n"
        f"out body geom;"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(OVERPASS_URL, data={"data": query})
            response.raise_for_status()
            return response.json().get("elements", [])
    except Exception:
        return []


def map_points_to_surfaces(
    latlng_points: list[list[float]], ways: list[dict]
) -> list[str]:
    """Map each GPS point to the nearest OSM way's surface tag."""
    results: list[str] = []

    # Pre-compute centroids of each way for fast nearest lookup
    way_centroids: list[tuple[float, float, str]] = []
    for way in ways:
        tags = way.get("tags", {})
        surface_raw = tags.get("surface", "")
        highway_raw = tags.get("highway", "")
        label = (
            SURFACE_MAP.get(surface_raw)
            or HIGHWAY_FALLBACK.get(highway_raw)
            or "unknown"
        )
        geom = way.get("geometry", [])
        if geom:
            lat = sum(n["lat"] for n in geom) / len(geom)
            lon = sum(n["lon"] for n in geom) / len(geom)
            way_centroids.append((lat, lon, label))

    for point in latlng_points:
        if len(point) < 2 or not way_centroids:
            results.append("unknown")
            continue
        pt_lat, pt_lon = point[0], point[1]
        best_label = "unknown"
        best_dist = float("inf")
        for clat, clon, label in way_centroids:
            dist = (pt_lat - clat) ** 2 + (pt_lon - clon) ** 2
            if dist < best_dist:
                best_dist = dist
                best_label = label
        results.append(best_label)

    return results


async def enrich_laps_with_surface(laps: list[dict]) -> list[dict]:
    """Add surface field to each lap dict using Overpass API."""
    enriched: list[dict] = []
    for lap in laps:
        mid_lat = lap.get("mid_lat")
        mid_lon = lap.get("mid_lon")
        if mid_lat and mid_lon:
            lap["surface"] = await get_surface_for_point(mid_lat, mid_lon)
        else:
            lap["surface"] = "unknown"
        enriched.append(lap)
    return enriched
