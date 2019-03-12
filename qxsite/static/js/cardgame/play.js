var messages;
var canvas;
var action_table, actions;
var confirm_select = null; // 确认选中或出牌按钮
var ctx;
var pokerWidth, pokerHeight;
var pokerFontSize, pokerFont, pokerSymbolFont;
var cardback, friendImg;
var turn = -1;
var my_turn = -1;
var my_state = 1;
var my_name;
var select_start = -1;

// player state
const PlayerState = {
    Out: 0,
    Waiting: 1,
    UnReady: 2,
    Ready: 3,
    Playing: 4,
    Finished: 5,
    Watching: 6,
};

// 场上区域
var myAreaWidth, myAreaHeight, myAreaLeft, myAreaTop;
var centerAreaWidth, centerAreaHeight, centerAreaLeft, centerAreaTop;

// 当前持有的牌
var myCards = [];
// 出牌区的牌
var centerAreaCards = [];
// 同局好友
var friends = [];
class friend {
    constructor(id, name, state, card_count) {
        this.id = id;
        this.name = name;
        this.state = state;
        this.card_count = card_count;
        this.history = [];
    }
}

function loadImage(url) {
    var img = new Image();
    img.onload = function() {
        rePaint();
    };
    img.src = url;
    return img;
}

function initialize() {
    // initialize canvas and 2D context
    canvas = document.getElementById("canvas");
    messages = document.getElementById("messages");
    actions = document.getElementById("actions");
    action_table = document.getElementById("action-table");
    if(canvas.getContext == undefined) {
        alert("浏览器不支持Canvas，请更换较新版本的浏览器");
        return;
    }
    ctx = canvas.getContext('2d');
    onResize();
    window.addEventListener("resize", onResize);
    window.addEventListener("beforeunload", onBeforeUnload);
    canvas.addEventListener("mousedown", function(e){ onMouse(e, true); });
    canvas.addEventListener("mouseup", function(e){ onMouse(e, false); });
}

function onMouse(e, is_down) {
    var x = e.clientX;
    var y = e.clientY;
    if(is_down)
        select_start = -1;
    if(x >= myAreaLeft && x <= myAreaLeft + myAreaWidth && y >= myAreaTop) {
        onMouse_MyArea(x, y, is_down);
    }
}

function clearActionSelects() {
    actions.innerHTML = '';
    confirm_select = null;
}

// return the button you add
function addActionSelect(title, handle) {
    td = document.createElement('td');
    td.align = 'center';
    button = document.createElement('button');
    button.innerText = title;
    button.addEventListener('click', handle);
    td.appendChild(button);
    actions.appendChild(td);
    return button;
}

var setActionsWhenOnMyTurn = function () {
    confirm_select = addActionSelect('出牌', function() {
        sendMsgSelectCard();
        unselectAll();
    });
    confirm_select.disabled = canSelect();
    // TODO: 判断你是否有牌权
    addActionSelect('不出', function() {
        unselectAll();
        sendMsgSelectCard();
    });
}

function setActions() {
    // action selects
    clearActionSelects();
    switch (my_state) {
        case PlayerState.Ready:
            addActionSelect('取消准备', sendMsgUnready);
            addActionSelect('离开', sendMsgLeaveRoom);
            break;
        case PlayerState.UnReady:
            addActionSelect('准备', sendMsgReady);
            addActionSelect('离开', sendMsgLeaveRoom);
            break;
        case PlayerState.Playing:
            if(turn == my_turn)
                setActionsWhenOnMyTurn();
            break;
        case PlayerState.Finished:
            addActionSelect('离开', sendMsgLeaveRoom);
            break;
        default:
            break;
    }
}

function onResize() {
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    // poker setting
    pokerWidth = Math.floor(canvas.width / 16);
    pokerHeight = Math.round(pokerWidth / 0.65);
    pokerFontSize = Math.max(Math.round(pokerWidth / 4), 10);
    pokerFont = pokerFontSize.toString() + "px sans-serif";
    pokerSymbolFont = Math.max(Math.round(pokerWidth / 1.5), 20).toString() + "px sans-serif";
    // area setting
    myAreaWidth = pokerWidth + 30 * pokerFontSize;
    myAreaHeight = Math.ceil(pokerHeight * 1.5) + pokerFontSize;
    myAreaTop = canvas.height - myAreaHeight;
    myAreaLeft = (canvas.width - myAreaWidth) / 2;

    centerAreaWidth = myAreaWidth;
    centerAreaHeight = myAreaHeight;
    centerAreaTop = Math.min((canvas.height - centerAreaHeight) / 2,
        myAreaTop - centerAreaHeight - pokerHeight / 2);
    centerAreaLeft = myAreaLeft;

    // action table
    action_table.style.top = myAreaTop - pokerHeight / 4;

    rePaint();
}

