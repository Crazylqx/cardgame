var landlord = -1;
var score = 0;

var _msg_situation = msg_listener['situation'];
msg_listener['situation'] = function(data) {
    landlord = data['landlord'];
    score = data['score'];
    _msg_situation(data);
};

msg_listener['game_over'] = function(data) {
    addMessage('本局游戏结束，' + (data['is_landlord_win'] ? '地主' : '农民') + '获胜');
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
};

msg_listener['elect_landlord'] = function(data) {
    var score = data['score'];
    if(score == 0) {
        addMessage(getCurrentPlayerName() + '不叫')
    } else {
        addMessage(getCurrentPlayerName() + '叫地主：' + data['score'] + '分')
    }
    setTurn(data['turn']);
}

msg_listener['landlord_elected'] = function(data) {
    cards = data['cards'];
    score = data['score'];
    centerAreaCards = cards;
    setTurn(data['landlord']);
    addMessage(getCurrentPlayerName() + ' 成为地主，分数：' + data['score']);
    paintCenterArea();
    addMessage('地主获得手牌：' + getCardsString(cards));
}

var _setActionsWhenOnMyTurn = setActionsWhenOnMyTurn;
var setActionsWhenOnMyTurn = function () {
    if(score == 0) {
        // 仍未叫地主
        addActionSelect('不叫', function() {
            sendJson({
                'msg': 'elect landlord',
                'score': 0,
            })
        });
        addActionSelect('1分', function() {
            sendJson({
                'msg': 'elect landlord',
                'score': 1,
            })
        });
        addActionSelect('2分', function() {
            sendJson({
                'msg': 'elect landlord',
                'score': 2,
            })
        });
        addActionSelect('3分', function() {
            sendJson({
                'msg': 'elect landlord',
                'score': 3,
            })
        });
    } else {
        _setActionsWhenOnMyTurn();
    }
}