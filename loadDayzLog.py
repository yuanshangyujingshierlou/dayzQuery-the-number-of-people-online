import datetime
import os
from datetime import datetime,timedelta
import shutil
import time
import psutil
import deadPlayerData
# 服务器日志文件夹路径
dayz_server_log_dir_path = 'C:/Program Files (x86)/Steam/steamapps/common/DayZServer/Profiles/0'

# 读取服务器的adm文件 返回在线玩家人数和时间
def read_dayz_log_txt(path):
    if os.path.exists(path):
        playInfoText = ''
        with open(path, 'r') as file:
            line = file.readline()
            while line:
                # 如果是包含Saved 1 players的行，就把它添加到allText
                if 'PlayerList' in line and 'players' in line:
                    playInfoText = line
                line = file.readline()
        return playInfoText

# 读取服务器ADM文件，获取查询的玩家的坐标
def read_player_location(path, player_name):
    if os.path.exists(path):
        playInfoText = '未查询到你的信息，请确保你已经在线，并且群昵称是你的游戏昵称！'
        with open(path, 'r') as file:
            line = file.readline()
            while line:
                # 如果是包含Saved 1 players的行，就把它添加到allText
                if 'Player' in line and '(id=' in line and player_name in line and 'pos=' in line:
                    playInfoText = line
                line = file.readline()
        return playInfoText 

# 获取离当前时间最近的文件 返回文件路径
def find_recent_file(dir_path):
    recent_file = None
    recent_time = None
    current_time = datetime.now()

    for filename in os.listdir(dir_path):
        if filename.endswith('.RPT'):
            file_path = os.path.join(dir_path, filename)
            create_time = datetime.fromtimestamp(os.path.getctime(file_path))
            time_diff = current_time - create_time
            if recent_time is None or time_diff < recent_time:
                recent_file = file_path
                recent_time = time_diff

    return recent_file

# 复制并改名文件
# src_path: 源文件路径
# dst_path: 目标文件路径
# 返回新文件的路径
def copy_and_rename_file(src_path, dst_path):
    # 删除当前目录下的playercount.txt
    if os.path.exists(dst_path):
        os.remove(dst_path)
    shutil.copy2(src_path, dst_path) # 复制文件
    return dst_path

# 获取离当前时间最近的在线玩家人数 返回在线人数和时间
def get_latest_player_count():
# 保存离当前时间最近的时间戳和在线玩家人数
    text = read_dayz_log_txt('C:/Program Files (x86)/Steam/steamapps/common/DayZServer/Profiles/0/DayZServer_x64.ADM')
    if text == '':
        return "", ""
    nearest_player_count = int(text.split('log:')[1].split(' ')[1])
    nearest_timestamp = text.split('|')[0]
    return nearest_player_count, nearest_timestamp

# 获取要查询的玩家的最近的一条坐标信息 传入日志最近的一条 返回坐标信息和时间
def get_player_position(player_name):
    text = read_player_location('C:/Program Files (x86)/Steam/steamapps/common/DayZServer/Profiles/0/DayZServer_x64.ADM', player_name)
    if text == '未查询到你的信息，请确保你已经在线，并且群昵称是你的游戏昵称！':
        return text, ""
    nearest_player_position = text.split('pos=<')[1].split('>)')[0]
    nearest_timestamp = text.split(' |')[0]
    # 如果超过五分钟，就返回空
    if is_in_time(nearest_timestamp, 300) :
        return "未查询到你的信息，请确保你已经在线，并且群昵称是你的游戏昵称！", ""
    return nearest_player_position, nearest_timestamp

# 判断名为name的进程是否正在运行
def is_process_running(name):
    # 判断名为name的进程是否正在运行
    for process in psutil.process_iter(['name']):
        if process.info['name'] == name:
            return True
    return False

# 修改本地的txt文件
def write_dayz_log_txt(path, text):
    with open(path, 'w') as file:
        file.write(text)

# 修改服务器虚假人数
def change_server_player_count(player_count:int):
    # 修改成string
    player_count = str(player_count)
    # 修改本地的txt文件
    write_dayz_log_txt('C:/Program Files (x86)/Steam/steamapps/common/DayZServer/dzfake.txt', player_count)


