import os
import time
import requests
import shutil

url = 'https://tucdn.wpon.cn/api-girl/index.php?wpon=json'
meinv_number = 100


# 请求随机美女链接
def get_meinv_url():
    r = requests.get(url)
    return r.json()['mp4']


# 下载美女视频
def download_meinv():
    try:
        # 判断是否超过了下载次数
        meinvlist = []
        if os.path.exists('meinv.cfg'):
            with open('meinv.cfg', 'r') as f:
                line = f.readline()
                while line:
                    meinvlist.append(line)
                    line = f.readline()
        if len(meinvlist) >= meinv_number:
            # 删除最早的一个文件
            os.remove('./meinv/{}.mp4'.format(meinvlist[0].split('\n')[0]))

        mnurl = get_meinv_url()
        r = requests.get('https:' + mnurl)
        # 随机生成文件名
        filename = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        with open('.\meinv\{}.mp4'.format(filename), 'wb') as f:
            f.write(r.content)
        # 下载成功一次记录一次
        with open('meinv.cfg', 'a') as f:
            f.write(filename + '\n')
        return 'D:/dayz/dayz_miraiBot/meinv/{}.mp4'.format(filename)
    except Exception as e:
        return None
