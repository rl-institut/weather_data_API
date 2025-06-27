import os
import xarray as xr
import pandas as pd
import numpy as np
import json

lat = 30
lon = 10

datasets = [
    "data-accum.nc",
    # "download.nc",
    "tp_evap_ssrd_2022.nc",
    "sp_fsr_2022.nc",
    "fdir_2022.nc",
    "100m_u_v_wind_2022.nc"
]

timeseries = []
ts_lengths = []
for dataset in datasets:
    ds = xr.open_dataset(os.path.join("staticfiles", dataset))

    dt = ds.sel(latitude=lat, longitude=lon, method="nearest")
    print(dt.coords)
    ts_lengths.append(len(dt.valid_time))
    timeseries.append(dt)


combined = xr.concat(timeseries, dim="valid_time", join="inner")
import pdb;pdb.set_trace()
