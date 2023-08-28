import requests as req
import json
import re

url = "https://gomisaku.jp/0188/ja/dictionary.js" #「ごみサク」からデータを抽出

request = req.get(url,verify=False)

data = request.text
data = data.lstrip("gomisakuGetData('dictionary',")
data = data.rstrip(");")
jsdata = json.loads(data)

js = jsdata["array"]["dict"]
trashes = []

for row_data in js:
    trash = {}
    for i,key in enumerate(row_data["key"]):
        value = row_data["string"][i]
        if not value:
            value = ""
        value = value.replace("(","（")
        value = value.replace(")","）")
        trash[key] = value
    trashes.append(trash)
for trash in trashes:
    if trash["typeID"]=="6":
        trash["comment"] = "中身は全部使い切る。穴あけ不要。燃えないゴミと分けて中身の見える袋で出す。クリーンステーションに燃えないゴミと場所をわけて出す"

    m_trash_option = re.search("(?<=（).*?(?=）)",trash["name"])
    if m_trash_option:
        text = m_trash_option.group()
        options = text.split("、")
        trash["options"] = options
    else:
        trash["options"] = []
    m_trash_examples = re.search("(?<=【).*?(?=】)",trash["name"])
    if m_trash_examples:
        text = m_trash_examples.group()
        examples = text.split("、")
        trash["examples"] = examples
    else:
        trash["examples"] = []

    m_simple_name = re.match("^.*?(?=[（【])",trash["name"])
    if m_simple_name:
        text = m_simple_name.group()
        trash["simple"] = text
    else:
        trash["simple"] = trash["name"]
    m_simple_index = re.match("^.*?(?=（)",trash["index"])
    if m_simple_index:
        text = m_simple_index.group()
        trash["simple_index"] = text
    else:
        trash["simple_index"] = trash["index"]
    



json_data = {"gomi":trashes}

filename = "gomi.json"
with open(filename,"w",encoding="utf-8") as f:
    json.dump(json_data,f,indent=2,ensure_ascii=False)