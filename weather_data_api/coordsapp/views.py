from django.http import HttpResponse, FileResponse, JsonResponse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import render, HttpResponseRedirect
import os
import xarray as xr
import pandas as pd
import json


def coordinates_form(request):
    if request.method == "POST":
        lat = float(request.POST.get("latitude"))
        lon = float(request.POST.get("longitude"))

        # grid_step = 0.25
        # lat_grid = ((lat + grid_step) // grid_step) * grid_step
        # lon_grid = ((lon + grid_step) // grid_step) * grid_step
        # print(dt2)
        # dt = ds.sel(latitude=lat_grid, longitude=lon_grid, method="nearest")
        ds = xr.open_dataset(staticfiles_storage.path("download.nc"))
        # import pdb;pdb.set_trace()
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
            # "latitude_grid": lat_grid,
            # "longitude_grid": lon_grid,
            "latitude": lat,
            "longitude": lon,
        }
        for col in df.columns.difference(["valid_time", "latitude", "longitude"]):
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
