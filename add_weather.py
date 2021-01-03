import stravalib
import time

if __name__ == '__main__':
    strava = stravalib.Strava()
    activities = strava.list_activities(after=int(time.time()-4*3600*24))
    weather_key = stravalib.get_weather_key()
    for activity in activities:
        strava.add_weather(activity['id'], weather_key, lan='ru')
