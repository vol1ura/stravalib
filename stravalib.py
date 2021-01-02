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
        print(f"Athlete is successfully connected to Strava.")
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
            "state": "https://github.com/",
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
            if "access_token" not in refresh_response:
                print('Token refresh is failed.')
                raise SystemExit
            print('Token was successfully refreshed.')
            self.token = refresh_response
            save_object(self.token, Strava.token_file)
        exp_time = self.token['expires_at'] - int(time.time())
        hours = exp_time // 3600
        mins = (exp_time - 3600 * hours) // 60
        s = f"{hours}h " if hours != 0 else ""
        print(f"Token expires after {s}{mins} min")

    def list_activities(self, **kwargs):
        values_url = urllib.parse.urlencode(kwargs)
        url = 'https://www.strava.com/api/v3/athlete/activities?' + values_url
        return requests.get(url, headers=self.extra_headers).json()

    def get_activity(self, activity_id):
        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
        return requests.get(url, headers=self.extra_headers).json()

    def add_weather(self, activity_id, weather_api_key, lan='en'):
        activity = self.get_activity(activity_id)
        if activity['manual']:
            print(f"Activity with ID {activity_id} is manual created. Can't add weather info for it.")
            return
        description = activity.get('description', '')
        description = '' if description is None else description
        if description.startswith('Погода:'):
            print(f'Weather description for activity ID {activity_id} is already set.')
            return
        lat = activity['start_latitude']
        lon = activity['start_longitude']
        time_tuple = time.strptime(activity['start_date'], '%Y-%m-%dT%H:%M:%SZ')
        start_time = int(time.mktime(time_tuple))
        base_url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine?" \
                   f"lat={lat}&lon={lon}&dt={start_time}&appid={weather_api_key}&units=metric&lang={lan}"
        w = requests.get(base_url).json()['current']
        trnsl = {'ru': ['Погода', 'по ощущениям', 'влажность', 'ветер', 'м/с', 'с'],
                 'en': ['Weather', 'feels like', 'humidity', 'wind', 'm/s', 'from']}
        weather_desc = f"{trnsl[lan][0]}: {w['temp']:.1f}°C ({trnsl[lan][1]} {w['feels_like']:.0f}°C), " \
                       f"{trnsl[lan][2]} {w['humidity']}%, {trnsl[lan][3]} {w['wind_speed']:.1f}{trnsl[lan][4]} " \
                       f"({trnsl[lan][5]} {compass_direction(w['wind_deg'], lan)}), {w['weather'][0]['description']}.\n"
        payload = {'description': weather_desc + description}
        url = f'https://www.strava.com/api/v3/activities/{activity_id}'
        return requests.put(url, headers=self.extra_headers, data=payload).json()
