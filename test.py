from datetime import datetime, timedelta
import random
import time
import loadDayzLog

# 查询服务器在线人数和状态
# 暂存这次获取的随机数值 因为日志不一定更新
random_online = 0 # 上次在线人数数值
onLinetime = 0    # 上一次获取的时间
def get_server():
    global random_online
    global onLinetime
    is_online = loadDayzLog.is_process_running("DayZServer_x64.exe")
    if is_online:
        playInfo = loadDayzLog.get_latest_player_count()
        # 如果获取的时间和上一次获取的时间一样 说明日志没有更新 则不能更新随机数值
        if onLinetime == playInfo[1]:
            # 用上一次的随机数值
            random_online = random_online
        else:
            # 如果获取的时间和上一次获取的时间不一样 记录这次获取的时间
            onLinetime = playInfo[1]
            # 人数波动 在夜里1点之后加虚假人数 1-3 第二天早上8点之前不加虚假人数 8点之后加虚假人数 5-8随机
            if time.localtime().tm_hour >= 1 and time.localtime().tm_hour < 13:
                random_online = random.randint(1, 3)
            elif time.localtime().tm_hour >= 13 and time.localtime().tm_hour < 18:
                # 随机生成虚假人数
                random_online = random.randint(5, 7)
            elif time.localtime().tm_hour > 18 and time.localtime().tm_hour <= 24:
                random_online = random.randint(5, 7)
            # 设置本地增加的虚假人数
            loadDayzLog.change_server_player_count(random_online)

        # 获取在线人数
        online = playInfo[0]
        if online == '':
            return "获取在线人数失败，稍后重试！"
        
        # 去掉小数点
        type_onLinetime = str(onLinetime).split('.')[0]
        # 去掉秒
        type_onLinetime = str(onLinetime).split(':')[0] + '点' + str(onLinetime).split(':')[1] + '分'

        # 加上虚假人数 这个人数是播报给qq机器人的人数
        online += random_online

        # 服务器状态
        return(f"服务器状态：在线，{type_onLinetime}在线人数：{online}")
    else:
        return "服务器进程未启动！"
    


last_request_time = None  # 存储上一次请求时间的变量

def make_request():
    global last_request_time
    
    now = datetime.now()  # 获取当前时间
    # 如果上一次请求时间不存在或距离当前时间超过5分钟，允许发起请求
    if last_request_time is None or now - last_request_time > timedelta(minutes=5):
        # 发起请求的代码在这里
        last_request_time = now  # 更新上一次请求时间
        return get_server()
    else:
        # 如果距离上一次请求时间不足5分钟
        return "距离上次请求时间不足5分钟，请稍后再试！"