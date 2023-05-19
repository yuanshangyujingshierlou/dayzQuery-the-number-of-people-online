from steam import game_servers as gs
import configData

# 返回服务器信息
def get_server():
    # 防止请求报错
    try:
        ip = configData.data['server_query_ip']
        server_addr = next(gs.query_master(rf'\gameaddr\{ip}'))  # get a single ip from hl2 master
        serverInfo = gs.a2s_info(server_addr)       # only accept goldsrc response
        ping = str(round(serverInfo['_ping'] * 10) / 10)
        player = str(serverInfo['players'])
        max_player = str(serverInfo['max_players'])
        keywords = str(serverInfo['keywords'])
        time = keywords.split(',')[-1]
        return {'ping': ping, 'player': player, 'max_player': max_player, 'time': time}
    except:
        return {}