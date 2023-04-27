import csv
import os


# 读取本地csv文件
def read_mirai_csv():
    # 判断文件是否存在
    if os.path.exists('./data.csv'):
        with open('./data.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                return row        # 返回读取到的数据
    else:
        return False


# 存数据到本地csv文件
def save_mirai_csv(data):
    # 如果文件不存在，就创建一个 data.csv 文件
    with open('./data.csv', 'a', encoding='utf-8') as f:
        f.write(data)
        f.close()

# 删除本地csv文件
def remove_mirai_csv():
    if os.path.exists('./data.csv'):
        os.remove('./data.csv')