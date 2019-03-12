from cardgame.room import *
from cardgame.cardtype import *

class FuckLandlordRoom(Room):
    def __init__(self, id):
        super().__init__(id)
        self.type = 'fucklandlord'
        self.last_winner = 0
        self.cur_score = 0
        self.landlord = -1

    def reset(self):
        self.cur_score = 0
        self.landlord = -1
        return super().reset()

    def get_situation(self, player):
        s = super().get_situation(player)
        s['score'] = self.cur_score
        s['landlord'] = self.landlord
        return s

    async def on_enter(self, msg):
        uid = msg['id']
        name = msg['name']
        channel_name = msg['channel']
        for player in self.players:
            if player.id == uid:
                raise GameException('already in room')
        if self.turn != -1:
            raise GameException('room already playing')
        if len(self.players) >= 3:
            raise GameException('房间已满')
        self.players.append(Player(uid, name, channel_name))
        await self.post_msg({
            'msg': 'enter',
            'id': uid,
            'name': name,
            'room_type': self.type,
        })

    async def on_ready(self, msg):
        await self.change_ready_state(msg, PlayerState.Ready)
        # 房间未满
        if len(self.players) != 3:
            return
        # 检查是否都ready了
        for player in self.players:
            if player.state != PlayerState.Ready:
                return
        # 对局开始
        await self.start_game()
    
    async def start_game(self):
        # 洗牌
        self.wash_cards()
        # 发牌
        start = 0
        for i, player in enumerate(self.players):
            end = start + 17
            player.cards = set(self.remaining_cards[start:end])
            player.state = PlayerState.Playing
            start = end
        self.remaining_cards = self.remaining_cards[51:54]
        # 指定第一个出牌的人
        self.turn = self.last_winner
        self.cur_score = 0
        self.landlord = -1
        self.last_cards = set()
        await self.post_start_msg()

    async def on_elect_landlord(self, msg):
        uid = msg['id']
        cur = self.players[self.turn]
        if uid != cur.id:
            raise GameException('not your turn')
        score = msg['score']
        if score > self.cur_score:
            self.cur_score = score
            self.holder = self.turn
        if self.turn == 2:
            self.turn = 0
        else:
            self.turn += 1
        await self.post_msg({
            'msg': 'elect_landlord',
            'score': score,
            'turn': self.turn,
        })
        if self.turn == 0:
            if self.cur_score == 0:
                # 没人叫地主
                await self.start_game()
            else:
                self.landlord = self.holder
                self.turn = self.holder
                await self.post_msg({
                    'msg': 'landlord_elected',
                    'landlord': self.landlord,
                    'score': self.cur_score,
                    'cards': self.remaining_cards,
                })
                self.remaining_cards = []

    async def on_select_card(self, msg):
        if self.landlord == -1:
            raise GameException('请等待叫地主完成')
        await super().on_select_card(msg)
    
    async def player_finish(self, player):
        player.state = PlayerState.Finished
        await self.post_msg({
            'msg': 'finish',
            'id': player.id,
        })
        self.last_winner = self.players.index(player)
        await self.game_over(self.last_winner == self.landlord)

    async def game_over(self, is_landlord_win):
        self.players = [player for player in self.players if player.state == PlayerState.Finished]
        self.reset()
        await self.post_msg({
            'msg': 'game_over',
            'is_landlord_win': is_landlord_win,
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
        if type == CardsType.Dragon and len(cards) < 5:
            return False
        if type == CardsType.DoubleDragon and len(cards) < 6:
            return False
        if self.holder == self.turn:
            self.last_card_type = type
            self.last_card_val = val
            self.last_cards = cards
            return True
        if type == self.last_card_type:
            if type == CardsType.Dragon or type == CardsType.DoubleDragon or is_plane_type(type):
                if len(cards) != len(self.last_cards):
                    return False
            if point_compare(self.last_card_val, val) == -1:
                self.last_card_val = val
                self.last_cards = cards
                return True
            else:
                return False
        if type in {
            CardsType.Single: [CardsType.Quad, CardsType.Jokers],
            CardsType.Double: [CardsType.Quad, CardsType.Jokers],
            CardsType.Dragon: [CardsType.Quad, CardsType.Jokers],
            CardsType.DoubleDragon: [CardsType.Quad, CardsType.Jokers],
            CardsType.Jokers: [],
            CardsType.Quad: [CardsType.Jokers],
            CardsType.Plane3With0: [CardsType.Quad, CardsType.Jokers],
            CardsType.Plane3With1: [CardsType.Quad, CardsType.Jokers],
            CardsType.Plane3With2: [CardsType.Quad, CardsType.Jokers],
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
            CardsType.Quad:     get_quad_val,
            CardsType.Jokers:   get_jokers_val,
            CardsType.Dragon:   get_dragon_val,
            CardsType.DoubleDragon: get_double_val,
            CardsType.Plane3With0: get_plane3with0_val,
            CardsType.Plane3With1: get_plane3with1_val,
            CardsType.Plane3With2: get_plane3with2_val,
        }.items():
            val = method(pt)
            if val != None:
                return type, val
        return CardsType.Error, 0