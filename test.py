from datetime import datetime, timedelta
import random
import time
import requests
import loadDayzLog
import querySteam

# 查询服务器在线人数和状态
# 暂存这次获取的随机数值 因为日志不一定更新
def get_server(ip):
    is_online = loadDayzLog.is_process_running("DayZServer_x64.exe")
    if is_online:
        playInfo = querySteam.get_server(ip)
        if playInfo == {}:
            return "请求错误，请稍后重试"
        # 人数波动 在夜里1点之后加虚假人数 1-3 第二天早上8点之前不加虚假人数 8点之后加虚假人数 5-8随机
        if time.localtime().tm_hour >= 1 and time.localtime().tm_hour < 13:
            random_online = random.randint(1, 3)
        elif time.localtime().tm_hour >= 13 and time.localtime().tm_hour < 18:
            # 随机生成虚假人数
            random_online = random.randint(3, 6)
        elif time.localtime().tm_hour > 18 and time.localtime().tm_hour <= 24:
            random_online = random.randint(6, 9)

        # 设置本地增加的虚假人数
        # loadDayzLog.change_server_player_count(random_online)

        # 加上虚假人数 这个人数是播报给qq机器人的人数
        # online += 3
        # 服务器状态
        return(f"服务器状态：在线，在线人数：{playInfo['player']} / {playInfo['max_player']}，服务器延迟：{playInfo['ping']}ms, 游戏时间：{playInfo['time']}")
    else:
        return "服务器进程未启动！"

# last_request_time = None  # 存储上一次请求时间的变量

# def make_request():
#     global last_request_time
    
#     now = datetime.now()  # 获取当前时间
#     # 如果上一次请求时间不存在或距离当前时间超过5分钟，允许发起请求
#     if last_request_time is None or now - last_request_time > timedelta(minutes=5):
#         # 发起请求的代码在这里
#         last_request_time = now  # 更新上一次请求时间
#         return get_server()
#     else:
#         # 如果距离上一次请求时间不足5分钟
#         return "距离上次请求时间不足5分钟，请稍后再试！"
    