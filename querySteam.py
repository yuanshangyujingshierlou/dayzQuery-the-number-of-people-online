from steam import game_servers as gs

# 返回服务器信息
def get_server(ip):
    # 防止请求报错
    try:
        server_addr = next(gs.query_master(filter_text = '\gameaddr\{}'.format(ip)))
        serverInfo = gs.a2s_info(server_addr)
        ping = str(round(serverInfo['_ping'] * 10) / 10)
        player = str(serverInfo['players'])
        max_player = str(serverInfo['max_players'])
        keywords = str(serverInfo['keywords'])
        time = keywords.split(',')[-1]
        return {'ping': ping, 'player': player, 'max_player': max_player, 'time': time}
    except:
        return {}