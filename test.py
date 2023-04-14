import requests
import re
import json
import base64
url = "https://www.battlemetrics.com/servers/dayz/19265029"
respomse = requests.get(url)
data = respomse.text


# 查询服务器在线人数和状态
def get_server():
    # 获取在线人数
    pattern = r"Players:\s(\d+)/(\d+)"
    # 服务器状态
    pattern2 = r"Status:\s(\w+)"
    match = re.search(pattern, data)
    match2 = re.search(pattern2, data)

    if match:
        online = match.group(1)
        max = match.group(2)
        return(f"服务器状态：{match2.group(1)},当前在线人数：{online}/{max}")
    else:
        return False
