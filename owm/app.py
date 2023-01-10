import logging
import boto3
from collections import namedtuple
from IPython.display import display, display_html
import time
import requests
import asyncio
import json
import pandas as pd

# units params = metrics to get celcius degree
base_url = "https://api.openweathermap.org/data/2.5/weather?"
api_key = "530664e7973fbffd84d0c2ab3eeeacf9"
AWS_REGION_NAME = 'ap-southeast-1'

kinesis_stream_name = 'OWM-PIPELINE'
session = boto3.session.Session(region_name=AWS_REGION_NAME)
kinesis_client = session.client('firehose')

async def get_data(city):
    # Get the current weather details for the given city.
    api = base_url + "appid=" + api_key + "&q=" + city
    response = requests.get(api)
    return response.json()

# as the wind direction from the api is in degree, what we actually need is in direction (following the train dataset)
# convert wind degree to direction


def degrees_to_cardinal(degree):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
            'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    ix = round(degree / (360 / len(dirs)))
    return dirs[ix % len(dirs)]


def convert_and_clean_pd(data):
    # convert json response to a pandas df
    # record_path = weather to get the nested data
    # meta to get the necessary fields
    columns = [['main', 'temp'],  ['main', 'temp_min'],  ['main', 'temp_max'],  ['main', 'pressure'],  [
        'main', 'humidity'],  ['wind', 'speed'], ['wind', 'deg'], ['wind', 'gust'], ['clouds', 'all']]
    df = pd.json_normalize(data, record_path='weather',
                           meta=columns, errors='ignore')

    # drop unnecessary columns from 'weather'
    drop_columns = ['id', 'description', 'icon']
    df = df.drop(columns=drop_columns, axis=1)

    # add date and time to the df
    now = time.localtime()
    df['Date'] = time.strftime(
        "%Y-%m-%d", now)
    df['Time'] = time.strftime(
        "%H:%M:%S", now)

    # convert main columns (which states the current status of the weather) to RainToday
    # as if it was raining, the value = 1, none then value = 0
    df['main'].mask(df['main'] == 'Rain', 1, inplace=True)
    df['main'].mask(df['main'] != 'Rain', 0, inplace=True)

    # as data is extracted, we need to convert them into proper data type
    cast_to_type = {
        'main': int,
        'main.temp': float,
        'main.temp_min': float,
        'main.temp_max': float,
        'main.pressure': float,
        'main.humidity': float,
        'wind.speed': float,
        'wind.deg': float,
        'wind.gust': float,
        'clouds.all': int,
        'Date': str,
        'Time': str
    }
    df = df.astype(cast_to_type)

    # convert wind direction columns
    df['WindDir'] = (degrees_to_cardinal(df.loc[0, 'wind.deg']))
    df.fillna('NaN', inplace=True)

    # rename columns to proper format
    df = df.rename(columns={'main': 'Raining', 'main.temp': 'Temp', 'main.temp_min': 'MinTemp',
                            'main.temp_max': 'MaxTemp', 'main.pressure': 'Pressure', 'main.humidity': 'Humidity',
                            'wind.speed': 'WindSpeed', 'wind.gust': 'WindGustSpeed', 'wind.deg': 'WindDeg', 'clouds.all': 'Cloud'})
    return df


def run():
    data = asyncio.run(get_data('sydney'))
    df = convert_and_clean_pd(data)
    return df


def lambda_handler(event, context):
    current_weather = run()
    current_weather = current_weather.to_dict('r')
    response = kinesis_client.put_record(
        DeliveryStreamName = kinesis_stream_name,
        Record = {
            "Data": json.dumps(current_weather)
        }
    )

    return current_weather
