#封装GET和POST请求
import requests
import json
import time
import miraiCsv
import test

qq_group = 572933068
qq_number = 270488994
server_url = "http://114.239.11.69:18080/"
session_key = ""


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


def post(url, api,data):
    url = url + api
    headers = {
        "Content-Type": "application/json"
    }
    data = data
    respomse = requests.post(url, headers=headers, json=data)
    text = respomse.text
    return text


# 获取认证接口
def post_verify():
    global session_key
    # 读取本地csv文件
    csv_text = miraiCsv.read_csv()
    if(csv_text):
        print('读取成功')
        session_key = csv_text[0]
    else:
        print('读取失败')
        # 获取认证接口
        api = "verify"
        # 填写verifyKey
        data = {"verifyKey": 1234567890}
        # 获取认证接口
        obj = json.loads(post(server_url, api, data))
        if obj["code"] == 0:
            # 保存sessionKey到本地csv文件
            miraiCsv.save_to_csv(obj["session"])
            session_key = obj["session"]
            print("认证成功")

    # 绑定sessionKey到指定QQ
    post_bind()




# 绑定sessionKey到指定QQ
def post_bind():
    api = "bind"
    data = {"sessionKey": session_key, "qq": qq_number}
    obj = json.loads(post(server_url, api, data))
    if obj["code"] != 0:
        print("绑定失败", "错误代码:", obj["code"])
    return obj


# 获取会话信息
def get_sessionInfo():
    api = "sessionInfo"
    data = {"sessionKey": session_key}
    obj = json.loads(get(server_url, api, data))
    print(obj["data"]["sessionKey"])
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
    else :
        print(obj["data"])
    return obj


# 筛选消息，回复指定群的指定消息
def get_messageFilter(data):
    boo = False
    obj = data['data'][0]
    # 判断消息类型
    if obj['type'] == 'GroupMessage': # 群消息
        # 判断是否是指定群
        if obj['sender']['group']['id'] == qq_group:
            # 判断是否是AT
            messageChain = obj['messageChain'] 
            for i in messageChain:
                if i['type'] == 'At' :
                    # 判断是否是AT机器人
                    if i['target'] == qq_number:
                        boo = True
                        continue
                if boo: # 是AT机器人
                    # 判断是否是指定消息
                    print(i['type'],i['text'])
                    if i['type'] == 'Plain' and i['text'] == ' 在线人数':
                        getServerText = test.get_server()
                        if getServerText:
                            # 回复消息
                            print(getServerText)
                            post_sendMessage(qq_group, getServerText)
                        else :
                            print('获取服务器信息失败')
                        break


# 发送单挑消息
def post_sendMessage(target, text):
    api = "sendGroupMessage"
    messageChain = [{"type": "Plain", "text": text}]
    data = {"sessionKey": session_key, "target": target, "messageChain": messageChain}
    obj = json.loads(post(server_url, api, data))
    if obj["code"] != 0:
        print("发送消息失败", "错误代码:", obj["code"])
    return obj



# 入口函数
def main():
    # 获取认证接口
    post_verify()

    # 查看消息队列
    while True:
        obj = get_message()
        if obj["data"] > 0:
            # 获取消息队列头部消息
            fetchMessageObj = get_fetchMessage(10)
            if fetchMessageObj['code'] == 0:
                # 筛选消息，回复指定群的指定消息
                get_messageFilter(fetchMessageObj)
            else :
                print('获取消息队列头部消息失败', '错误代码:', fetchMessageObj['code'])
        time.sleep(1)
main()