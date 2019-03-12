# cardgame
基于django-channels的网页纸牌游戏框架\
正在开发中，但目前已经可以正常运行
## 如何配置本项目
#### 需要安装的组件
- python3
- python3-pip
- django
- django-channels
- redis
- django-redis
- captcha
等，尚未整理完整安装本项目的全部流程
#### 需要进行的配置
在`qxsite/qxsite/settings.py`中设置你的邮箱服务器和域名，以及django SECRET_KEY等
## 如何添加新玩法
- 仿照本项目中的斗地主模块，在`qxsite/cardgame/`下新建python脚本，比如`examplefile.py`，设立一个`cardgame.Room`类的子类，比如`MyRoom`，重写你需要的方法。
- 在`qxsite/template/index.html`中添加一个`<select>`选项，让它的值为你的玩法名称，比如
```HTML
  <option value="example">示例</option>
```
- 在`qxsite/static/js/cardgame/`中添加一个js文件，重写`play.js`中你需要的方法，比如`example.js`，注意这个名称要与上面`<select>`的`value`值一样
- 修改`qxsite/cardgame/game_settings.py`，引用你的房间类，如：
```python3
from cardgame import examplefile

ROOM_TYPES = {
    ...
    'example': examplefile.MyRoom,
}
```
这里`ROOM_TYPES`的key要与上面`<select>`的`value`值一样
