# dayzQuery-the-number-of-people-online
玩dayz大概半年多，因为各种原因自己开了个服务器，然后有些玩家要求需要播报击杀和查询在线人数，就自己做了个qq机器人。<br>用的是mirai框架，是一位大佬的开源qq登录框架，很感谢大佬的项目<br>
本项目使用方法：<br>
1.先打开那个Start.cmd，加载完后输入qrLogin 机器人qq，然后会跳出来一个二维码，扫码登录<br>
2.用mirai登录好机器人qq后，打开mirai\mirai\config\net.mamoe.mirai-api-http\下的config文件，把http端口改成你要使用的端口，这个端口要记下来，host就填127.0.0.1或者你的局域网ip或者你的公网ip或者localhost<br>
3.然后打开dayzOnlineNumber文件夹下的config.cfg文件，把里面的server_url改成你刚刚设置的mirai的http端口格式大概是http:127.0.0.1:8080,其他配置按需修改就行了<br>大概就是群号，机器人qq，以及服务器ip，还有dayz的服务端绝对路径，<br>改好之后回到父目录下启动bot.bat文件就可以了，如果有什么报错应该是配置文件没改对，可以参考下我的配置文件，记得不要用我的ip和端口，会冲突的
