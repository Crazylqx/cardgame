/**
 * 调用此脚本时，需要定义msg_listener，格式为
 * msg_listener = {
 *      'some type': function(data) { ... },
 *      ...
 * }
 */

const heart_check_timeout = 10000;
const reconnect_interval = 2000;

var socket;
var lock_reconnect;
var ws_url = 'ws://' + window.location.host + '/ws/cardgame/';
var timeout_obj = null, server_timeout_obj = null;

if (!('WebSocket' in window)) {
    alert('浏览器版本过低，请更换浏览器');
}

function connect() {
    try {
        socket = new WebSocket(ws_url);
        setSocketEventHandle();
        lock_reconnect = false;
    } catch (e) {
        reconnect(ws_url);
    }
}

function reconnect() {
    if(lock_reconnect)
        return;
    lock_reconnect = true;
    setTimeout(connect, reconnect_interval);
}

function resetHeartCheck() {
    clearTimeout(timeout_obj);
    clearTimeout(server_timeout_obj);
    timeout_obj = setTimeout(beat, heart_check_timeout);
}

function beat() {
    sendJson({});
    server_timeout_obj = setTimeout(function() {
        socket.close(); // 自动重连随之启动
    }, heart_check_timeout);
}

function setSocketEventHandle() {
    socket.onmessage = function(e) {
        resetHeartCheck();
        if(e.data == '{}')  // 心跳包
            return;
        var data = JSON.parse(e.data);
        // console.log(data);
        type = data['msg'];
        if(type in msg_listener)
            msg_listener[type](data);
    };
    socket.onopen = function(e) {
        msg_listener['_open']();
        resetHeartCheck();
    }
    socket.onclose = function(e) {
        if(e.code == 4233)
            window.location.href = '/login/?next=/cardgame/';
        if(e.code == 4111) {
            alert('您在其他位置登录了游戏，如非本人操作则您已被盗号，请联系系统管理员');
            window.location.gref = '/';
        }
        msg_listener['_close']();
        reconnect();
    };
    socket.onerror = function(e) {
        reconnect();
    }
}

function sendJson(json) {
    if(socket.readyState == 1)
        socket.send(JSON.stringify(json));
}