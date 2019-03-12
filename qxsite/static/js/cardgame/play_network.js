var my_id;
var connecting = document.getElementById('connecting');

var iobusy = {};
iobusy.off = function() {
    connecting.style.visibility = 'visible';
};
iobusy.on = function() {
    connecting.style.visibility = 'hidden';
};

msg_listener = {
    '_open': function(){
        iobusy.on();
    },
    '_close': function() {
        iobusy.off();
    },
    'connect': function(data) {
        my_id = data['id'];
    },
    'enter': function(data) {
        id = data['id'];
        name = data['name'];
        addMessage(name + ' 进入了房间');
        if(id != my_id) {
            addFriend(id, name, PlayerState.UnReady, 0);
        }
    },
    'error': function(data) {
        alert(data['error']);
    },
    'reconnect': function(data) {
        // TODO
    },
    'disband': function(data) {
        alert('房间已解散');
        window.location = '/cardgame';
    },
    'situation': function(data) {
        friends = [];
        players = data['player'];
        for (var i in players) {
            player = players[i];
            if(player['id'] == my_id) {
                my_turn = i;
                my_state = player['state'];
                my_name = player['name'];
            }
            else
                addFriend(player['id'], player['name'], player['state'], player['card_count']);
        }
        setTurn(data['turn']);
        myCards = [];
        for (const card of data['cards']) {
            getCard(card);
        }
        centerAreaCards = data['last_cards'];
        rePaint();
        setActions();
    },
    'game_over': function(data) {
        addMessage('本局游戏结束，' + data['loser'] + '被抓了！');
        addMessage('');
        alert('游戏结束！');
        myCards = [];
        centerAreaCards = [];
        my_state = PlayerState.UnReady;
        for (const f of friends) {
            f.state = PlayerState.UnReady;
        }
        setActions();
        rePaint();
    },
    'change_state': function(data) {
        if(data['id'] == my_id) {
            my_state = data['state'];
            setActions();
        } else {
            for (const f of friends) {
                if(f.id == data['id']) {
                    f.state = data['state'];
                    // TODO: 画面
                    break;
                }
            }
        }
    },
    'start': function(data) {
        addMessage('游戏开始');
        setTurn(data['turn']);
        // TODO romove left ones
        for (const f of friends) {
            f.card_count = data['card_count'][f.id];
        }
        myCards = [];
        rePaint();
        cards = data['cards'];
        i = 0;
        interval = setInterval(function() {
            getCard(cards[i]);
            i += 1;
            if(i == cards.length) {
                clearInterval(interval);
            }
        }, 100);
    },
    'select_card': function(data) {
        cards = data['cards'];
        if(cards.length != 0) {
            if(turn < my_turn) {
                friends[turn].card_count -= cards.length;
                paintFriend(turn, friends[turn]);
            } else if(turn > my_turn) {
                friends[turn - 1].card_count -= cards.length;
                paintFriend(turn - 1, friends[turn - 1]);
            }
            centerAreaCards = cards;
            paintCenterArea();
            addMessage(getCurrentPlayerName() + ' 打出了 ' + getCardsString(cards));
        } else {
            addMessage(getCurrentPlayerName() + ' 跳过');
        }
        if(turn == my_turn) {
            after = [];
            for (const card of myCards) {
                if(cards.indexOf(card[0]) == -1) {
                    after.push(card);
                }
            }
            myCards = after;
            paintMyArea();
        }
        setTurn(data['turn']);
    },
    'finish': function(data) {
        var id = data['id'];
        if(id == my_id){
            addMessage('你已完成');
        } else {
            for (const player of friends) {
                if(player.id == id) {
                    addMessage(player.name + ' 已完成');
                    break;
                }
            }
        }
        setActions();
        // TODO
    },
    'chat': function(data) {
        addMessage(data['speaker'] + ': ' + data['context']);
    },
    'leave': function(data) {
        if('id' in data) {
            for(var i = 0; i < friends.length; i++) {
                if(friends[i].id == data['id']) {
                    addMessage(friends[i].name + ' 离开了房间');
                    friends.splice(i, 1);
                    break;
                }
            }
            rePaint();
        } else {
            window.location.href = '/cardgame/';
        }
    }
}

function sendMsgSelectCard() {
    var cards = [];
    for (const card of myCards) {
        if(card[1]) {
            cards.push(card[0]);
        }
    }
    sendJson({
        'msg': 'select card',
        'cards': cards,
    })
}

function getCurrentPlayerName() {
    var name;
    if(turn == my_turn)
        name = my_name;
    else if(turn > my_turn)
        name = friends[turn - 1].name;
    else
        name = friends[turn].name;
    return name;
}

function sendMsgLeaveRoom() {
    sendJson({
        'msg': 'leave room',
    })
}

function sendMsgReady() {
    sendJson({
        'msg': 'ready'
    })
}

function sendMsgUnready() {
    sendJson({
        'msg': 'unready'
    })
}

connect();