from django.http import HttpResponse, FileResponse, JsonResponse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import render, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token

from django.db.models import Max, Min, Count
import os
import xarray as xr
import pandas as pd
import numpy as np
import json
from weather_data_api.coordsapp.models import WeatherData


# As the .nc files store the data more efficiently than postgres, we read from .nc files
datasets = [
    "data-accum.nc",
    "tp_evap_ssrd_2022.nc",
    "sp_fsr_2022.nc",
    "fdir_2022.nc",
    "100m_u_v_wind_2022.nc",
    "2t_10u_10v_2022.nc",
    "2d_2022.nc",
]

def compress_timestamps_info(ts):
    freq = pd.infer_freq(ts)
    date_start = ts[0]
    date_end = ts[-1]
    return freq, date_start, date_end


def get_closest_grid_point(lat, lon):
    lats = pd.Series([14.442, 14.192, 13.942, 13.692, 13.442, 13.192, 12.942, 12.692, 12.442,
                      12.192, 11.942, 11.692, 11.442, 11.192, 10.942, 10.692, 10.442, 10.192,
                      9.942, 9.692, 9.442, 9.192, 8.942, 8.692, 8.442, 8.192, 7.942,
                      7.692, 7.442, 7.192, 6.942, 6.692, 6.442, 6.192, 5.942, 5.692,
                      5.442, 5.192, 4.942, 4.692, 4.442, 4.192, 3.942, 3.692, 3.442,
                      3.192, 2.942, 2.691])
    lons = pd.Series([4.24, 4.490026, 4.740053, 4.990079, 5.240105, 5.490131,
                      5.740158, 5.990184, 6.240211, 6.490237, 6.740263, 6.99029,
                      7.240316, 7.490342, 7.740368, 7.990395, 8.240421, 8.490447,
                      8.740474, 8.9905, 9.240526, 9.490553, 9.740579, 9.990605,
                      10.240631, 10.490658, 10.740685, 10.99071, 11.240737, 11.490763,
                      11.740789, 11.990816, 12.240842, 12.490869, 12.740894, 12.990921,
                      13.240948, 13.490973, 13.741])
    closest_lat = round(lats.loc[(lats - lat).abs().idxmin()], 3)
    closest_lon = round(lons.loc[(lons - lon).abs().idxmin()], 3)
    return closest_lat, closest_lon

def coordinates_form(request):
    if request.method == "POST":
        lat = float(request.POST.get("latitude"))
        lon = float(request.POST.get("longitude"))

        # grid_step = 0.25
        # lat_grid = ((lat + grid_step) // grid_step) * grid_step
        # lon_grid = ((lon + grid_step) // grid_step) * grid_step
        # print(dt2)
        # dt = ds.sel(latitude=lat_grid, longitude=lon_grid, method="nearest")
        # ds = xr.open_dataset(staticfiles_storage.path("download.nc"))

        timeseries = []
        ts_lengths = []
        for dataset in datasets:
            ds = xr.open_dataset(staticfiles_storage.path(dataset))
            dt = ds.sel(latitude=lat, longitude=lon, method="nearest")
            latitude = float(dt.latitude)
            longitude = float(dt.longitude)
            dt = dt.squeeze().drop_vars(["latitude", "longitude", "number", "expver"], errors="ignore")
            ts_lengths.append(len(dt.valid_time))
            timeseries.append(dt)


        # # import pdb;
        # # pdb.set_trace()
        # mismatch_in_indexes = False
        # if (np.diff(ts_lengths) != 0).any():
        #     print("error with the timeseries not all indexes have the same length")
        #     mismatch_in_indexes = True
        # else:
        #     freq_ref, date_start_ref, date_stop_ref = compress_timestamps_info(timeseries[0].index)
        #
        #     for i,ts in enumerate(timeseries[1:]):
        #         freq, date_start, date_stop = compress_timestamps_info(ts.index)
        #         if freq != freq_ref:
        #             mismatch_in_indexes =True
        #         if date_start != date_start_ref:
        #             mismatch_in_indexes =True
        #         if date_stop != date_stop_ref:
        #             mismatch_in_indexes =True

        combined = xr.merge(timeseries, join="inner")

        df = combined.to_dataframe()
        # pdb.set_trace()
        # ds = xr.open_dataset(staticfiles_storage.path("data-accum.nc"))
        # ds_wind = xr.open_dataset(staticfiles_storage.path("data_wind.nc"))
        # dt = ds.sel(latitude=lat, longitude=lon, method="nearest")
        #
        # dt_wind = ds_wind.sel(latitude=lat, longitude=lon, method="nearest")
        #
        # df = dt.to_dataframe()
        # df_wind = dt_wind.to_dataframe()
        idx = df.index
        df = df.reset_index()
        freq, date_start, date_stop = compress_timestamps_info(idx)
        if freq is None:
            freq="h"
        json_dict = {
            "time": {"start": str(date_start), "end": str(date_stop), "freq": freq},
            "variables": {},
            "latitude_grid": latitude,
            "longitude_grid": longitude,
            "latitude": lat,
            "longitude": lon,
        }
        for col in df.columns.difference(["valid_time", "latitude", "longitude"]):
            json_dict["variables"][col] = json.loads(df[col].to_json(orient="values"))

        # Redirect to the download page and pass the coordinates for display
        return JsonResponse(json_dict)
        #return HttpResponseRedirect("download_file")

    return render(request, "coordsapp/coordinates_form.html")

