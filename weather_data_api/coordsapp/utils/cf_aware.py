"""
CF (Characterization Factor) extraction utilities for AWARE 2.0 water scarcity data.

This module provides functions to extract water scarcity characterization factors
from the AWARE 2.0 dataset by geographic coordinates.

Data Citation:
Boulay, A.-M., Bare, J., Benini, L., Berger, M., Lathuillière, M. J., Manzardo, A.,
Margni, M., Motoshita, M., Núñez, M., Pastor, A. V., Ridoutt, B., Oki, T., Worbe, S.,
& Pfister, S. (2018). The WULCA consensus characterization model for water scarcity
footprints: assessing impacts of water consumption based on available water remaining
(AWARE). The International Journal of Life Cycle Assessment, 23(2), 368-378.
https://doi.org/10.1007/s11367-017-1333-8
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.contrib.staticfiles.storage import staticfiles_storage

logger = logging.getLogger(__name__)


def snap_to_grid(lon: float, lat: float, grid_size: float = 0.5) -> Tuple[float, float]:
    """
    Snap coordinates to the nearest grid cell center.

    The AWARE20 dataset uses 0.5-degree grid cells. This function rounds
    any input coordinates to the nearest grid cell center.

    Args:
        lon: Longitude in decimal degrees
        lat: Latitude in decimal degrees
        grid_size: Grid cell size in degrees (default: 0.5)

    Returns:
        Tuple of (snapped_lon, snapped_lat)
    """
    snapped_lon = round(lon / grid_size) * grid_size
    snapped_lat = round(lat / grid_size) * grid_size
    return snapped_lon, snapped_lat


def find_nearest_basin_with_data(
    gpkg_path: str, lon: float, lat: float, max_search_radius: float = 5.0
) -> Optional[Tuple[float, float]]:
    """
    Find the nearest grid cell that has CF data.

    This prevents coastal land locations from snapping to ocean cells.
    Searches in expanding rings around the input coordinate.

    Args:
        gpkg_path: Path to GeoPackage file
        lon: Original longitude
        lat: Original latitude
        max_search_radius: Maximum search radius in degrees (default: 5.0)

    Returns:
        Tuple of (lon, lat) for nearest grid cell with data, or None if not found
    """
    try:
        conn = sqlite3.connect(gpkg_path)
        cursor = conn.cursor()

        grid_size = 0.5

        # Generate candidate grid cells in expanding search radius
        candidates = []

        # First: the directly snapped cell
        snapped_lon, snapped_lat = snap_to_grid(lon, lat, grid_size)
        candidates.append((snapped_lon, snapped_lat, 0))  # distance = 0

        # Then: check surrounding cells in rings
        for ring in range(1, int(max_search_radius / grid_size) + 1):
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    # Only check cells on the perimeter of this ring
                    if abs(dx) == ring or abs(dy) == ring:
                        test_lon = snapped_lon + dx * grid_size
                        test_lat = snapped_lat + dy * grid_size

                        # Calculate actual distance from original point
                        distance = ((test_lon - lon) ** 2 + (test_lat - lat) ** 2) ** 0.5

                        if distance <= max_search_radius:
                            candidates.append((test_lon, test_lat, distance))

        # Sort by distance
        candidates.sort(key=lambda x: x[2])

        # Check each candidate for data availability
        for test_lon, test_lat, distance in candidates:
            cursor.execute(
                """
                SELECT Basin_ID
                FROM AWARE20_Native_CFs_geospatial cf
                JOIN rtree_AWARE20_Native_CFs_geospatial_geom r ON cf.rowid = r.id
                WHERE r.minx <= ? AND r.maxx >= ?
                  AND r.miny <= ? AND r.maxy >= ?
                  AND cf.CF_Jan IS NOT NULL
                LIMIT 1;
            """,
                (test_lon, test_lon, test_lat, test_lat),
            )

            result = cursor.fetchone()

            if result:
                conn.close()
                return (test_lon, test_lat)

        conn.close()
        return None

    except Exception as e:
        logger.error(f"Error in find_nearest_basin_with_data: {e}")
        return None


def extract_cf_values_by_coordinate(
    gpkg_path: str, lon: float, lat: float
) -> Optional[Dict]:
    """
    Extract CF values for a given coordinate (longitude, latitude).

    Args:
        gpkg_path: Path to the GeoPackage file
        lon: Longitude in decimal degrees (WGS84)
        lat: Latitude in decimal degrees (WGS84)

    Returns:
        Dictionary containing Basin_ID and monthly CF values, or None if no basin found
    """
    try:
        conn = sqlite3.connect(gpkg_path)
        conn.enable_load_extension(True)

        # Try to load spatialite extension for spatial queries
        has_spatialite = False
        try:
            conn.load_extension("mod_spatialite")
            has_spatialite = True
        except Exception:
            pass

        cursor = conn.cursor()

        if has_spatialite:
            # Use spatialite for proper point-in-polygon query
            query = """
            SELECT
                Basin_ID,
                CF_Jan, CF_Feb, CF_Mar, CF_Apr, CF_May, CF_Jun,
                CF_Jul, CF_Aug, CF_Sep, CF_Oct, CF_Nov, CF_Dec
            FROM AWARE20_Native_CFs_geospatial
            WHERE ST_Contains(geom, MakePoint(?, ?, 4326))
            LIMIT 1;
            """
            cursor.execute(query, (lon, lat))
        else:
            # Fallback: use rtree index for bounding box search
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
            logger.warning(
                "Using bounding box approximation for CF query (spatialite not available)"
            )

        result = cursor.fetchone()
        conn.close()

        if result and result[1] is not None:  # Check if CF_Jan is not NULL
            return {"Basin_ID": result[0], "monthly_values": list(result[1:13])}
        else:
            return None

    except sqlite3.Error as e:
        logger.error(f"SQLite error in CF extraction: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in CF extraction: {e}")
        return None


def monthly_to_hourly_step_function(monthly_values: List[float]) -> List[float]:
    """
    Convert monthly CF values to hourly resolution using a step function.

    Each hour in a month gets that month's CF value (constant within month).
    Uses non-leap year (365 days = 8760 hours).

    Args:
        monthly_values: List of 12 monthly CF values (Jan-Dec)

    Returns:
        List of 8760 hourly CF values
    """
    # Hours per month (non-leap year)
    hours_per_month = [
        31 * 24,  # Jan: 744
        28 * 24,  # Feb: 672
        31 * 24,  # Mar: 744
        30 * 24,  # Apr: 720
        31 * 24,  # May: 744
        30 * 24,  # Jun: 720
        31 * 24,  # Jul: 744
        31 * 24,  # Aug: 744
        30 * 24,  # Sep: 720
        31 * 24,  # Oct: 744
        30 * 24,  # Nov: 720
        31 * 24,  # Dec: 744
    ]

    # Create hourly timeseries with step function
    hourly_values = []
    for month_idx, (cf_value, hours) in enumerate(zip(monthly_values, hours_per_month)):
        # Repeat the monthly CF value for all hours in that month
        hourly_values.extend([cf_value] * hours)

    return hourly_values


def get_cf_timeseries_for_coordinate(lat: float, lon: float) -> List[float]:
    """
    Get hourly CF timeseries for a coordinate (Django-friendly wrapper).

    This is the main function to use from Django views.

    Note: CF values are static (don't vary by year). Each month's CF value is
    applied to all hours in that month (step function). Uses non-leap year
    (365 days = 8760 hours).

    Args:
        lat: Latitude in decimal degrees (WGS84)
        lon: Longitude in decimal degrees (WGS84)

    Returns:
        List of 8760 hourly CF values (returns all 1.0 if no data available)
    """
    try:
        # Get the GeoPackage file path from Django static files
        gpkg_path = staticfiles_storage.path("AWARE20_Native_CFs_geospatial.gpkg")

        # Find nearest basin with data
        nearest_coords = find_nearest_basin_with_data(gpkg_path, lon, lat, max_search_radius=5.0)

        if nearest_coords:
            snapped_lon, snapped_lat = nearest_coords
            distance = ((snapped_lon - lon) ** 2 + (snapped_lat - lat) ** 2) ** 0.5

            if distance > 0.01:  # Log if snapping occurred
                logger.info(
                    f"CF query: Snapped ({lat}, {lon}) to ({snapped_lat}, {snapped_lon}) "
                    f"- distance: {distance:.3f}° (~{distance * 111:.1f} km)"
                )

            # Extract monthly CF values
            cf_data = extract_cf_values_by_coordinate(gpkg_path, snapped_lon, snapped_lat)

            if cf_data:
                # Convert to hourly values using step function
                hourly_values = monthly_to_hourly_step_function(cf_data["monthly_values"])
                logger.info(
                    f"CF data extracted for basin {cf_data['Basin_ID']} at ({snapped_lat}, {snapped_lon})"
                )
                return hourly_values
            else:
                logger.warning(
                    f"No CF data found for coordinate ({lat}, {lon}) - returning CF=1.0"
                )
                return [1.0] * 8760
        else:
            logger.warning(
                f"No basins with CF data within 5° of ({lat}, {lon}) - returning CF=1.0"
            )
            return [1.0] * 8760

    except FileNotFoundError:
        logger.error(
            "AWARE20_Native_CFs_geospatial.gpkg not found in static files - returning CF=1.0"
        )
        return [1.0] * 8760
    except Exception as e:
        logger.error(f"Error getting CF timeseries: {e} - returning CF=1.0")
        return [1.0] * 8760
