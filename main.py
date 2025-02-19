from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from cred import *
from datetime import datetime
import requests
import openai
import unicodedata
import random
from data import *
import os
import shutil
import json


MAIN_PATH = '/home/triceratops-whisperer/weather_info'

def get_day_name():
    dt = datetime.now()
    day_name = dt.strftime('%A')
    daymonth = dt.strftime(f"{'%d'}/{'%m'}")
    year = dt.strftime(f"{'%Y'}")
    full_year = dt.strftime(f"{'%Y'}-{'%m'}-{'%d'}")

    return day_name, daymonth, year, full_year

day_name, daymonth, year, full_year = get_day_name()

def get_weather():
    city_name = 'Gdańsk'
    url = f'http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API}&q={city_name}&days=1&aqi=yes&alerts=no'
    request = requests.get(url)
    data = request.json()
    # date = data['forecast']['forecastday'][0]['date']
    max_temp = data['forecast']['forecastday'][0]['day']['maxtemp_c']
    min_temp = data['forecast']['forecastday'][0]['day']['mintemp_c']
    condition = data['forecast']['forecastday'][0]['day']['condition']['text']
    rain_chance = data['forecast']['forecastday'][0]['day']['daily_chance_of_rain']
    snow_chance = data['forecast']['forecastday'][0]['day']['daily_chance_of_snow']

    return max_temp, min_temp, condition, rain_chance, snow_chance

max_temp, min_temp, condition , rain_chance, snow_chance = get_weather()

def funfact_call(FACT_KEY):
    api_url = 'https://api.api-ninjas.com/v1/facts'
    response = requests.get(api_url, headers={'X-Api-Key': FACT_KEY})
    if response.status_code == requests.codes.ok:
        data = response.json()
        return data[0]['fact']
    else:
        print(f"API error: {response.status_code}")
        return None

def save_fact(fact):
    with open(f"{MAIN_PATH}/fact_data.txt", "a") as f:
        f.write(f'{fact}\n')
    print(f'File saved: {fact}')

def load_existing_facts():
    try:
        with open(f"{MAIN_PATH}/fact_data.txt", "r") as f:
            return set(f.read().splitlines())
    except FileNotFoundError:
        return set()

def checker_fact():
    existing_facts = load_existing_facts()
    attempts = 0
    fact = funfact_call(FACT_KEY)
    while (fact in existing_facts or fact is None) and attempts < 5:
        print('Duplicate found or API error. Generating new fact...')
        fact = funfact_call(FACT_KEY)
        attempts += 1
    if fact and fact not in existing_facts:
        save_fact(fact)
        return fact
    else:
        print("Failed to generate a unique fact after 5 attempts.")
        return None

fact = checker_fact()


def gen_traits():
    return random.choice(traits)

traits = gen_traits()
print(traits)


def get_calendar_data(year):
    path = f'{MAIN_PATH}/calendar-{year}.json'
    if os.path.exists(path):
        print('Calendar data is up to date!')
    else:
        api_url = f'https://calendarific.com/api/v2/holidays?&api_key={CALENDAR_API}&country=PL&year={year}'
        response = requests.get(api_url)
        if response.status_code == requests.codes.ok:
            data = response.json()
            with open(f'{MAIN_PATH}/calendar-{year}.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        else:
            print("Error:", response.status_code, response.text)

get_calendar_data(year)


def check_holiday(holidays, full_year):
    for holiday in holidays:
        if holiday["date"]["iso"] == full_year:
            return holiday["name"]
    return None

with open(f"{MAIN_PATH}/calendar-{year}.json", "r") as file:
    holiday_data = json.load(file)
    
holidays = holiday_data["response"]["holidays"]

# full_year = '2024-01-01'
holiday_name = check_holiday(holidays, full_year)


def check_birthdays(birthdays, daymonth):
    for date, name in birthdays:
        if daymonth == date:
            return name

birthday = check_birthdays(birthdays, daymonth)


def generate_prompt(prompt_key, **kwargs):
    if prompt_key in prompts:
        return prompts[prompt_key].format(**kwargs)


weather_message = generate_prompt(
    "weather_caster",
    max_temp=max_temp,
    min_temp=min_temp,
    condition=condition,
    rain_chance=rain_chance,
    snow_chance=snow_chance,
    day_name=day_name,
    traits=traits
)

birthday_message = generate_prompt(
    "birthday_wishes", 
    name=birthday,
    max_temp=max_temp,
    min_temp=min_temp,
    condition=condition,
    rain_chance=rain_chance,
    snow_chance=snow_chance,
    day_name=day_name,
    traits=traits)

holiday_message = generate_prompt(
    "holiday_greetings", 
    traits=traits, 
    holiday_name=holiday_name)


def api_chatgpt_text(OPENAI_API, birthday, holiday_name):
    openai.api_key = OPENAI_API

    if birthday is None:
        if holiday_name:
            prompt = weather_message + holiday_message
        else:
            prompt = weather_message
    else:
        if holiday_name:
            prompt = birthday_message + holiday_message
        else:
            prompt = birthday_message


    completion = openai.chat.completions.create(
    #model="gpt-3.5-turbo",
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": prompt,
        },
    ],
)
    gpt_answer = completion.choices[0].message.content
    return gpt_answer

gpt_answer = api_chatgpt_text(OPENAI_API, birthday, holiday_name)

# print(gpt_answer)

def convert_messege(text):
    normalized_text = unicodedata.normalize('NFC', text)
    char_bmp = ''.join(char for char in normalized_text if ord(char) <= 0xFFFF)
    return char_bmp

message = convert_messege(f'{gpt_answer}\nHere is some fun fact: {fact}')

# print(message)

chrome_options = Options()
chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox") 
chrome_options.add_argument("--disable-dev-shm-usage") 
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

service = Service('/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)
try:

    driver.get(f"https://www.messenger.com/t/{THREAD_ID}")
    time.sleep(5) 

    driver.find_element(By.XPATH, "//button[@title='Allow all cookies' and @type='submit']").click()
    time.sleep(5)
    driver.find_element(By.ID, "email").send_keys(EMAIL)
    time.sleep(5)
    driver.find_element(By.ID, "pass").send_keys(PASSWORD)
    time.sleep(5)
    driver.find_element(By.ID, "loginbutton").click()
    time.sleep(5)

    if "login" in driver.current_url.lower():
        print("Login failed. Check your credentials or CAPTCHA.")
    else:
        print("Login successful!")

        driver.get(f"https://www.messenger.com/t/{THREAD_ID}")
        time.sleep(5)  

        send = driver.find_element(By.XPATH, "//div[contains(@class, 'xzsf02u x1a2a7pz x1n2onr6')]")
        send.send_keys(message)
        enter = driver.find_element(By.XPATH, "//div[contains(@class, 'xzsf02u x1a2a7pz x1n2onr6')]")
        enter.send_keys(Keys.RETURN)

        time.sleep(1)
        print(f"Message sent to thread {THREAD_ID}!")
finally:
    driver.quit()

def create_file():
    os.mkdir(f'{MAIN_PATH}/Message_sent')

create_file()