def wefe_data(request):
    if request.method == "POST":
        lat = float(request.POST.get("latitude"))
        lon = float(request.POST.get("longitude"))

        timeseries = []
        ts_lengths = []
        for dataset in datasets:
            ds = xr.open_dataset(staticfiles_storage.path(dataset))
            dt = ds.sel(latitude=lat, longitude=lon, method="nearest")
            latitude = float(dt.latitude)
            longitude = float(dt.longitude)
            dt = dt.squeeze().drop_vars(["latitude", "longitude", "number", "expver"], errors="ignore")
            ts_lengths.append(len(dt.valid_time))
            timeseries.append(dt)

        combined = xr.merge(timeseries, join="inner")

        df = combined.to_dataframe()

        idx = df.index
        df = df.reset_index()

        df['ghi'] = (df['ssrd'] / 3600.0)
        df['t_air'] = df['t2m'] - 273.15
        df['t_dew'] = df['d2m'] - 273.15
        df['e'] *= 1000
        df['tp'] *= 1000
        df['windspeed'] = np.sqrt(df["u100"] ** 2 + df["v100"] ** 2)

        df.drop(["u10", "v10", "u100", "v100", "t2m", "ssrd", "d2m"], axis=1, inplace=True)

        freq, date_start, date_stop = compress_timestamps_info(idx)
        if freq is None:
            freq="h"
        json_dict = {
            "time": {"start": str(date_start), "end": str(date_stop), "freq": freq},
            "variables": {},
            "latitude_grid": latitude,
            "longitude_grid": longitude,
            "latitude": lat,
            "longitude": lon,
        }
        for col in df.columns.difference(["valid_time", "latitude", "longitude"]):
            json_dict["variables"][col] = json.loads(df[col].to_json(orient="values"))

        # Redirect to the download page and pass the coordinates for display
        return JsonResponse(json_dict)

    return render(request, "coordsapp/coordinates_form.html")


def pps_weather_data(request):
    if request.method == "POST":
        lat_user = float(request.POST.get("latitude"))
        lon_user = float(request.POST.get("longitude"))
        lat,lon = get_closest_grid_point(lat_user, lon_user)
        columns = ['wind_speed', 'temp_air', 'ghi', 'dni', 'dhi']


        #import pdb;pdb.set_trace()
        # TODO fetch colum names
        # qs = WeatherData.objects.filter(lat=lat,lon=lon,dt__gt="2022-01-01 00:00", dt__lte="2023-01-01 00:00").order_by('dt')
        qs = WeatherData.objects.filter(lat=lat,lon=lon).order_by('dt')
        vals = qs.values(*columns)

        date_end = qs.order_by("-dt")[0].dt
        date_start = qs.order_by("dt")[0].dt

        df = pd.DataFrame(list(vals),columns=columns)
        #import pdb;pdb.set_trace()

        # # grid_step = 0.25
        # # lat_grid = ((lat + grid_step) // grid_step) * grid_step
        # # lon_grid = ((lon + grid_step) // grid_step) * grid_step
        # # print(dt2)
        # # dt = ds.sel(latitude=lat_grid, longitude=lon_grid, method="nearest")
        # ds = xr.open_dataset(staticfiles_storage.path("download.nc"))
        # # import pdb;pdb.set_trace()
        # dt = ds.sel(latitude=lat, longitude=lon, method="nearest")
        # #
        # # df = dt.to_dataframe()
        # # idx = df.index
        # # df = df.reset_index()
        # # freq = pd.infer_freq(idx)

        freq="h"
        json_dict = {
            "time": {"start": str(date_start), "end": str(date_end), "freq": freq},
            "variables": {},
            "latitude_grid": lat,
            "longitude_grid": lon,
            "latitude": lat_user,
            "longitude": lon_user,
        }
        # for col in df.columns.difference(["valid_time", "latitude", "longitude"]):
        #     json_dict["variables"][col] = json.loads(df[col].to_json(orient="values"))
        for col in columns:
            json_dict["variables"][col] = json.loads(df[col].to_json(orient="values"))

        # Redirect to the download page and pass the coordinates for display
        return JsonResponse(json_dict)
        #return HttpResponseRedirect("download_file")

    return render(request, "coordsapp/coordinates_form.html")



# def timeseries():
#     output = BytesIO()
#     workbook = xlsxwriter.Workbook(output)
#     worksheet = workbook.add_worksheet("Scalars")
#
#     for idx, kpi_obj in enumerate(scalar_kpis_json):
#         if idx == 0:
#             worksheet.write_row(0, 0, kpi_obj.keys())
#         worksheet.write_row(idx + 1, 0, kpi_obj.values())
#
#     workbook.close()
#     output.seek(0)
#
#
#     filename = "kpi_scalar_results.xlsx"
#     response = HttpResponse(
#         output,
#         content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#     )
#     response["Content-Disposition"] = f"attachment; filename={filename}"


# Second view: Serve the corresponding file for download
def download_file(request):
    lat = request.GET.get("lat", "N/A")
    lon = request.GET.get("lon", "N/A")

    # Absolute path to the files folder
    files_dir = r"C:\Users\Vivek.Rana\Desktop\Projects\DjangoTask\coordproject\coordsapp\files"

    # Generate the filename based on coordinates (you can customize this logic)
    file_name = f"{lat}_{lon}.csv"  # Example: "12.34_56.78.csv"
    file_path = os.path.join(files_dir, file_name)

    # Check if the file exists
    if os.path.exists(file_path):
        # Serve the corresponding file
        response = FileResponse(open(file_path, "rb"), as_attachment=True)
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response
    else:
        # If file does not exist, return an error response
        return HttpResponse("File not found for the given coordinates.", status=404)

@require_http_methods(["GET"])
def imprint(request):
    return render(request, "pages/imprint.html")


@require_http_methods(["GET"])
def privacy(request):
    return render(request, "pages/privacy.html")

@require_http_methods(["GET"])
def get_csrf_token(request):
    """
    Return the CSRF token for this session.
    """
    token = get_token(request)
    return JsonResponse({"csrfToken": token})
