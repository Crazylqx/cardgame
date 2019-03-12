var create_mode = false;
var my_id;
var enter_tag = document.getElementById('enter_tag');
var create_tag = document.getElementById('create_tag');
var submit = document.getElementById('submit');
var p_type = document.getElementById('p_type');
var room_type = document.getElementById('room_type');
var room_id = document.getElementById('room_id');
var connecting = document.getElementById('connecting');

function set_mode(is_create_mode) {
    if(is_create_mode) {
        create_mode = true;
        document.title = "创建房间";
        submit.innerText = "创建"
        create_tag.style.fontSize = "120%";
        create_tag.style.color = "black";
        enter_tag.style.fontSize = "100%";
        enter_tag.style.color = "gray";
        p_type.style.visibility = "visible";
    } else {
        create_mode = false;
        document.title = "加入房间";
        submit.innerText = "加入"
        enter_tag.style.fontSize = "120%";
        enter_tag.style.color = "black";
        create_tag.style.fontSize = "100%";
        create_tag.style.color = "gray";
        p_type.style.visibility = "hidden";
    }
}

enter_tag.addEventListener('click', function(e) {
    set_mode(false);
});

create_tag.addEventListener('click', function(e) {
    set_mode(true);
});

submit.addEventListener('click', function(e) {
    iobusy.on()
    if(create_mode) {
        sendJson({
            'msg': 'create room',
            'room': room_id.value,
            'room_type': room_type.value,
        });
    } else {
        sendJson({
            'msg': 'enter room',
            'room': room_id.value,
        })
    }
})

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
        iobusy.off()
    },
    'connect': function(data) {
        my_id = data['id']
    },
    'error': function(data) {
        alert(data['error']);
    },
    'enter': function(data) {
        if(data['id'] == my_id) {
            window.location = 'play?type=' + data['room_type'];
        }
    },
    'reconnect': function(data) {
        if(data['id'] == my_id) {
            window.location = 'play?type=' + data['room_type'];
        }
    },
    'create': function(data) {
        console.log('房间创建成功');
    },
    'disband': function(data) {
        alert('房间已解散');
    }
}

set_mode(false);
connect();