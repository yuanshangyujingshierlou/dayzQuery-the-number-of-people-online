#封装GET和POST请求
import datetime
import os
from threading import Timer
import requests
import json
import time
import meinv
import schedule
import miraiCsv
import test
import testHash
import loadDayzLog
from requests_toolbelt.multipart.encoder import MultipartEncoder

qq_group = 697785664
qq_number = 270488994
server_url = "http://dayz.qiyonghan.icu:18080/"
session_key = ""
# 记录开服日期，判断今天是开服第几天
server_start_time = "2023-04-25 00:00:00"

def get(url, api, data=None):
    url = url + api
    # 把参数拼接到url后面
    if data:
        url = url + "?"
        for key, value in data.items():
            url = url + key + "=" + str(value) + "&"
        url = url[:-1]
    respomse = requests.get(url)
    text = respomse.text
    return text


def post(url, api, data, type="application/json"):
    url = url + api
    headers = {
        "Content-Type": type
    }
    data = data
    respomse = None
    if type == "application/json":
        respomse = requests.post(url, headers=headers, json=data)
    else:
        respomse = requests.post(url, data=data, headers=headers)
    text = respomse.text
    return text


# 获取认证接口
def post_verify():
    global session_key
    # 读取本地csv文件
    csv_text = miraiCsv.read_mirai_csv()
    if(csv_text):
        session_key = csv_text[0]
    else:
        # 获取认证接口
        api = "verify"
        # 填写verifyKey
        data = {"verifyKey": 1234567890}
        # 获取认证接口
        obj = json.loads(post(server_url, api, data))
        if obj["code"] == 0:
            # 保存sessionKey到本地csv文件
            miraiCsv.save_mirai_csv(obj["session"])
            session_key = obj["session"]

    # 绑定sessionKey到指定QQ
    if post_bind() :
        print("绑定成功")
    else:
        # 绑定失败就重来
        miraiCsv.remove_mirai_csv()
        post_verify()



# 绑定sessionKey到指定QQ
# 绑定失败重来计数
bind_fail_count = 0
def post_bind():
    api = "bind"
    data = {"sessionKey": session_key, "qq": qq_number}
    obj = json.loads(post(server_url, api, data, "application/json"))
    global bind_fail_count
    bind_fail_count += 1 
    if obj["code"] != 0:
        print("绑定失败", "错误代码:", obj["code"], '即将进行第{}次重试'.format(bind_fail_count))
        return False
    return True


# 获取会话信息
def get_sessionInfo():
    api = "sessionInfo"
    data = {"sessionKey": session_key}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        # session_key = obj["data"]["sessionKey"]
        print("获取会话信息失败", "错误代码:", obj["code"])
    return obj


# 查看消息队列
def get_message():
    api = "countMessage"
    data = {"sessionKey": session_key}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        print("查看消息队列失败", "错误代码:", obj["code"])
    return obj


# 通过messageId获取消息
def get_messageById(messageId):
    api = "messageFromId"
    data = {"sessionKey": session_key, "messageId": messageId, "target": 0}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        print("通过messageId获取消息失败", "错误代码:", obj["code"])
    return obj


# 获取消息队列头部消息
def get_fetchMessage(num=10):
    api = "fetchMessage"
    data = {"sessionKey": session_key, "count": num}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        print("获取消息队列头部消息失败", "错误代码:", obj["code"])
    return obj


