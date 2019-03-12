from threading import Thread, Timer
from qxsite.settings import ROOM_TTL
import channels.layers
from asgiref.sync import async_to_sync
from django.core.cache import cache
from enum import Enum, unique
import asyncio
import random
import math
from asyncio import get_event_loop
from cardgame.log import log
from cardgame.cardtype import *

class GameException(Exception):
    def __init__(self, msg = 'unknown game exception'):
        self.msg = msg
    
    def __str__(self):
        return self.msg

# a function for customer
def create_room(room_class, room_id):
    room = room_class(room_id)
    async_to_sync(channels.layers.get_channel_layer().send)('room.' + room_id, {
        'type': 'hello',
    })
    room.start()
    return room

@unique
class PlayerState(Enum):
    Out = 0         # 房间外
    Waiting = 1     # 等待进入房间，或者重连后等待房间确认
    UnReady = 2     # 房间内，未准备
    Ready = 3       # 房间内，已准备，未开局
    Playing = 4     # 房间内，游戏中
    Finished = 5    # 房间内，已出局但游戏正在进行
    Watching = 6    # 旁观中

class Player:
    def __init__(self, id, name, channel_name):
        self.id = id
        self.name = name
        self.channel_name = channel_name
        self.state = PlayerState.UnReady
        self.cards = set()

