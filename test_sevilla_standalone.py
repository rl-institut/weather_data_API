#!/usr/bin/env python3
"""
Test CF data extraction for Sevilla, Spain (standalone).
"""

import sqlite3
import sys


def snap_to_grid(lon: float, lat: float, grid_size: float = 0.5):
    """Snap coordinates to nearest grid cell."""
    snapped_lon = round(lon / grid_size) * grid_size
    snapped_lat = round(lat / grid_size) * grid_size
    return snapped_lon, snapped_lat


def find_nearest_basin_with_data(gpkg_path: str, lon: float, lat: float, max_search_radius: float = 5.0):
    """Find nearest grid cell with CF data."""
    try:
        conn = sqlite3.connect(gpkg_path)
        cursor = conn.cursor()
        grid_size = 0.5

        candidates = []
        snapped_lon, snapped_lat = snap_to_grid(lon, lat, grid_size)
        candidates.append((snapped_lon, snapped_lat, 0))

        for ring in range(1, int(max_search_radius / grid_size) + 1):
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if abs(dx) == ring or abs(dy) == ring:
                        test_lon = snapped_lon + dx * grid_size
                        test_lat = snapped_lat + dy * grid_size
                        distance = ((test_lon - lon) ** 2 + (test_lat - lat) ** 2) ** 0.5

                        if distance <= max_search_radius:
                            candidates.append((test_lon, test_lat, distance))

        candidates.sort(key=lambda x: x[2])

        for test_lon, test_lat, distance in candidates:
            cursor.execute("""
                SELECT Basin_ID
                FROM AWARE20_Native_CFs_geospatial cf
                JOIN rtree_AWARE20_Native_CFs_geospatial_geom r ON cf.rowid = r.id
                WHERE r.minx <= ? AND r.maxx >= ?
                  AND r.miny <= ? AND r.maxy >= ?
                  AND cf.CF_Jan IS NOT NULL
                LIMIT 1;
            """, (test_lon, test_lon, test_lat, test_lat))

            result = cursor.fetchone()
            if result:
                conn.close()
                return (test_lon, test_lat)

        conn.close()
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def extract_cf_values(gpkg_path: str, lon: float, lat: float):
    """Extract CF values for coordinate."""
    try:
        conn = sqlite3.connect(gpkg_path)
        cursor = conn.cursor()

        query = """
        SELECT
            cf.Basin_ID,
            cf.CF_Jan, cf.CF_Feb, cf.CF_Mar, cf.CF_Apr, cf.CF_May, cf.CF_Jun,
            cf.CF_Jul, cf.CF_Aug, cf.CF_Sep, cf.CF_Oct, cf.CF_Nov, cf.CF_Dec
        FROM AWARE20_Native_CFs_geospatial cf
        JOIN rtree_AWARE20_Native_CFs_geospatial_geom r ON cf.rowid = r.id
        WHERE r.minx <= ? AND r.maxx >= ?
          AND r.miny <= ? AND r.maxy >= ?
        LIMIT 1;
        """
        cursor.execute(query, (lon, lon, lat, lat))
        result = cursor.fetchone()
        conn.close()

        if result and result[1] is not None:
            return {"Basin_ID": result[0], "monthly_values": list(result[1:13])}
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


def monthly_to_hourly_step_function(monthly_values):
    """Convert monthly to hourly using step function."""
    hours_per_month = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]
    hourly_values = []
    for cf_value, hours in zip(monthly_values, hours_per_month):
        hourly_values.extend([cf_value] * hours)
    return hourly_values


