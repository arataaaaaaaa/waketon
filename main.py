import sys
import json
import time
from google.cloud import speech
import setting
import pyaudio
from six.moves import queue
import pykakasi
from speak import speak
from PIL import Image, ImageDraw, ImageFont, ImageOps
from adafruit_rgb_display.rgb import color565
from adafruit_rgb_display.ili9341 import ILI9341
from busio import SPI
from digitalio import DigitalInOut
import board
import RPi.GPIO as GPIO
import requests as req
import Levenshtein

cs_pin = DigitalInOut(board.D8)
dc_pin = DigitalInOut(board.D25)
rst_pin = DigitalInOut(board.D24)

gomi_type = [
    "N/A", #typeID=1
    "缶、びん、ペットボトルごみ", #typeID=2
    "容器包装プラスチックごみ", #typeID=3
    "大型ごみ", #typeID=4
    "燃えないごみ", #typeID=5
    "カセットボンベ、スプレー缶ごみ", #typeID=6
    "燃えるごみ", #typeID=7
    "ペットの死体",#typeID=8
    "市では収集しないもの"#typeID=9
]

spi = SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)

display = ILI9341(
    spi,
    cs=cs_pin, dc=dc_pin, rst=rst_pin,
    width=240, height=320,
    rotation=90,
    baudrate=24000000
)
width = 240
height = 320
display.fill(color565(255,255,255))

gomi_json = {}
with open("gomi.json","r",encoding="utf-8") as f:
    gomi_json = json.load(f)
gomi_list = gomi_json["gomi"]

weather_codes = {}
with open("weather_codes.json","r") as f:
    weather_codes = json.load(f)

def display_text(_display,x,y,text,fontsize,back_color=(255,255,255),color=(0,0,0)):
    width = _display.width
    height = _display.height

    font = ImageFont.truetype(setting.FONT_NAME,fontsize)
    img = Image.new("RGB",(height,width),back_color)
    draw = ImageDraw.Draw(img)
    i = 0
    for line in text.split("\n"):
        split_length = int((height-x)/fontsize)
        split_text = [line[x:x+split_length] for x in range(0, len(line), split_length)]
        for txt in split_text:
            if not fontsize*i+fontsize>width:
                draw.text((0,fontsize*i),txt,color,font=font)
            i += 1

    img = ImageOps.mirror(img)
    img = ImageOps.flip(img)
    _display.image(img)

    return i

class MicrophoneStream(object):
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True
        self.stop = False
    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self
    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()
    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue
    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            if self.stop:
                data = []
            yield b"".join(data)
def parse_gomi_name(text):
    gomi_name = text[:text.index("捨て方")].rstrip("の")
    return gomi_name

def find_gomi(gomi_name):
    r = ""
    kks = pykakasi.kakasi()
    gomi_index = kks.convert(gomi_name)[0]["kana"]

    match_gomi = {}
    for gomi in gomi_list:
        if gomi_index in gomi["simple_index"]:
            simple = gomi["simple"]
            if not simple in match_gomi:
                match_gomi[simple] = []
            match_gomi[simple].append(gomi)
    return match_gomi

def text_gomi(gomi_name,match_gomi):
    reply = ""

    reply += gomi_name
    reply += "やな。"

    if match_gomi:
        for simple,gomi_group in match_gomi.items():
            reply += simple
            reply += "なら、"
            if len(gomi_group)>1:
                for gomi in gomi_group:
                    reply += "、".join(gomi["options"])
                    reply += "の場合は、"
                    reply += gomi_type[int(gomi["typeID"])-1]
                    reply += "、"
                    reply += gomi["comment"].replace("　","。")
                    reply += "、"
            else:
                gomi = gomi_group[0]
                reply += gomi_type[int(gomi["typeID"])-1]
                reply += "、"
                reply += gomi["comment"].replace("　","。")
            reply += "。"
        reply += "やで。"
    else:
        reply += "見つからんかったわ。"
        reply = ""
        similar = []
        for gomi in gomi_list:
            simple = gomi["simple"]
            distance = Levenshtein.distance(gomi_name,simple)
            if distance < 5:
                similar.append((simple,distance))
        if len(similar)>0:
            reply += "もしかして、"
            text = "もしかして：\n"

            similar.sort(key=lambda e:e[1])
            for gomi in similar[:5]:
                reply += gomi[0]
                reply += "、"
                text += "・"
                text += gomi[0]
                text += "\n"
            display_text(0,0,text,20,(255,255,255),(0,0,0))
    return reply