function addMessage(msg) {
    messages.innerText += msg + "\n";
    messages.scrollTop=messages.scrollHeight;
}

function rePaint() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    paintMyArea();
    paintCenterArea();
    paintFriends();
}

function paintFriends() {
    // TODO: clear areas
    for (var i = 0; i < friends.length; i++) {
        paintFriend(i, friends[i]);
    }
}

function addFriend(id, name, state, card_count) {
    var f = new friend(id, name, state, card_count);
    friends.push(f);
    paintFriend(friends.length - 1, f);
}

function paintFriend(n, f) {
    var dy = pokerFontSize + pokerHeight;
    var y = n * dy;
    var count = f.card_count > 3 ? 4 : f.card_count;
    ctx.clearRect(0, y, dy, dy);
    if(count > 0) {
        var i;
        for(i = 0; i < count - 1; i++)
            drawCardBack(i * pokerFontSize, y);
        drawCardBack(i * pokerFontSize, y, f.card_count.toString());
    } else {
        if(friendImg)
            ctx.drawImage(friendImg, 0, y, pokerHeight, pokerHeight);
    }
    ctx.save();
    // on turn
    if((turn < my_turn && turn == n) || (turn > my_turn && turn == n + 1)) {
        var w;
        if(count == 0)
            w = pokerHeight;
        else
            w = (count - 1) * pokerFontSize + pokerWidth;
        ctx.strokeStyle = "gold";
        ctx.lineWidth = 3;
        ctx.strokeRect(0, y, w, pokerHeight);
    }
    ctx.fillStyle = "black";
    ctx.textAlign = "start";
    ctx.textBaseline = "top";
    ctx.font = pokerFont;
    ctx.fillText(f.name, 0, y + pokerHeight);
    ctx.restore();
}

function paintCenterArea() {
    ctx.clearRect(centerAreaLeft, centerAreaTop, centerAreaWidth, centerAreaHeight);
    y0 = centerAreaTop + Math.floor(pokerHeight / 4);
    if(centerAreaCards.length < 10) {
        var x = (canvas.width - pokerWidth - (centerAreaCards.length - 1) * pokerFontSize) / 2;
        for (var i = 0; i < centerAreaCards.length; i++) {
            drawCard(centerAreaCards[i], x + i * pokerFontSize, y0);
        }
    } else {
        var upSize = Math.ceil(centerAreaCards.length / 2);
        var x = (canvas.width - pokerWidth - (upSize + 1) * pokerFontSize) / 2;
        var y0 = centerAreaTop + 1;
        for (var i = 0; i < upSize; i++) {
            drawCard(centerAreaCards[i], x + i * pokerFontSize, y0);
        }
        x = (canvas.width - pokerWidth - (centerAreaCards.length - upSize - 1) * pokerFontSize) / 2;
        y0 = centerAreaTop + Math.floor(pokerHeight / 2);
        for (var i = upSize; i < centerAreaCards.length; i++) {
            drawCard(centerAreaCards[i], x + (i - upSize) * pokerFontSize, y0);
        }
    }
}

function paintMyArea() {
    ctx.clearRect(myAreaLeft, myAreaTop, myAreaWidth, myAreaHeight);
    y0 = myAreaTop + Math.floor(pokerHeight / 4);
    if(myCards.length < 30) {
        var x = (canvas.width - pokerWidth - (myCards.length - 1) * pokerFontSize) / 2;
        for (var i = 0; i < myCards.length; i++) {
            drawCard(myCards[i][0], x + i * pokerFontSize, y0 + (myCards[i][1] ? 1 : pokerFontSize));
        }
    } else {
        var upSize = Math.floor(myCards.length / 2);
        var x = (canvas.width - pokerWidth - (upSize - 1) * pokerFontSize) / 2;
        var y0 = myAreaTop;
        for (var i = 0; i < upSize; i++) {
            drawCard(myCards[i][0], x + i * pokerFontSize, y0 + (myCards[i][1] ? 1 : pokerFontSize));
        }
        x = (canvas.width - pokerWidth - (myCards.length - upSize - 1) * pokerFontSize) / 2;
        y0 = myAreaTop + Math.floor(pokerHeight / 2);
        for (var i = upSize; i < myCards.length; i++) {
            drawCard(myCards[i][0], x + (i - upSize) * pokerFontSize, y0 + (myCards[i][1] ? 1 : pokerFontSize));
        }
    }
}

