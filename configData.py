data = {}


# 读取配置文件 赋值给data
def read_config():
    global data
    with open("config.cfg", "r", encoding="utf-8") as file:
        line = file.readline()
        while line:
            # 过滤掉注释和空行
            if line.find("=") == -1 or line.startswith("#"):
                line = file.readline()
                continue
            key = line.split(" = ")[0]
            # value带有""，需要去掉
            value = line.split(" = ")[1].rstrip("\n").replace('"', "").replace("\\", "/").replace("/n", "\n")
            # 判断value是不是数字
            if value.isdigit():
                value = int(value)
            data[key] = value
            line = file.readline()
    return data