import json
import requests
import logging
import asyncio
import time
import boto3
from dataprep.connector import connect
from collections import namedtuple

# import requests
AWS_REGION_NAME = 'ap-southeast-1'

kinesis_stream_name = 'BD-ASM3'
session = boto3.session.Session(region_name=AWS_REGION_NAME)
kinesis_client = session.client('firehose')

access_token = 'bd6ea98b5d9d65c8061d8fcdb5cf9910'

ApiInfo = namedtuple('ApiInfo', ['name', 'access_token'])
apiInfo = ApiInfo('openweathermap', access_token)

sc = connect(apiInfo.name, _auth={'access_token': apiInfo.access_token}, _concurrency=3)
locations = ['Singapore']

async def get_weather(city):
    df_weather = await sc.query("weather", q=city)
    return df_weather


def lambda_handler(event, context):
    output = []

    location = locations[0]
    current_weather = asyncio.run(get_weather(city=location))
    current_weather['location'] = location
    now = time.localtime()
    current_weather['report_time'] = time.strftime(
        "%Y-%m-%d %H:%M:%S", now)
    logging.info("Current Weather information:")
    logging.info(current_weather)
    current_weather = current_weather.to_json(orient="records")
    response = kinesis_client.put_record(
        DeliveryStreamName = kinesis_stream_name,
        Record = {
            'Data': current_weather
        }
    )
    logging.info("Response:")
    logging.info(response)

    output.append(response)
    return {
        "records": output
    }