# 筛选消息 根据消息类型 分发不同的处理函数
def get_messageFilter(data):
    boo = False
    obj = data['data'][0]
    # 判断消息类型
    if obj['type'] == 'GroupMessage': # 群消息
        # 判断是否是指定群
        if obj['sender']['group']['id'] == qq_group:
            # 判断是否是AT
            messageChain = obj['messageChain'] # 消息链
            quoteId = 0
            for i in messageChain:
                # 判断messageChain是否有type为source的元素，该元素内是否有id
                if (i['type'] == 'Source') and ('id' in i):
                    quoteId = i['id']
                if i['type'] == 'At' :
                    # 判断是否是AT机器人
                    if i['target'] == qq_number:
                        boo = True
                        continue
                if boo: # 是AT机器人
                    # 判断是否是指定消息
                    if i['type'] == 'Plain' and i['text'] == ' 在线人数':
                        getServerText = test.get_server()
                        if getServerText:
                            # 回复消息
                            post_sendMessage(qq_group, getServerText, quote=quoteId)
                        break
                    elif i['type'] == 'Plain' and i['text'].find('我在哪') >= 0: 
                        # 获取玩家昵称
                        playerName = obj['sender']['memberName']
                        posText = loadDayzLog.get_player_position(playerName)
                        if posText[1] == '':
                            post_sendMessage(qq_group, posText[0])
                        else:
                            pos = [posText[0].split(',')[0], posText[0].split(',')[1]]
                            posHour = posText[1].split(':')[0]
                            posMin = posText[1].split(':')[1]
                            posTime = posHour + '时' + posMin + '分'
                            post_sendMessage(qq_group, '{}\n位置：(x:{},y:{})\n时间：{}'.format(playerName, pos[0], pos[1], posTime), quote=quoteId)
                    # 判断是否是否包含转换为波西米亚id
                    elif i['type'] == 'Plain' and i['text'].find('转换为波西米亚id:') >= 0:
                        # 从消息从获取steamid
                        steamid = i['text'].replace(' 转换为波西米亚id:', '')
                        # 获取波西米亚id
                        bosimia_id = testHash.get_bosimia_id(steamid)
                        if bosimia_id:
                            # 回复消息
                            post_sendMessage(qq_group, bosimia_id)
                        else :
                            post_sendMessage(qq_group, '获取波西米亚id失败')
                        break
                    elif i['type'] == 'Plain' and i['text'] == ' 如何进服务器':
                        post_sendMessage(qq_group, "进服务器方法http://dayzguide.qiyonghan.icu/", quote=quoteId)
                        break
                    elif i['type'] == 'Plain' and i['text'] == ' 查询命令':
                        # 回复消息
                        post_sendMessage(qq_group, '1.在线人数\n2.我在哪\n3.转换为波西米亚id:steamid(英文冒号！！！！！！！！！)\n4.如何进服务器\n')
                        break
                    else : # 不是任何命令
                        # 回复消息
                        post_sendMessage(qq_group, '输入的命令有误,你可以跟我说查询命令,我会告诉你所有的命令', quote=quoteId)
                else :# 不是AT机器人 抓取关键字
                    if i['type'] == 'Plain' and ('进不去' in i['text'] or '连不上' in i['text']):
                        # 回复消息
                        post_sendMessage(qq_group, '服务器IP换了,进不去就取消收藏,重新直连一次,或者去社区搜索群名。\n直连IP为dayz.qiyonghan.icu,端口为22302')
                    # 判断是否是请求美女视频
                    if i['type'] == 'Plain' and "视频" in i['text']:
                        # 上传文件
                        post_uploadGroupFile(qq_group, "", meinv.download_meinv())
    # 新人入群事件
    elif obj['type'] == 'MemberJoinEvent':
        # 判断是否是指定群
        if obj['member']['group']['id'] == qq_group:
            target_qq = obj['member']['id']
            target_name = obj['member']['memberName']
            # 回复消息
            post_sendMessage(qq_group, ' 欢迎{}入群! 白名单申请看公告，把steam资料设置全部公开。格式:\nqq:xxxxxxx\nsteamid:xxxxxxxxxxxxxxxx\n波西米亚id:xxxxxxxxx\n游戏昵称:xxx。\n波西米亚id获取方式：群里AT机器人发送命令：转换为波西米亚id:此处填写你的steam17位id。\n以上面这个格式发送给群主\nsteamid获取方式看公告\n进服务器方法http://dayzguide.qiyonghan.icu/'.format(target_name), 'At', target_qq)
    # 退群事件
    elif obj['type'] == 'MemberLeaveEventQuit':
        # 判断是否是指定群
        if obj['member']['group']['id'] == qq_group:
            target_qq = obj['member']['id']
            target_name = obj['member']['memberName']
            # 回复消息
            post_sendMessage(qq_group, ' {}离开了我们'.format(target_name))
    # 申请入群事件
    elif obj['type'] == 'MemberJoinRequestEvent':
        # 判断是否是指定群
        if obj['groupId'] == qq_group:
            # 获取事件id和申请人qq
            post_handleJoinRequest_eventId = obj['eventId']
            post_handleJoinRequest_qq = obj['fromId']
            # 查询申请人资料
            getMemberInfo = get_qqInfo(post_handleJoinRequest_qq)
            # 等级大于等于20
            if getMemberInfo['level'] >= 20:
                # 同意申请
                post_handleJoinRequest(post_handleJoinRequest_eventId, post_handleJoinRequest_qq, qq_group, 0, '')
            else:
                post_handleJoinRequest(post_handleJoinRequest_eventId, post_handleJoinRequest_qq, qq_group, 1, '检测到你的等级小于20，无法加入本群')




# 事件处理
def get_event():
    api = "fetchLatestEvent"
    data = {"sessionKey": session_key}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        print("事件处理失败", "错误代码:", obj["code"])
    return obj

# 群文件上传
# type是上传类型，目前只支持group
# target是群号
# path是qq群文件路径
# file是服务器上的资源路径
def post_uploadGroupFile(group_number, path, file):
    if file == None:
        post_sendMessage(group_number, "获取视频失败")
        return
    api = "file/upload"
    multipart_encode = MultipartEncoder(fields={'sessionKey': session_key, 'type': 'group', "target": '{}'.format(group_number), "path": "/video", "file": (os.path.basename(file), open(file, 'rb'), 'multipart/form-data')})
    obj = json.loads(post(server_url, api, multipart_encode, type=multipart_encode.content_type))
    if obj["code"] != 0:
        print("群文件上传失败", "错误代码:", obj["code"])
    return obj

