# stravalib 

`stravalib` is a library and scripts for working with the Strava based on Strava API.

## Before use

You need to register an application in your Strava account before getting started. 
A registered application will be assigned a `client ID` and `client secret`. 
For more detail information see [official Strava documentation](https://developers.strava.com/docs/getting-started/).

## Using module

Module `stravalib` contains a class with methods based on requests to the [Strava API](https://developers.strava.com/docs/reference/)

Constructor of the class will redirect you to the default system browser, where the authorization flow must be completed. 
In the background the local webserver will be running and listening to the data returned by Strava. All received data will be saved locally for future using.

## Using scripts

Script `add_weather.py` adds weather information to all your Strava activities for the past four days. 
He will automatically skips the training if the information has already been added. 
This script uses a weather server https://api.openweathermap.org/. You need to register on this site to recieve api token that will be prompted when you run script.
You can choose language of description from two languages - english by default or russian.
