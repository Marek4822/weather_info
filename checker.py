import os
import shutil
import time

def checker(max_retries=5):
    path = '/home/triceratops-whisperer/weather_info/Message_sent'
    retries = 0

    while retries < max_retries:
        if os.path.exists(path):
            print('All good')
            shutil.rmtree(path)
            exit()
        else:
            os.system('/home/linuxbrew/.linuxbrew/bin/python3 /home/triceratops-whisperer/weather_info/main.py')
            time.sleep(180)
            retries += 1

    exit()

checker()