# 发送群单条消息
# group: 目标群号
# text: 消息内容
# text_type: 消息类型
# target: 被At对象
def post_sendMessage(group, text, text_type="Plain", target=0, quote=0):
    api = "sendGroupMessage"
    messageChain = []
    # 如果是At消息
    if text_type == 'At':
        messageChain = [{"type": "At", "target": target}, {"type": "Plain", "text": text}]
    elif text_type == 'Plain' :
        messageChain = [{"type": text_type, "text": text}]
    elif text_type == 'AtAll' :
        messageChain = [{"type": "AtAll", "target": target}, {"type": "Plain", "text": text}]
    elif text_type == 'Image' :
        messageChain = [{"type": "AtAll", "target": target}, {"type": "Image", "url": text}, {"type": "Plain", "text": ''}]
    if quote == 0:
        data = {"sessionKey": session_key, "target": group, "messageChain": messageChain}
    else:
        data = {"sessionKey": session_key, "target": group, "messageChain": messageChain, "quote": quote}
    obj = json.loads(post(server_url, api, data))
    if obj["code"] != 0:
        print("发送消息失败", "错误代码:", obj["code"])
    return obj


# 获取qq用户资料
def get_qqInfo(qq):
    api = "userProfile"
    data = {"sessionKey": session_key, "target": qq}
    obj = json.loads(get(server_url, api, data))
    # 判断obj内是否有level
    if 'level' in obj:
        # 是正确拿到了资料
        obj = obj
    else:
        # 没有拿到资料
        print('获取qq资料失败')
    return obj


# 处理入群申请
# eventId: 事件id
# fromId: 申请人qq
# groupId: 群号
# isAgree: 是否同意
# message: 拒绝理由
def post_handleJoinRequest(eventId, fromId, groupId, operate, message=""):
    api = "resp/memberJoinRequestEvent"
    data = {"sessionKey": session_key, "eventId": eventId, "fromId": fromId, "groupId": groupId, "operate": operate, "message": message}
    obj = json.loads(post(server_url, api, data))
    if obj["code"] != 0:
        print("处理入群申请失败", "错误代码:", obj["code"])
    return obj

# 查看群文件列表
# group: 群号
def get_groupFileList(group):
    api = "file/list"
    data = {"sessionKey": session_key, "id": "", "group": group}
    obj = json.loads(get(server_url, api, data))
    if obj["code"] != 0:
        print("查看群文件列表失败", "错误代码:", obj["code"])
    return obj

# 自动@全体成员 19:30
def post_atAll():
    # 判断是开服第几天
    # 获取今天日期
    today = datetime.date.today()
    # 获取开服日期
    startDay = datetime.date(2023, 4, 25)
    # 计算开服天数
    day = (today - startDay).days
    # 判断是否是开服第一天
    if day == 0:
        # 发送@全体消息
        post_sendMessage(qq_group, text='http://qiyonghan.icu:40080/images/dayzstrat.jpg', text_type='Image')
        post_sendMessage(qq_group, text='今天开服，速速上线,{}'.format(test.get_server()), text_type='AtAll')
    else:
        # 发送@全体消息
        post_sendMessage(qq_group, text='今天是开服第{}天,{},兄弟们开冲'.format(day, test.get_server()), text_type='AtAll')
        post_sendMessage(qq_group, text='http://qiyonghan.icu:40080/images/dayzstrat.jpg', text_type='Image')

# 入口函数
def main():
    # 获取认证接口
    post_verify()

    # 每晚@全体成员
    schedule.every().day.at("19:00").do(post_atAll)
    schedule.every().day.at("20:00").do(post_atAll)
    schedule.every().day.at("21:00").do(post_atAll)
    schedule.every().day.at("22:00").do(post_atAll)
    # print(get_groupFileList(qq_group))
    # 查看消息队列
    while True:
        schedule.run_pending() # 运行所有可以运行的计时器任务
        obj = get_message() # 获取群消息
        if obj["data"] > 0: # 如果消息队列不为空
            # 获取消息队列头部消息
            fetchMessageObj = get_fetchMessage(10) # 获取头部十条消息 获取成功后消息队列会自动删除
            if fetchMessageObj['code'] == 0: # 如果获取消息成功
                # 筛选消息，回复指定群的指定消息
                get_messageFilter(fetchMessageObj)
            else :
                print('获取消息队列头部消息失败', '错误代码:', fetchMessageObj['code'])

        # 每秒检测一次本地的dayz服务器日志
        deadMessage = loadDayzLog.read_adm_log_txt('C:/Program Files (x86)/Steam/steamapps/common/DayZServer/Profiles/0/DayZServer_x64.ADM')
        # 判断是否有死亡消息
        if deadMessage :
            # 发送死亡消息 延迟一分钟发送
            post_sendMessage(qq_group, deadMessage)
        time.sleep(1)
main()