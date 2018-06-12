import os
import urllib
import random
import base64
import boto3
import time
import json
from forecastiopy import *
import zipcodes


# Grab the Bot OAuth token from the environment.
BOT_TOKEN = base64.standard_b64decode(os.environ["BOT_TOKEN"])

# Base slack api url
SLACK_URL = "https://slack.com/api/"

def get_loc(messages):
    for word in messages:
        word = word.rstrip('?:!.,;')
        if word.isdigit():
            myzip = zipcodes.matching(word)
            if myzip:
                myzip_dict = myzip[0]
                myzip_dict['location_text'] = ('{}, {}').format(myzip_dict['city'], myzip_dict['state'])
                return myzip_dict

    return False

def convertF(temp):
    temp = (temp - 32) / 9.0 * 5.0
    return temp
    
def get_current_weather(fio):
    if fio.has_currently() is True:
        currently = FIOCurrently.FIOCurrently(fio)
        currentSummary = currently.summary
        currentTemp = currently.temperature
        return {'summary': currentSummary, 'temp': currentTemp}
    else:
        return False
    
def get_daily_weather(fio):
    if fio.has_daily() is True:
        daily = FIODaily.FIODaily(fio)
        today = daily.get_day(0)
        summary = today['summary']
        high = today['temperatureHigh']
        low = today['temperatureLow']
        return {'summary': summary, 'high': high, 'low': low}
    else:
        return False

def get_weather(loc):
    apikey = os.environ['DARKSKY_TOKEN']
    fio = ForecastIO.ForecastIO(apikey,
                                units = ForecastIO.ForecastIO.UNITS_US,
                                lang=ForecastIO.ForecastIO.LANG_ENGLISH,
                                latitude=loc['lat'], longitude=loc['long'])
                                
    currentWeather = get_current_weather(fio)
    dailyWeather = get_daily_weather(fio)
    if currentWeather and dailyWeather:
        weatherReport = ('```In {}: {}, Currently {:.0f}F/{:.0f}C, High of {:.0f}F/{:.0f}C,'
                         ' Low of {:.0f}F/{:.0f}C. {}```'.format( loc['location_text'],
                            currentWeather['summary'], currentWeather['temp'],
                            convertF(currentWeather['temp']), dailyWeather['high'],
                            convertF(dailyWeather['high']), dailyWeather['low'],
                            convertF(dailyWeather['low']), dailyWeather['summary']
                        ))
        return weatherReport
    else:
        return False

def pick_train():
    s3 = boto3.client('s3')
    bucket_name = 'aedanbot-trains'
    train_objects = s3.list_objects_v2(Bucket=bucket_name)

    choice = random.choice(train_objects["Contents"])
    print(choice["Key"])
    train_link = "https://s3.amazonaws.com/aedanbot-trains/{}".format(choice["Key"])
    
    return train_link
        

def send_message(data):
    
    message_url = SLACK_URL + "chat.postMessage"
    
    # Construct the HTTP request that will be sent to the Slack API.
    request = urllib.request.Request(
        message_url, 
        data=data, 
        method="POST"
    )
    # Add a header mentioning that the text is URL-encoded.
    request.add_header(
        "Content-Type", 
        "application/x-www-form-urlencoded"
    )
    
    # Fire off the request!
    urllib.request.urlopen(request).read()

def lambda_handler(event, context):
    
    #print(event)
    
    train_array = ["train","trains","subway","path"]
    climb_array = ["climb","climbing","climber"]

    message_raw = json.loads(event['body'])

    #print(message_raw.keys())
    
    if "challenge" in message_raw.keys():
        challenge = message_raw["challenge"]
        response_body = {"challenge": challenge }
        response = {
                        "isBase64Encoded": False,
                        "statusCode": 200,
                        "headers": { "Content-Type": "application/json" },
                        "body": json.dumps(response_body)
                    }
        print(response)
        return response
        
    
    if "event" in message_raw.keys():
        message_details = message_raw["event"]
        print(message_details)
        print(message_details["text"])
        
        message_text = message_details["text"].lower().split()
        message_text = [x.rstrip('?:!.,;') for x in message_text]
        #message_text = ''.join([x.rstrip('?:!.,;') for x in message_text])
        
        if message_details["text"].strip() == "<@UB6EQQG5V>":
            possible_responses = [
                {"response":"my dudes!"},
                {"response":":thinking-3d:"},
                {"response":"allbirds are good yall"},
                {"response":":path:"},
                {"response":"_something something New Jersey_"}
            ]
            choice = random.choice(possible_responses)
            print(choice)
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice["response"]),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
            
        elif "help" in message_text:
            choice = (':wave: My pals, I am a bot. Try asking me about: \n'
                        '```the weather in your zipcode \n'
                        'allbirds \n'
                        'trains \n'
                        'or climbing```')
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
        
        elif "allbirds" in message_text:
            choice = "https://www.allbirds.com/"
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
            
    
        elif bool(set(climb_array) & set(message_text)):
            choice = "https://www.youtube.com/watch?v=mzepo51Ua44"
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
            
        elif "weather" in message_text:
            loc = get_loc(message_text)
            if loc:
                choice = get_weather(loc)
            else:
                choice = 'Sorry I didn\'t understand that zipcode :fb-sad:'
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
            
        elif bool(set(train_array) & set(message_text)):
            choice = pick_train()
            data = urllib.parse.urlencode(
                (
                    ("token", BOT_TOKEN),
                    ("channel", message_details["channel"]),
                    ("text", choice),
                    ("as_user", True)
                )
            )
            data = data.encode("ascii")
            send_message(data)
        
        
        
        # Everything went fine.
        response = {
                        "isBase64Encoded": False,
                        "statusCode": 200,
                        "headers": { "Content-Type": "application/json" },
                        "body": "200 OK"
                    }
        print(response)
        return response
