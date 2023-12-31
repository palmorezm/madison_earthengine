# -*- coding: utf-8 -*-
"""GoogleEarthEngine.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nSmkV3y0Ia54T-jACjqepGKpJ3HggNiv

This is a script to access data from the Google Earth Engine.
"""

# Working with earth engine (ee)
import ee
# Trigger the authentication flow.
ee.Authenticate()
# Initialize the library.
ee.Initialize()

"""Token authorization provided. Now, what data do we want?"""

# Import the ERA5 C collection.
# Daily Aggregates - Latest Climate Reanalysis Produced by ECMWF / Copernicus Climate Change Service
# https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_DAILY#bands
lst = ee.ImageCollection('MODIS/061/MOD11A1')

"""Data source: [ERA5 Daily Aggregates](https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_DAILY#bands)
**Data source: [MOD11A1.061 Terra Land Surface Temperature and Emissivity Daily Global](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A1#bands)**

Select only the data within the dates we want.
"""

# Initial date of interest (inclusive).
i_date = '2000-02-24'

# Final date of interest (exclusive).
f_date = '2023-04-28'

# Selection of appropriate bands and dates for LST.
lst = lst.select('LST_Day_1km', 'QC_Day').filterDate(i_date, f_date)

"""Let's take a look at Madison, WI. We can specify the coords by lat and lon."""

# Define the location of interest
# Madison WI
# lon = -89.40123019999999
# lat = 43.0730517
u_lon = -89.4012
u_lat = 43.0730
u_poi = ee.Geometry.Point(u_lon, u_lat)

"""Define the scale we want in meters and then calculate the average temp at the point."""

scale = 1000  # scale in meters

# Calculate and print the mean value of the LST collection at the point.
lst_urban_point = lst.mean().sample(u_poi, scale).first().get('LST_Day_1km').getInfo()
print('Average daytime LST at urban point:', round(lst_urban_point*0.02 -273.15, 2), '°C')

"""We got it going now. Let's look at the first 5 points.  


"""

# Get the data for the pixel intersecting the point in urban area.
lst_u_poi = lst.getRegion(u_poi, scale).getInfo()
# Preview the result.
lst_u_poi[:5]

"""Convert that to a pandas data frame to make it easier to work with."""

import pandas as pd

def ee_array_to_df(arr, list_of_bands):
    """Transforms client-side ee.Image.getRegion array to pandas.DataFrame."""
    df = pd.DataFrame(arr)

    # Rearrange the header.
    headers = df.iloc[0]
    df = pd.DataFrame(df.values[1:], columns=headers)

    # Remove rows without data inside.
    df = df[['longitude', 'latitude', 'time', *list_of_bands]].dropna()

    # Convert the data to numeric values.
    for band in list_of_bands:
        df[band] = pd.to_numeric(df[band], errors='coerce')

    # Convert the time field into a datetime.
    df['datetime'] = pd.to_datetime(df['time'], unit='ms')

    # Keep the columns of interest.
    df = df[['time','datetime',  *list_of_bands]]

    return df

"""Look at the data frame and convert temperature to celcius for all points."""

lst_df_urban = ee_array_to_df(lst_u_poi,['LST_Day_1km'])

def t_modis_to_celsius(t_modis):
    """Converts MODIS LST units to degrees Celsius."""
    t_celsius =  0.02*t_modis - 273.15
    return t_celsius

# Apply the function to get temperature in celsius.
lst_df_urban['LST_Day_1km'] = lst_df_urban['LST_Day_1km'].apply(t_modis_to_celsius)

lst_df_urban.head()

"""Can we download the data as a csv? I think so. Let's try."""

from google.colab import files
lst_df_urban.to_csv('lst.csv')
files.download("lst.csv")

# Commented out IPython magic to ensure Python compatibility.
import matplotlib.pyplot as plt
import numpy as np
from scipy import optimize
# %matplotlib inline

# Fitting curves.
## First, extract x values (times) from the dfs.
x_data_u = np.asanyarray(lst_df_urban['time'].apply(float))  # urban

## Secondly, extract y values (LST) from the dfs.
y_data_u = np.asanyarray(lst_df_urban['LST_Day_1km'].apply(float))  # urban

## Then, define the fitting function with parameters.
def fit_func(t, lst0, delta_lst, tau, phi):
    return lst0 + (delta_lst/2)*np.sin(2*np.pi*t/tau + phi)

## Optimize the parameters using a good start p0.
lst0 = 20
delta_lst = 40
tau = 365*24*3600*1000   # milliseconds in a year
phi = 2*np.pi*4*30.5*3600*1000/tau  # offset regarding when we expect LST(t)=LST0

params_u, params_covariance_u = optimize.curve_fit(
    fit_func, x_data_u, y_data_u, p0=[lst0, delta_lst, tau, phi])

# Subplots.
fig, ax = plt.subplots(figsize=(14, 6))

# Add scatter plots.
ax.scatter(lst_df_urban['datetime'], lst_df_urban['LST_Day_1km'],
           c='black', alpha=0.2, label='Urban (data)')

# Add fitting curves.
ax.plot(lst_df_urban['datetime'],
        fit_func(x_data_u, params_u[0], params_u[1], params_u[2], params_u[3]),
        label='Urban (fitted)', color='black', lw=2.5)

# Add some parameters.
ax.set_title('Daytime Land Surface Temperature Madison, WI', fontsize=16)
ax.set_xlabel('Date', fontsize=14)
ax.set_ylabel('Temperature [C]', fontsize=14)
ax.set_ylim(-30, 50)
ax.grid(lw=0.2)
ax.legend(fontsize=14, loc='lower right')

plt.show()