// 抓牌
function getCard(card) {
    var i;
    for(i = 0; i < myCards.length; i++) {
        if(pokerCompare(myCards[i][0], card) == 1) {
            break;
        }
    }
    myCards.splice(i, 0, [card, false]);
    paintMyArea();
}

// 选中第i张手牌
function selectMyCard(from, to) {
    if(from < 0)
        return;
    for(var i = from; i <= to; i++)
        myCards[i][1] = !myCards[i][1];
    // 设置出牌按钮是否灰显
    if(confirm_select) {
        confirm_select.disabled = canSelect();
    }
    paintMyArea();
}

function setTurn(t) {
    var last_turn = turn;
    turn = t;
    if(last_turn >= 0) {
        // 去掉on_turn标志
        if(last_turn < my_turn)
            paintFriend(last_turn, friends[last_turn]);
        else if(last_turn > my_turn)
            paintFriend(last_turn - 1, friends[last_turn - 1]);
    }
    clearActionSelects();
    if(turn == my_turn) {
        setActionsWhenOnMyTurn();
    } else {
        if(turn < 0)
            return;
        if(turn < my_turn)
            paintFriend(turn, friends[turn]);
        else
            paintFriend(turn - 1, friends[turn - 1]);
    }
}

// 事件响应
function onMouse_MyArea(x, y, is_down) {
    if(myCards.length < 30) {
        var ymin = myAreaTop + Math.floor(pokerHeight / 4);
        var ymax = myAreaTop + Math.floor(pokerHeight * 1.25) + pokerFontSize;
        if(y < ymin || y > ymax)
            return;
        var w = pokerWidth + (myCards.length - 1) * pokerFontSize;
        var xmin = (canvas.width - w) / 2;
        var xmax = (canvas.width + w) / 2;
        if(x >= xmin && x <= xmax) {
            var i = Math.floor((x - xmin) / pokerFontSize);
            if(i >= myCards.length) {
                i = myCards.length - 1;
            }
            if(is_down)
                select_start = i;
            else {
                if(i < select_start)
                    selectMyCard(i, select_start);
                else
                    selectMyCard(select_start, i);
            }
        }
    } else {
        var y0 = myAreaTop + Math.floor(pokerHeight / 2);
        var y1 = y0 + pokerFontSize;
        var upSize = Math.floor(myCards.length / 2);
        // 判断是否为下边一排
        var w = pokerWidth + (myCards.length - upSize - 1) * pokerFontSize;
        var xmin = (canvas.width - w) / 2;
        var xmax = (canvas.width + w) / 2;
        if(x >= xmin && x <= xmax) {
            var i = Math.floor((x - xmin) / pokerFontSize);
            i += upSize;
            if(i >= myCards.length) {
                i = myCards.length - 1;
            }
            if(myCards[i][1] ? y >= y0 : y >= y1) {
                if(is_down)
                    select_start = i;
                else
                    selectMyCard(select_start, i);
                return;
            }
        }
        // 判断是否为上边一排
        w = pokerWidth + (upSize - 1) * pokerFontSize;
        xmin = (canvas.width - w) / 2;
        xmax = (canvas.width + w) / 2;
        if(x >= xmin && x <= xmax) {
            var i = Math.floor((x - xmin) / pokerFontSize);
            if(i >= upSize) {
                i = upSize - 1;
            }
            if(y < y1) {
                if(is_down)
                    select_start = i;
                else
                    selectMyCard(select_start, i);
                return;
            }
        }
    }
}

function onBeforeUnload() {
    var msg = '你将离开此页面，但不会退出房间。';
    alert(msg);
    return msg;
}

function getSelectedCards() {
    selected = [];
    for (const card of myCards) {
        if(card[1])
            selected.push(card[0]);
    }
    return selected;
}

function unselectAll() {
    for(var i = 0; i < myCards.length; i++)
        myCards[i][1] = false;
    if(confirm_select) {
        confirm_select.disabled = false;
    }
    paintMyArea();
}

// 返回当前选中的牌是否合法，特别地，不出被认为是不合法的
function canSelect() {
    // TODO
    return false;
}