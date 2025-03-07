from django.http import HttpResponse, FileResponse, JsonResponse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import render, HttpResponseRedirect
from django.db.models import Max, Min, Count
import os
import xarray as xr
import pandas as pd
import json
from weather_data_api.coordsapp.models import WeatherData

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
        ds = xr.open_dataset(staticfiles_storage.path("data-accum.nc"))
        dt = ds.sel(latitude=lat, longitude=lon, method="nearest")

        df = dt.to_dataframe()
        idx = df.index
        df = df.reset_index()
        freq = pd.infer_freq(idx)
        if freq is None:
            freq="h"
        json_dict = {
            "time": {"start": str(idx[0]), "end": str(idx[-1]), "freq": freq},
            "variables": {},
            "latitude_grid": float(df.latitude.unique()[0]),
            "longitude_grid": float(df.longitude.unique()[0]),
            "latitude": lat,
            "longitude": lon,
        }
        for col in df.columns.difference(["valid_time", "latitude", "longitude"]):
            json_dict["variables"][col] = json.loads(df[col].to_json(orient="values"))

        # Redirect to the download page and pass the coordinates for display
        return JsonResponse(json_dict)
        #return HttpResponseRedirect("download_file")

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
