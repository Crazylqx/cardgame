from enum import Enum, unique
import math


# 牌组类型
@unique
class CardsType(Enum):
    Error = -1  # 不符合规则
    Pass = 0    # 过
    Single = 1  # 单
    Double = 2  # 对
    Triple = 3  # 炸（三个）
    Quad = 4    # 轰（四个）
    Jokers = 5  # 对王
    Dragon = 6  # 单龙
    DoubleDragon = 7    # 双龙
    Plane3With0 = 8     # 飞机（包括单独的三个的)，带0
    Plane3With1 = 9     # 飞机，带单
    Plane3With2 = 10    # 飞机，带双


def is_plane_type(type):
    return type.value >= CardsType.Plane3With0.value and type.value <= CardsType.Plane3With2.value

def get_card_point(card):
    if card == 53:
        return 15
    return math.floor(card / 4) + 1

def get_dragon_next(point):
    if point > 2 and point < 13:
        return point + 1
    elif point == 13:
        return 1
    else:
        return -1   # 连不下去了

def point_compare(point1, point2):
    def cmpval(point):
        if point <= 2 or point == 14:
            return point + 14
        else:
            return point
    v1 = cmpval(point1)
    v2 = cmpval(point2)
    if v1 > v2:
        return 1
    elif v1 == v2:
        return 0
    else:
        return -1


def card_compare(card1, card2):
    return point_compare(get_card_point(card1), get_card_point(card2))

# 牌型判断和大小获取
def get_pass_val(pt):
    if len(pt) == 0:
        return 0

def get_single_val(pt):
    if len(pt) == 1:
        return pt[0]

def get_jokers_val(pt):
    if len(pt) == 2 and pt[0] == 14 and pt[1] == 15:
        return 0

def get_double_val(pt):
    if len(pt) == 2 and pt[0] == pt[1]:
        return pt[0]

def get_triple_val(pt):
    if len(pt) == 3 and pt[0] == pt[1] and pt[0] == pt[2]:
        return pt[0]

def get_quad_val(pt):
    if len(pt) == 4 and pt[0] == pt[1] and pt[0] == pt[2] and pt[0] == pt[3]:
        return pt[0]

def get_dragon_val(pt):
    v = pt[0]
    for val in pt:
        if val != v:
            return
        v = get_dragon_next(v)
    return pt[0]

def get_double_dragon_val(pt):
    if len(pt) % 2 == 1:
        return
    v = pt[0]
    for i, val in enumerate(pt):
        if val != v:
            return
        if i % 2 == 1:
            v = get_dragon_next(v)
    return pt[0]


def get_plane3with0_val(pt):
    if len(pt) % 3 != 0:
        return
    v = pt[0]
    for i, val in enumerate(pt):
        if val != v:
            return
        if i % 3 == 2:
            v = get_dragon_next(v)
    return pt[0]

def get_plane3with1_val(pt):
    if len(pt) % 4 != 0:
        return
    triples = []
    singles = []
    i = 0
    while i < len(pt):
        if i < len(pt) - 2 and pt[i] == pt[i + 1] and pt[i] == pt[i + 2]:
            triples.append(pt[i]) 
            i += 3
        else:
            singles.append(pt[i])
            i += 1
    if len(triples) == len(singles):
        # 带的东西必须不一样
        i = 0
        while i < len(singles) - 1:
            if singles[i] == singles[i + 1]:
                return
        return get_dragon_val(triples)

def get_plane3with2_val(pt):
    if len(pt) % 4 != 0:
        return
    triples = []
    doubles = []
    i = 0
    while i < len(pt):
        if i < len(pt) - 2 and pt[i] == pt[i + 1] and pt[i] == pt[i + 2]:
            triples.append(pt[i]) 
            i += 3
        elif i < len(pt) - 1 and pt[i] == pt[i + 1]:
            doubles.append(pt[i])
            i += 2
        else:
            return
    if len(triples) == len(doubles):
        # 带的东西必须不一样
        i = 0
        while i < len(doubles) - 1:
            if doubles[i] == doubles[i + 1]:
                return
        return get_dragon_val(triples)