import os

MEBO_AUTH_KEY = {
    "api_key": "API KEY HERE",
    "agent_id": "AGENT ID HERE",
    "uid": "UID HERE"
}
FONT_NAME = "NotoSansJP-VariableFont_wght.ttf"
AREA_ID = "280000"
RATE = 48000
CHUNK = int(RATE / 10)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getcwd() + '/google_auth_key.json'