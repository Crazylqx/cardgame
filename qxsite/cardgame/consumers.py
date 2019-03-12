from channels.generic.websocket import JsonWebsocketConsumer
from login.views import get_online_user_id
import json
from cardgame.game_settings import *
from cardgame.room import GameException, PlayerState
from cardgame import room
from asgiref.sync import async_to_sync
from django.core.cache import cache
import traceback
from qxsite.settings import USER_TTL
from cardgame.log import log


# 以下方法用于获取从网络上获得的JSON中的指定字段
# 如果字段非法，则产生一个GameException
def get_room_id(context):
    room_id = context['room'].strip()
    id_len = len(room_id)
    if id_len > 16:
        raise GameException('room id too long')
    if id_len == 0:
        raise GameException('room id empty')
    if not room_id.encode('UTF-8').isalnum():
        raise GameException('房间号只能由数字或字母组成')
    return room_id

class GameConsumer(JsonWebsocketConsumer):
    # call when connect
    # load from cache and write channel name to cache
    def load_from_cache(self):
        user_key = 'user.' + str(self.user_id)
        user_cache = cache.get(user_key)
        user_cache['channel_name'] = self.channel_name
        cache.set(user_key, user_cache, timeout = USER_TTL)
        self.name = user_cache.get('name')
        self.state = user_cache.get('player_state', PlayerState.Out)
        self.room_id = user_cache.get('room_id')
        log(self.name + 'loaded from cache, state = ' + str(self.state))

    # call when disconnect
    # save user_state to cache and delete 'channel_name'
    def save_to_cache(self):
        user_key = 'user.' + str(self.user_id)
        user_cache = cache.get(user_key)
        user_cache['player_state'] = self.state
        log(self.name + 'saved to cache, state = ' + str(self.state))
        user_cache['room_id'] = self.room_id
        if 'channel_name' in user_cache:
            del user_cache['channel_name']
        cache.set(user_key, user_cache, timeout = USER_TTL)

    def try_reconnect_to_room(self):
        room_key = 'room.' + self.room_id
        # 房间仍然存在
        self.state = PlayerState.Waiting
        # 监听
        async_to_sync(self.channel_layer.group_add)(room_key, self.channel_name)
        if not cache.get(room_key):
            self.leave_room()
            # 房间不存在或已经解散
        else:
            self.send_msg_to_room({
                'type': 'reconnect',
                'channel': self.channel_name,
            })
        
    # TODO 异地登录导致下线后信息同步问题
    def connect(self):
        session = self.scope['session']
        user_id = get_online_user_id(session)
        if user_id:
            self.accept()
            self.user_id = user_id
            self.load_from_cache()
            log('connect: user', self.name)
            self.send_json({
                'msg': 'connect',
                'id': self.user_id,
            })
            # 尝试连接房间（房间将下线同id的连接）
            if self.state != PlayerState.Out:
                log('try reconnect to room')
                self.try_reconnect_to_room()
        else:
            self.user_id = None
            self.accept()
            self.close(code = 4233)

    def disconnect(self, close_code):
        if self.user_id == None:
            return
        if self.room_id != None:
            self.send_msg_to_room({
                'type': 'disconnect',
            })
        self.save_to_cache()

    def receive_json(self, context):
        if len(context) == 0:
            self.send_json({})
            return
        try:
            log('recieve json from', self.name, ':')
            log(context)
            msg = context['msg']
            if msg in GameConsumer.msg_listener:
                GameConsumer.msg_listener[msg](self, context)
            else:
                self.send_error('type error: ' + msg)
        except KeyError as e:
            self.send_error('key error: ' + e.args[0])
        except GameException as e:
            self.send_error(str(e))
        except Exception:
            self.send_error('unkown server error')
            traceback.log_exc()

    def send_error(self, msg):
        log('send error to', self.name, ':', msg)
        self.send_json({
            'msg': 'error',
            'error':  msg
        })

    def check_out_of_room(self):
        if self.state != PlayerState.Out:
            if self.state == PlayerState.Waiting:
                raise GameException('server busy')
            raise GameException('already in room')
            
    # create room
    def on_msg_create_room(self, context):
        self.check_out_of_room()
        room_id = get_room_id(context)
        room_type = context['room_type']
        if room_type not in ROOM_TYPES:
            raise GameException('unknown room type')
        room.create_room(ROOM_TYPES[room_type], room_id)
        self.enter_room(room_id)
        self.room_id = room_id
        self.send_json({
            'msg': 'room created',
            'room': self.room_id,
        })
    
    # enter room
    def on_msg_enter_room(self, context):
        self.check_out_of_room()
        room_id = get_room_id(context)
        self.enter_room(room_id)

    def enter_room(self, room_id):
        room_key = 'room.' + room_id
        self.state = PlayerState.Waiting
        # 先收听频道，以获得频道解散消息
        log(self.name, 'add group:', room_key)
        async_to_sync(self.channel_layer.group_add)(room_key, self.channel_name)
        self.room_id = room_id
        if not cache.get(room_key):
            self.leave_room()
            # 房间不存在或已经解散
            raise GameException('room not exist')
        self.send_msg_to_room({
            'type': 'enter',
            'name': self.name,
            'channel': self.channel_name,
        })

    # leave room
    def on_msg_leave_room(self, context):
        if self.state == PlayerState.Out:
            raise GameException('not in room')
        self.send_msg_to_room({
            'type': 'leave'
        })

    def on_msg_select_card(self, context):
        if self.state != PlayerState.Playing:
            raise GameException('not playing')
        self.send_msg_to_room({
            'type': 'select_card',
            'cards': context['cards'],
        })

    def on_msg_elect_landlord(self, context):
        if self.state != PlayerState.Playing:
            raise GameException('not playing')
        self.send_msg_to_room({
            'type': 'elect_landlord',
            'score': context['score'],
        })
    
    def send_msg_to_room(self, context):
        context['id'] = self.user_id
        async_to_sync(self.channel_layer.send)('room.' + self.room_id, context)

    # 监听后端消息
    def room_msg(self, event):
        log(self.name, 'get msg from room:')
        log(event)
        if event['msg'] == 'error' and event['error'] == 'not in room':
            self.leave_room()
            return
        # 设置状态改变
        if 'id' in event and event['id'] == self.user_id:
            state = {
                'enter': PlayerState.UnReady,
                'watch': PlayerState.Watching,
                'finish': PlayerState.Finished,
            }.get(event['msg'], None)
            if state == None and event['msg'] == 'reconnect':
                state = PlayerState(event.get('state'))
            if event['msg'] == 'change_state':
                state = PlayerState(event['state'])
            if state != None:
                self.state = state
                log('set state', state)
        if event['msg'] == 'start':
            self.state = PlayerState.Playing
        # 被下线
        if event['msg'] == 'downlined':
            self.close(code = 4111)
            return
        # 如果房间解散，被禁止加入房间或者主动离场，则离开
        if event['msg'] == 'disband' \
            or (event['msg'] == 'leave' and event['id'] == self.user_id) \
            or (self.state == PlayerState.Waiting and event['msg'] == 'error'):
            self.leave_room()
        elif self.state == PlayerState.Waiting:
            # 尚未进入房间，其他消息与你无关
            return
        # 向客户端发送消息
        context = event.copy()
        context.pop('type')   # 这是Room与Customer传递消息用的，与客户端无关
        self.send_json(context)

    # 当获悉自己从房间离开时，调用此方法
    def leave_room(self):
        async_to_sync(self.channel_layer.group_discard)('room.' + self.room_id, self.channel_name)
        self.room_id = None
        self.state = PlayerState.Out
        self.send_json({
            'msg': 'leave'
        })

    def on_msg_ready(self, _):
        self.send_msg_to_room({
            'type': 'ready'
        })

    def on_msg_unready(self, _):
        self.send_msg_to_room({
            'type': 'unready'
        })

    def on_msg_chat(self, context):
        async_to_sync(self.channel_layer.group_send)('room.' + self.room_id, {
            'type': 'room.msg',
            'msg': 'chat',
            'speaker': self.name,
            'context': context['context'],
        })

    msg_listener = {
        'create room': on_msg_create_room,
        'enter room': on_msg_enter_room,
        'leave room': on_msg_leave_room,
        'select card': on_msg_select_card,
        'ready': on_msg_ready,
        'unready': on_msg_unready,
        'chat': on_msg_chat,
        # 斗地主
        'elect landlord': on_msg_elect_landlord,
    }