# 把死亡的玩家信息记录下来
my_data_recorder = deadPlayerData.DataRecorder()
# 读取adm日志文件 获取击杀信息
def read_adm_log_txt(path):
    if os.path.exists(path): # 判断文件是否存在
        deadText = ''
        boo = False # 设置一个标识符 判断是否是同一天
        with open(path, 'r') as file:
            line = file.readline()
            while line:
                # 先判断这一行带不带有AdminLog 如果有就证明是第一条信息，是有日期的
                if ('AdminLog' in line and 'at' in line): # 判断是否是管理员日志信息 或者是同一天的信息
                    adminlog_time = line.split(' ')[3] # 获取时间
                    # 2023-04-21 时间格式 判断是否是同天
                    if adminlog_time.split('-')[0] == datetime.now().strftime('%Y') and adminlog_time.split('-')[1] == datetime.now().strftime('%m') and adminlog_time.split('-')[2] == datetime.now().strftime('%d'):
                        boo = True
                    else :
                        boo = False
                        line = file.readline()
                        continue
                if boo : # 如果是同一天的信息
                    if '(DEAD)' in line: # 判断是否是死亡信息
                        # 判断是否在当前时间的五秒内
                        infoTime = line.split(' |')[0] # 获取死亡信息时间
                        if is_in_time(infoTime): # 如果不在五秒内，就跳过
                            line = file.readline()
                            continue
                        # 判断是否有两个Player
                        if line.count('Player') == 2 and 'with' in line and 'from' and "meters" in line and 'into' in line:
                            # 获取两个Player的名字 1是被杀 2是杀人
                            player1 = line.split('Player')[1].split(' ')[1]
                            player2 = line.split('Player')[2].split(' ')[1]
                            # 获取击中部位
                            hitPart = line.split('into')[1].split(' ')[1]
                            # 判断是否是重复信息
                            if(my_data_recorder.has_data(player1)):
                                line = file.readline()
                                continue
                            else : # 如果不是重复信息，就把他加入到死亡列表中 被杀人已经死了，接下来15秒内不在接收他的死亡信息
                                my_data_recorder.add_data(player1, player1)
                                # 获取武器
                                weapon = line.split('with')[1].split(' ')[1]
                                # 获取距离
                                distance = line.split('from')[1].split(' ')[1]
                                print(player1, player2, weapon, distance, hitPart)
                                deadText = '在{}，{}被{}用{}击中{}，距离{}米，致死'.format(infoTime, player1, player2, weapon, hitPart, distance)
                    # # 判断是不是自杀
                    # elif 'Player' in line and 'committed suicide' in line:
                    #     # 判断在不在五秒内
                    #     infoTime = line.split(' |')[0] # 获取死亡信息时间
                    #     if is_in_time(infoTime): # 如果不在五秒内，就跳过
                    #         line = file.readline()
                    #         continue
                    #     player = line.split('Player')[1].split(' ')[1]
                    #     deadTime = line.split(' |')[0] # 获取死亡信息时间
                    #     # 判断是否是重复信息
                    #     if(my_data_recorder.has_data(player)):
                    #         line = file.readline()
                    #         continue
                    #     my_data_recorder.add_data(player, player)
                    #     deadText = '在{}，{}选择了自杀'.format(deadTime, player)
                    line = file.readline()
                line = file.readline()
        if deadText == "" :
            return None
        else :
            return deadText
# 判断是不是在规定时间内
def is_in_time(infoTime, time=60):
        nowTime = datetime.now().time() # 获取当前时间
        # 转换格式可以和nowTime运算的格式
        infoTime = datetime.strptime(infoTime, "%H:%M:%S").time()
        infoDateTime = datetime.combine(datetime.today(), infoTime)
        nowDateTime = datetime.combine(datetime.today(), nowTime)
        delta = abs(nowDateTime - infoDateTime) # 获取时间差
        if delta.total_seconds() > time: # 如果不在五秒内，就跳过
            return True
        else:
            return False