def show_sevilla_data():
    """Show CF data for Sevilla."""
    lat = 37.3802341083545
    lon = -5.894728710396742

    gpkg_path = "weather_data_api/static/AWARE20_Native_CFs_geospatial.gpkg"

    print("=" * 80)
    print(f"SEVILLA, SPAIN - FULL DATA EXTRACTION TEST")
    print("=" * 80)
    print(f"\nInput coordinates: ({lat}, {lon})")

    # ========== PART 1: CF (Water Scarcity) Data ==========
    print("\n" + "=" * 80)
    print("PART 1: CF (WATER SCARCITY) DATA - AWARE 2.0")
    print("=" * 80)

    # Find nearest basin
    nearest = find_nearest_basin_with_data(gpkg_path, lon, lat)
    if not nearest:
        print("✗ No CF data found!")
        return

    snapped_lon, snapped_lat = nearest
    distance = ((snapped_lon - lon) ** 2 + (snapped_lat - lat) ** 2) ** 0.5

    print(f"\nSnapped to grid:    ({snapped_lat}, {snapped_lon})")
    print(f"Distance:           {distance:.3f}° (~{distance * 111:.1f} km)")

    # Extract CF data
    cf_data = extract_cf_values(gpkg_path, snapped_lon, snapped_lat)
    if not cf_data:
        print("✗ Failed to extract CF data!")
        return

    print(f"Basin ID:           {cf_data['Basin_ID']}")

    # Convert to hourly
    cf_timeseries = monthly_to_hourly_step_function(cf_data["monthly_values"])

    print(f"\nTotal hours:        {len(cf_timeseries)}")

    # First 24 hours
    print(f"\n┌─ First 24 hours (January 1st) - cf_aware values ─────────────────┐")
    print(f"│ {'Hour':<6} {'CF Value':<12} {'Time':<20} {'Note':<18} │")
    print(f"├───────────────────────────────────────────────────────────────────┤")

    for i in range(24):
        hour_num = i + 1
        cf_value = cf_timeseries[i]
        time_str = f"Jan 1, {i:02d}:00"
        note = "First hour" if i == 0 else ("Noon" if i == 12 else "")
        print(f"│ {hour_num:<6} {cf_value:<12.6f} {time_str:<20} {note:<18} │")

    print(f"└───────────────────────────────────────────────────────────────────┘")

    # Monthly summary
    print(f"\n┌─ Monthly CF values (step function - constant per month) ─────────┐")
    print(f"│ {'Month':<12} {'CF Value':<12} {'Hours':<10} {'Water Stress':<18} │")
    print(f"├───────────────────────────────────────────────────────────────────┤")

    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    hours_per_month = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]

    for i, (month, hours) in enumerate(zip(month_names, hours_per_month)):
        cf_value = cf_data["monthly_values"][i]

        # Categorize water stress
        if cf_value < 1.0:
            stress = "Low (abundant)"
        elif cf_value < 2.0:
            stress = "Moderate"
        elif cf_value < 5.0:
            stress = "High"
        elif cf_value < 10.0:
            stress = "Very High"
        else:
            stress = "Extreme"

        marker = " ← PEAK" if cf_value == max(cf_data["monthly_values"]) else ""
        print(f"│ {month:<12} {cf_value:<12.6f} {hours:<10} {stress:<18} │{marker}")

    print(f"└───────────────────────────────────────────────────────────────────┘")

    # Statistics
    min_cf = min(cf_data["monthly_values"])
    max_cf = max(cf_data["monthly_values"])
    avg_cf = sum(cf_data["monthly_values"]) / len(cf_data["monthly_values"])

    print(f"\n┌─ Annual Statistics ───────────────────────────────────────────────┐")
    print(f"│ Minimum CF:         {min_cf:.4f} ({month_names[cf_data['monthly_values'].index(min_cf)]})")
    print(f"│ Maximum CF:         {max_cf:.4f} ({month_names[cf_data['monthly_values'].index(max_cf)]})")
    print(f"│ Annual Average:     {avg_cf:.4f}")
    print(f"└───────────────────────────────────────────────────────────────────┘")

    # ========== PART 2: Climate Data Preview ==========
    print("\n" + "=" * 80)
    print("PART 2: CLIMATE DATA - Structure (actual values require NetCDF files)")
    print("=" * 80)

    print(f"\n📍 Location: Sevilla region ({lat}, {lon})")
    print(f"   Grid coverage: West Africa (~2.7° to 14.4°N, ~4.2° to 13.7°E)")
    print(f"\n⚠️  NOTE: Sevilla is OUTSIDE the NetCDF coverage area!")
    print(f"   The /data/ endpoint will not return weather data for this location.")
    print(f"   However, CF data IS available (global coverage).")

    print(f"\nExpected API response structure for Sevilla:")
    print("-" * 80)
    print("""{
  "time": {
    "start": "...",
    "end": "...",
    "freq": "h"
  },
  "variables": {
    "cf_aware": [""" + f"{cf_timeseries[0]:.4f}, {cf_timeseries[1]:.4f}, {cf_timeseries[2]:.4f}, ...]")
    print("""    # Note: No weather variables (t2m, u10, v10, etc.) because
    # Sevilla is outside the West Africa NetCDF coverage area
  },
  "latitude_grid": """ + f"{snapped_lat},")
    print("""  "longitude_grid": """ + f"{snapped_lon},")
    print("""  "latitude": """ + f"{lat},")
    print("""  "longitude": """ + f"{lon}")
    print("""}""")

    # Show what climate data WOULD look like if available
    print(f"\n" + "=" * 80)
    print("EXAMPLE: What climate data looks like (for West Africa coordinates)")
    print("=" * 80)

    print(f"""
If you query a coordinate WITHIN West Africa (e.g., 10.5, -73.5), the API returns:

┌─ First 24 hours - All Variables ──────────────────────────────────────┐
│ Hour  cf_aware   t2m(K)   u10(m/s) v10(m/s) tp(m)    ssrd(J/m²)      │
├───────────────────────────────────────────────────────────────────────┤
│ 1     2.890      298.5    2.3      1.2      0.0000   0.0            │
│ 2     2.890      298.4    2.4      1.3      0.0000   0.0            │
│ 3     2.890      298.3    2.5      1.4      0.0000   0.0            │
│ ...   ...        ...      ...      ...      ...      ...            │
│ 24    2.890      299.2    3.1      1.8      0.0001   1250000.0      │
└───────────────────────────────────────────────────────────────────────┘

Available variables:
  - cf_aware: Water scarcity CF (8760 values)
  - t2m: 2m temperature (Kelvin)
  - u10, v10: 10m wind components (m/s)
  - u100, v100: 100m wind components (m/s)
  - tp: Total precipitation (meters)
  - e: Evaporation (meters)
  - ssrd: Surface solar radiation (J/m²)
  - sp: Surface pressure (Pa)
  - fdir: Direct radiation (J/m²)
  - fsr: Forecast snow rain (meters)
""")

    print("=" * 80)
    print("✓ TEST COMPLETE - CF data successfully extracted for Sevilla!")
    print("✗ Weather data not available (location outside NetCDF coverage)")
    print("=" * 80)


if __name__ == "__main__":
    show_sevilla_data()
