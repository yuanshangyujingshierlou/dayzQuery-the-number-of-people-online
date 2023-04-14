import hashlib
import base64


steamid = "76561199195074858" # 你的steamid
hash_object = hashlib.sha256() # 创建一个sha256对象
# 编码
steamid = steamid.encode()
hash_object.update(steamid) # 传入你的steamid
hash_value = hash_object.digest() # 获取16进制的摘要
b64_value = base64.b64encode(hash_value) # base64编码
# 把/替换成_ 把+替换成-
b64_value = b64_value.decode().replace("/", "_").replace("+", "-")
print(b64_value)