def weather_text(codes):
    url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{setting.AREA_ID}.json"
    js = json.loads(req.get(url).text)
    reply = ""
    i = 0
    days = ["今日","明日","明後日",""]
    for i,weather in enumerate(js[0]["timeSeries"][0]["areas"][0]["weatherCodes"]):
        if weather in codes:
            weather_text = codes[weather][3]
            reply += days[i] + "の天気は"
            reply += weather_text
            reply += "、"
            i += 1
        reply += "。"
    reply += "やで"
    return reply
def reply_ai(text):
    json_data = {"utterance":text}
    json_data.update(setting.MEBO_AUTH_KEY)

    res = req.post('https://api-mebo.dev/api', headers={'Content-Type': 'application/json'}, json=json_data)
    js = res.json()
    if "bestResponse" in js:
        t = js["bestResponse"]["utterance"]
        return t
    else:
        return "エラーが発生したか、もしくはAIを利用する回数制限を全て使ってしまったようやな。"
def simple_reply(text):
    if "教えてワケトン" in text or "教えて理由と" in text or "教えてはけとん" in text or "教えてケトン" in text:
        return "な～に～"
    elif "ありがと" in text:
        return "ええでええで"
    elif "誰" in text:
        return """ワケトンやで。神戸生まれで、仲間と協力して、町のみんなにごみの排出区分やルールを説明したり、ごみの日にキチンとルールが守られているかをチェックしているよ。
        ルールを守らない宿敵「ワケヘン」に悩まされながらも、今日もこよなく愛する神戸のために、友達と一緒にごみ問題に取り組んでいるんやで。"""
    elif "天気" in text:
        return weather_text(weather_codes)
    else:
        return reply_ai(text)
    return "よく分からんわ。"


def answer(text):
    speak_text = ""
    if "捨て方" in text:
        gomi_name = parse_gomi_name(text)
        match_gomi = find_gomi(gomi_name)
        speak_text = text_gomi(gomi_name,match_gomi)

        text_display = ""
        for simple,gomi_group in match_gomi.items():
            text_display += simple + "\n"
            if len(gomi_group)>1:
                for gomi in gomi_group:
                    text_display += "　" + "、".join(gomi["options"]) + "\n"
                    text_display += "　‥‥" + gomi_type[int(gomi["typeID"])-1] + "\n"
                    text_display += "　　" + gomi["comment"] + "\n"
            else:
                gomi = gomi_group[0]
                text_display += "　・・" + gomi_type[int(gomi["typeID"])-1] + "\n"
                text_display += "　　" + gomi["comment"] + "\n"
            text_display += "\n"
        display_text(display,0,0,text_display,15)
    else:
        speak_text = simple_reply(text)
        display_text(display,0,0,"ワケトン> " + speak_text,20)
    return speak_text

def listen(responses,stream):
    num_chars_printed = 0
    for response in responses:
        if not response.results:
            continue
        result = response.results[0]
        if not result.alternatives:
            continue
        transcript = result.alternatives[0].transcript
        overwrite_chars = " " * (num_chars_printed - len(transcript))
        if not result.is_final:
            sys.stdout.write(transcript + overwrite_chars + "\r")
            sys.stdout.flush()
            num_chars_printed = len(transcript)
            display_text(display,0,0,transcript,25,(125,125,125),(255,255,255))
        else:
            print("$",transcript + overwrite_chars)
            
            speak_text = answer(transcript)
            stream.stop = True
            print("ワケトン>",speak_text)
            speak(speak_text)
            stream.stop = False
            break

def main():
    language_code = "ja-JP"
    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=setting.RATE,
        language_code=language_code,
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(21,GPIO.IN)
    while True:
        display_text(display,0,0,"何でも聞いてや～\n\nスイッチ押して話しかけてや～",25)

        while not GPIO.input(21):
            time.sleep(0.01)
        
        display_text(display,0,0,"何でも聞いてな～",25)
        with MicrophoneStream(setting.RATE, setting.CHUNK) as stream:
            audio_generator = stream.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )
            responses = client.streaming_recognize(streaming_config, requests)
            print("Listening..")
            listen(responses, stream)
if __name__ == "__main__":
    main()