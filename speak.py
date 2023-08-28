import requests as req
import base64
import simpleaudio
import google.auth
import google.auth.transport.requests

def get_accesstoken():
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    return credentials.token

def speak(text,lang="ja-JP",voice="ja-JP-Neural2-C"):
    data = {
    "audioConfig": {
        "audioEncoding": "LINEAR16",
        "effectsProfileId": [
        "small-bluetooth-speaker-class-device"
        ],
        "sampleRateHertz": 16000,
        "pitch": 0,
        "speakingRate": 1
    },
    "input": {
        "text": text
    },
    "voice": {
        "languageCode": lang,
        "name": voice
    }
    }
    token = get_accesstoken()

    headers = {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json; charset=utf-8',
    }

    res = req.post('https://texttospeech.googleapis.com/v1beta1/text:synthesize', headers=headers, json=data)

    js = res.json()


    filename = "temp.wav"
    if "audioContent" in js:
        base64audio = js["audioContent"]

        wav_file = open(filename, "wb")
        decode_string = base64.b64decode(base64audio)
        wav_file.write(decode_string)
        try:
            wav_obj = simpleaudio.WaveObject.from_wave_file(filename)
            play_obj = wav_obj.play()
            play_obj.wait_done()
            return play_obj
        except Exception as err:
            print("ERROR:",err)
    else:
        raise js