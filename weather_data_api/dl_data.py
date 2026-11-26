accumulated_variables = [
    "evaporation",
    "total_sky_direct_solar_radiation_at_surface",
    "surface_solar_radiation_downwards",
    "total_precipitation",
]

instantaneous_variables = [
    "2m_dewpoint_temperature",
    "forecast_surface_roughness",
    "surface_pressure",
    "2m_temperature",
    "10m_u_component_of_wind",
    "100m_u_component_of_wind",
    "10m_v_component_of_wind",
    "100m_v_component_of_wind",
]

from pathlib import Path
import cdsapi

#one need to copy the key into the ~/.cdsapirc file

client = cdsapi.Client()

dataset = "reanalysis-era5-single-levels"

variable_groups = {
    "tp": "total_precipitation",
    "e": "evaporation",
    "ssrd": "surface_solar_radiation_downwards",
    "fdir": "total_sky_direct_solar_radiation_at_surface",
    "t2m": "2m_temperature",
    "d2m": "2m_dewpoint_temperature",
    "sp": "surface_pressure",
    "u10": "10m_u_component_of_wind",
    "v10": "10m_v_component_of_wind",
    "fsr": "forecast_surface_roughness",
    "u100": "100m_u_component_of_wind",
    "v100": "100m_v_component_of_wind",
}

year = 2025

STATIC_DIR = Path("staticfiles")

for name, variables in variable_groups.items():

    target = Path(f"{name}_{year}.nc")
    target = STATIC_DIR / target

    if target.exists():
        print(f"Skipping {target}: already exists")
        continue

    print(f"Downloading {target}")
    request = {
        "product_type": ["reanalysis"],
        "variable": [variables],
        "year": [str(year)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "data_format": "netcdf",
        "download_format": "unarchived",
    }

    client.retrieve(dataset, request, target)
