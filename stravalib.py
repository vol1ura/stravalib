import pickle
import requests
import socket
import time
import urllib.parse
import webbrowser


def save_object(obj, filename: str):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)


def load_object(filename: str):
    with open(filename, 'rb') as f:
        return pickle.load(f)


def get_strava_app_data():
    """
    Read file with Strava API Client. If file is not exists then you will be asked for input.
    Read https://developers.strava.com/docs/getting-started/#account for more information.

    :return: dictionary with client ID and Strava client secret key
    """
    try:
        strava_app = load_object('my_strava_app.dat')
    except FileNotFoundError:
        strava_app = dict()
        strava_app['client_id'] = input('Input Strava client ID:')
        strava_app['client_secret'] = input('Input Strava client secret:')
        save_object(strava_app, 'my_strava_app.dat')
    return strava_app


def get_weather_key() -> str:
    """
    Read file with API key for weather data access. If file is not exists then you will be asked for input.
    Read https://openweathermap.org/api

    :return: string with key
    """
    try:
        key = load_object('my_weather_key.dat')
    except FileNotFoundError:
        key = input('Input openweathermap.org API key:')
        save_object(key, 'my_weather_key.dat')
    return key


def compass_direction(degree: int, lan='en') -> str:
    compass_arr = {'ru': ["С", "ССВ", "СВ", "ВСВ", "В", "ВЮВ", "ЮВ", "ЮЮВ",
                          "Ю", "ЮЮЗ", "ЮЗ", "ЗЮЗ", "З", "ЗСЗ", "СЗ", "ССЗ", "С"],
                   'en': ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]}
    return compass_arr[lan][int((degree % 360) / 22.5 + 0.5)]


class Strava:
    token_file = 'my_strava_token.dat'

    def __init__(self):
        self.client = get_strava_app_data()
        try:
            self.token = load_object(Strava.token_file)
        except FileNotFoundError:
            self.token = self.get_token()
            save_object(self.token, Strava.token_file)
        self.check_token()
        print(f"Hello {self.token['athlete']['firstname']} {self.token['athlete']['lastname']}, "
              f"you successfully get access to Strava.")
        self.extra_headers = {'Authorization': f"Bearer {self.token['access_token']}"}

    def get_token(self):
        client_id = self.client['client_id']
        client_secret = self.client['client_secret']
        port = 5000
        params_oauth = {
            "response_type": "code",
            "client_id": client_id,
            "scope": "read_all,profile:read_all,activity:write,activity:read_all",
            "approval_prompt": "force",
            "state": "https://github.com/vol1ura/stravalib",
            "redirect_uri": f"http://localhost:{port}/authorization_successful"
        }
        values_url = urllib.parse.urlencode(params_oauth)
        webbrowser.open('https://www.strava.com/oauth/authorize?' + values_url)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            s.listen()
            conn, addr = s.accept()
            request_bytes = b''
            with conn:
                while True:
                    chunk = conn.recv(512)
                    request_bytes += chunk
                    if request_bytes.endswith(b'\r\n\r\n'):
                        break
                conn.sendall(b'HTTP/1.1 200 OK\r\n\r\nAuthorized OK. You can close the window now.\r\n')
        request = request_bytes.decode('utf-8')
        if 'authorization_successful' not in request:
            print('Authorization failed.')
            raise SystemExit
        code = urllib.parse.parse_qs(request.split(' ')[1])['code'][0]
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code"
        }
        token_response = requests.post("https://www.strava.com/oauth/token", data=params).json()
        if 'access_token' not in token_response:
            print('Access to token is failed.')
            raise SystemExit
        return token_response

    def check_token(self):
        client_id = self.client['client_id']
        client_secret = self.client['client_secret']

        if self.token['expires_at'] < time.time():
            params = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": self.token['refresh_token'],
                "grant_type": "refresh_token"
            }
            refresh_response = requests.post("https://www.strava.com/oauth/token", data=params).json()
            try:
                self.token['refresh_token'] = refresh_response['refresh_token']
                self.token['access_token'] = refresh_response['access_token']
                self.token['expires_at'] = refresh_response['expires_at']
                save_object(self.token, Strava.token_file)
            except KeyError:
                print('Token refresh is failed.')
                raise SystemExit
            print('Token was successfully refreshed.')
        exp_time = self.token['expires_at'] - int(time.time())
        hours = exp_time // 3600
        mins = (exp_time - 3600 * hours) // 60
        s = f"{hours}h " if hours != 0 else ""
        print(f"Token expires after {s}{mins} min")

    def list_activities(self, after=0, before=time.time()):
        """
        List athlete activities. Usually with parameters:

        :param after: integer, the time since epoch is assumed
        :param before: integer, the time since epoch is assumed
        :return: list with SummaryActivity dictionaries
        """
        url = f'https://www.strava.com/api/v3/athlete/activities?after={after}&before={before}'
        return requests.get(url, headers=self.extra_headers).json()

    def get_activity(self, activity_id: int):
        """Get information about activity

        :param activity_id: integer or string is a number
        :return: dictionary with activity data
        """
        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
        return requests.get(url, headers=self.extra_headers).json()

    def modify_activity(self, activity_id: int, payload: dict):
        """
        Method can change UpdatableActivity parameters such that description, name, type, gear_id.
        See https://developers.strava.com/docs/reference/#api-models-UpdatableActivity

        :param activity_id: integer Strava activity ID
        :param payload: dictionary with keys description, name, type, gear_id, trainer, commute
        :return: dictionary with updated activity parameters
        """
        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
        return requests.put(url, headers=self.extra_headers, data=payload).json()

    def add_weather(self, activity_id: int, weather_api_key: str, lan='en'):
        activity = self.get_activity(activity_id)
        if activity['manual']:
            print(f"Activity with ID{activity_id} is manual created. Can't add weather info for it.")
            return
        description = activity.get('description', '')
        description = '' if description is None else description
        if description.startswith('Погода:'):
            print(f'Weather description for activity ID{activity_id} is already set.')
            return
        lat = activity['start_latitude']
        lon = activity['start_longitude']
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(time.mktime(time_tuple))
        base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
                   f"lat={lat}&lon={lon}&dt={start_time}&appid={weather_api_key}&units=metric&lang={lan}"
        w = requests.get(base_url).json()['current']
        base_url = f"http://api.openweathermap.org/data/2.5/air_pollution?" \
                   f"lat={lat}&lon={lon}&appid={weather_api_key}"
        aq = requests.get(base_url).json()
        print(aq)
        print(start_time + 7200 > aq['list'][0]['dt'])
        air_conditions = f"Воздух: {aq['list'][0]['components']['so2']}(PM2.5), " \
                         f"{aq['list'][0]['components']['so2']}(SO₂), {aq['list'][0]['components']['no2']}(NO₂), " \
                         f"{aq['list'][0]['components']['nh3']}(NH₃).\n"
        print(air_conditions)
        trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
                 'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
        weather_desc = f"{trnsl[lan][0]}: {w['temp']:.1f}°C ({trnsl[lan][1]} {w['feels_like']:.0f}°C), " \
                       f"{trnsl[lan][2]} {w['humidity']}%, {trnsl[lan][3]} {w['wind_speed']:.1f}{trnsl[lan][4]} " \
                       f"({trnsl[lan][5]} {compass_direction(w['wind_deg'], lan)}), {w['weather'][0]['description']}.\n"
        payload = {'description': weather_desc + air_conditions + description}
        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
        return requests.put(url, headers=self.extra_headers, data=payload).json()