class Room(Thread):
    def __init__(self, id):
        # 注册
        if not cache.set('room.' + id, True, nx = True, timeout = None):
            raise GameException('room in use')
        Thread.__init__(self)
        self.type = 'default'
        self.id = id
        self.players = []
        self.watchers = {}
        self.reset()

    def reset(self):
        for player in self.players:
            player.state = PlayerState.UnReady
            player.cards = set()
        self.turn = -1 # game not start yet
        self.remaining_cards = []
        self.last_cards = set() # 上次打出的牌（不包括pass）
        self.last_card_type = CardsType.Pass
        self.last_card_val = 0
        self.holder = -1        # 拥有牌权的人，通常指上次出牌的人（不包括pass）

    async def asnyc_run(self):
        self.layer = channels.layers.get_channel_layer()
        log('Room', self.id, 'created')
        # clean old messages until get a 'hello'
        while True:
            msg = await self.layer.receive('room.' + self.id)
            if msg['type'] == 'hello':
                break
        while True:
            self.killer = Timer(ROOM_TTL, self.kill)
            self.killer.start()
            msg = await self.layer.receive('room.' + self.id)
            self.killer.cancel()
            if await self.process_msg(msg):
                break
        log('Room', self.id, 'disbanded')


    def run(self):
        # fuck
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop = get_event_loop()
        loop.run_until_complete(self.asnyc_run())
        log('thread end')

    # return True while room is disbanding
    async def process_msg(self, msg):
        log('Room', self.id, 'get message:')
        log(msg)
        try:
            return await getattr(self, 'on_' + msg['type'], self.on_error_msg)(msg)
        except GameException as e:
            player = self.find_player_by_id(msg['id'])
            if player and player.channel_name:
                channel_name = player.channel_name
            elif 'channel' in msg:
                channel_name = msg['channel']
            else:
                raise GameException('got error message from people not in the room, error =' + e.msg)
            await self.post_msg_to(channel_name, {
                'msg': 'error',
                'error': str(e),
            })

    def find_player_by_id(self, id):
        for player in self.players:
            if player.id == id:
                return player
        return None

    def kill(self):
        async_to_sync(self.layer.send)('room.' + self.id, {'type': 'disband'})

    async def post_msg(self, context):
        context['type'] = 'room.msg'
        log('Room', self.id, 'post message:')
        log(context)
        await self.layer.group_send('room.' + self.id, context)

    async def post_msg_to(self, channel_name, context):
        context['type'] = 'room.msg'
        log('Room', self.id, 'post message to channel', channel_name, ':')
        log(context)
        await self.layer.send(channel_name, context)
    
    async def on_error_msg(self, msg):
        log('Room', self.id, 'error message:', msg)
        raise GameException('unknown backend message type: ' + str(msg['type']))

    async def on_disband(self, msg):
        cache.set('room.' + self.id, False)
        # 发布消息解散房间
        await self.post_msg({
            'msg': 'disband',
        })
        # 删除房间占用标志
        cache.delete('room.' + self.id)
        return True

    async def on_disconnect(self, msg):
        uid = msg['id']
        player = self.find_player_by_id(uid)
        player.channel_name = None
        await self.post_msg({
            'msg': 'disconnect',
            'id': uid,
        })

    async def on_reconnect(self, msg):
        uid = msg['id']
        channel_name = msg['channel']
        log('on reconnect, uid =', uid, 'channel =', channel_name)
        player = self.find_player_by_id(uid)
        if player == None:
            log('player == None')
            raise GameException('not in room')
        else:
            if player.channel_name:
                await self.post_msg_to(player.channel_name, {
                    'msg': 'downlined',
                })
            player.channel_name = channel_name
            await self.post_msg({
                'msg': 'reconnect',
                'id': uid,
                'state': player.state.value,
                'room_type': self.type,
            })
            await self.post_msg_to(player.channel_name, self.get_situation_msg(player))

    def get_situation_msg(self, player):
        s = self.get_situation(player)
        s['msg'] = 'situation'
        return s
    
    # 获取player眼中的局面
    # 应当重载
    def get_situation(self, player):
        return {
            'player': [{
                'id': p.id,
                'name': p.name,
                'state': p.state.value,
                'card_count': len(p.cards), # 只显示count
            } for p in self.players],
            # TODO: watchers
            'turn': self.turn,
            'cards': list(player.cards),
            'last_cards': list(self.last_cards),
        }

    async def on_enter(self, msg):
        uid = msg['id']
        name = msg['name']
        channel_name = msg['channel']
        for player in self.players:
            if player.id == uid:
                raise GameException('already in room')
        if self.turn != -1:
            raise GameException('room already playing')
        self.players.append(Player(uid, name, channel_name))
        await self.post_msg({
            'msg': 'enter',
            'id': uid,
            'name': name,
            'type': self.type
        })

    async def change_ready_state(self, msg, value):
        if self.turn != -1:
            raise GameException('game is playing')
        uid = msg['id']
        player = self.find_player_by_id(uid)
        if player == None:
            raise GameException('not in room')
        player.state = value
        await self.post_msg({
            'msg': 'change_state',
            'id': uid,
            'state': value.value
        })

    async def on_ready(self, msg):
        await self.change_ready_state(msg,PlayerState.Ready)
        # 只有一人不能开局
        if len(self.players) <= 1:
            return
        # 检查是否都ready了
        for player in self.players:
            if player.state != PlayerState.Ready:
                return
        # 对局开始
        await self.start_game()

    async def on_unready(self, msg):
        await self.change_ready_state(msg, PlayerState.UnReady)

    async def on_leave(self, msg):
        player = self.find_player_by_id(msg['id'])
        if player == None:
            raise GameException('not in room')
        if player.state == PlayerState.Playing:
            raise GameException('游戏期间不允许离开房间')
        self.players.remove(player)
        await self.post_msg({
            'msg': 'leave',
            'id': player.id,
        })
        if len(self.players) == 0:
            return await self.on_disband(msg)

    async def start_game(self):
        # 洗牌
        self.wash_cards()
        # 发牌
        all_count = len(self.remaining_cards)
        avr = math.floor(all_count / len(self.players))
        mod = all_count % len(self.players)
        start = 0
        for i, player in enumerate(self.players):
            if i < mod:
                end = start + avr + 1
            else:
                end = start + avr
            player.cards = set(self.remaining_cards[start:end])
            player.state = PlayerState.Playing
            start = end
        self.remaining_cards = []
        # 指定第一个出牌的人
        self.turn = random.randint(0, len(self.players) - 1)
        self.holder = self.turn
        self.last_cards = set()
        # 发布消息
        await self.post_start_msg()

    async def post_start_msg(self):
        card_count = {p.id: len(p.cards) for p in self.players}
        for player in self.players:
            if player.channel_name != None:
                await self.post_msg_to(player.channel_name, {
                    'msg': 'start',
                    'turn': self.turn,
                    'card_count': card_count,
                    'cards': list(player.cards),
                })


    # 玩家打出或选中牌
    async def on_select_card(self, msg):
        uid = msg['id']
        cur = self.players[self.turn]
        if uid != cur.id:
            raise GameException('not your turn')
        card_list = msg['cards']
        cards = set(card_list)
        if not cards <= cur.cards:
            # 打出的牌不都是手牌中存在的
            raise GameException('cards not owned by you')
        if not self.try_select(cards):
            raise GameException('不能这样出牌')
        # 从player手中删除这些牌
        for c in card_list:
            cur.cards.remove(c)
        # 设置局面
        if len(card_list) != 0:
            self.holder = self.turn
        while True:
            self.turn += 1
            if self.turn == len(self.players):
                self.turn = 0
            if self.players[self.turn].state == PlayerState.Playing:
                break
            if self.turn == self.holder:
                # 此时，又轮到holder出牌，但是holder已经出光了，所以推风
                self.holder += 1
                if self.holder == len(self.players):
                    self.holder = 0
        # 发送消息
        await self.post_msg({
            'msg': 'select_card',
            'cards': card_list,
            'turn': self.turn,
        })        
        if len(cur.cards) == 0:
            # 玩家已经胜出
            await self.player_finish(cur)

    async def player_finish(self, player):
        player.state = PlayerState.Finished
        await self.post_msg({
            'msg': 'finish',
            'id': player.id,
        })
        # 检查游戏是否结束
        loser = None
        for p in self.players:
            if p.state == PlayerState.Playing:
                if loser == None:
                    loser = p
                else:
                    return
        await self.game_over(loser)

    async def game_over(self, loser):
        # 删除已经离场（state=Out）的玩家
        self.players = [player for player in self.players if player.state == PlayerState.Finished]
        self.reset()
        await self.post_msg({
            'msg': 'game_over',
            'loser': loser.name,
        })
    
    # 返回是否成功
    def try_select(self, cards):
        if len(cards) == 0:
            # 玩家跳过
            return self.turn != self.holder
        # 普通打法
        type, val = self.get_cards_type(cards)
        if type == CardsType.Error:
            return False
        if type == CardsType.Dragon and len(cards) < 3:
            return False
        if type == CardsType.DoubleDragon and len(cards) < 6:
            return False
        if self.holder == self.turn:
            # if type != CardsType.Pass:  # 没必要判断，上面判断过了
            self.last_card_type = type
            self.last_card_val = val
            self.last_cards = cards
            return True
            # else:
            #     return False
        if type == self.last_card_type:
            if type == CardsType.Dragon or type == CardsType.DoubleDragon:
                if len(cards) != len(self.last_cards):
                    return False
            if point_compare(self.last_card_val, val) == -1:
                self.last_card_val = val
                self.last_cards = cards
                return True
            else:
                return False
        if type in {
            CardsType.Single: [CardsType.Triple, CardsType.Quad, CardsType.Jokers],
            CardsType.Double: [CardsType.Triple, CardsType.Quad, CardsType.Jokers],
            CardsType.Dragon: [CardsType.Triple, CardsType.Quad, CardsType.Jokers],
            CardsType.DoubleDragon: [CardsType.Quad, CardsType.Jokers],
            CardsType.Triple: [CardsType.Quad, CardsType.Jokers],
            CardsType.Jokers: [CardsType.Quad],
            CardsType.Quad: [],
        }.get(self.last_card_type, []):
            self.last_card_type = type
            self.last_card_val = val
            self.last_cards = cards
            return True
        else:
            return False
        

    # 获得牌组类型
    def get_cards_type(self, cards):
        pt = [get_card_point(card) for card in cards]
        pt.sort()
        for type, method in {
            CardsType.Pass:     get_pass_val,
            CardsType.Single:   get_single_val,
            CardsType.Double:   get_double_val,
            CardsType.Triple:   get_triple_val,
            CardsType.Quad:     get_quad_val,
            CardsType.Jokers:   get_jokers_val,
            CardsType.Dragon:   get_dragon_val,
            CardsType.DoubleDragon: get_double_val,
        }.items():
            val = method(pt)
            if val != None:
                return type, val
        return CardsType.Error, 0

    def all_cards(self):
        return range(54)

    # 从all_cards生成随机序列填入remaining_cards
    # 注意这个函数不会清理场上其他地方的牌（如玩家手牌），请自行清理
    def wash_cards(self):
        self.remaining_cards = []
        for card in self.all_cards():
            i = random.randint(0, card)
            if i == card:
                self.remaining_cards.append(card)
            else:
                self.remaining_cards.append(
                    self.remaining_cards[i]
                    )
                self.remaining_cards[i] = card
                

