const PokerColor = {
    Spade: 0,
    Heart: 1,
    Club: 2,
    Diamond: 3
};

const King = 53;
const Kinglet = 52;
const PokerColorChar = "♠♥♣♦";

function isJoker(value) {
    return value >= Kinglet;
}

function isRed(value) {
    return value % 2 == 1;
}

function getColor(value) {
    return value % 4;
}

function getPoint(value) {
    return parseInt(value / 4) + 1;
}

function getCardsString(cards) {
    str = '';
    for (const card of cards) {
        if(card == King)
            str += 'JOKER ';
        else if(card == Kinglet)
            str += 'joker ';
        else {
            s = getPokerString(card);
            str += s[0] + s[1] + ' ';
        }
    }
    return str;
}

function getPokerString(value) {
    if(isJoker(value))
        return "JOKER";
    var p = getPoint(value);
    var sym = PokerColorChar[getColor(value)];
    if(p == 10)
        return ["10", sym];
    return " A234567890JQK"[p] + sym;
}

/*
const HeartImg = document.getElementById("HeartImg");
const DiamondImg = document.getElementById("DiamondImg");
const SpadeImg = document.getElementById("SpadeImg");
const ClubImg = document.getElementById("ClubImg");
*/

function drawCard(which, x, y, width, height) {
    if(width == undefined) {
        width = pokerWidth;
        height = pokerHeight;
    }
    ctx.save();
    ctx.translate(x, y);
    // 边框
    ctx.strokeStyle = "black";
    ctx.fillStyle = "white";
    ctx.strokeRect(0, 0, width, height);
    ctx.fillRect(0, 0, width, height);
    // 设置颜色
    ctx.fillStyle = isRed(which) ? "red" : "black";
    // 中心
    if(isJoker(which)) {
        // TODO
    } else {
        ctx.font = pokerSymbolFont;
        ctx.textBaseline = "middle";
        ctx.textAlign = "center";
        ctx.fillText(PokerColorChar[getColor(which)], width / 2, height / 2);
    }
    // 字符
    ctx.font = pokerFont;
    ctx.textBaseline = "top";
    ctx.textAlign = "start";
    var str = getPokerString(which);
    for(var i = 0; i < str.length; i++)
        ctx.fillText(str[i], 0, pokerFontSize * i);
    ctx.translate(width, height);
    ctx.rotate(Math.PI);
    for(var i = 0; i < str.length; i++)
        ctx.fillText(str[i], 0, pokerFontSize * i);
    // 结束
    ctx.restore();
}

function drawCardBack(x, y, msg, width, height) {
    if(width == undefined) {
        width = pokerWidth;
        height = pokerHeight;
    }
    ctx.save();
    // 边框
    ctx.strokeStyle = "black";
    ctx.strokeRect(x, y, width, height);
    ctx.drawImage(cardback, x, y, width, height);
    if(msg != undefined) {
        ctx.font = pokerSymbolFont + "bold";
        ctx.strokeStyle = "white";
        ctx.lineWidth = 3;
        ctx.fillStyle = "black";
        ctx.textBaseline = "middle";
        ctx.textAlign = "center";
        ctx.strokeText(msg, x + width / 2, y + height / 2, width);
        ctx.fillText(msg, x + width / 2, y + height / 2, width);
    }
    // 结束
    ctx.restore();
}



// defaut functions, you can change it in your script

// 用于排序，没有别的作用，对局中的判定在服务器端进行
var pokerCompare = function(a, b) {
    var cmpVal = function(card) {
        var point = getPoint(card);
        if(point <= 2 || point == 14) {
            return card + King;
        } else {
            return card;
        }
    }
    var pa = cmpVal(a);
    var pb = cmpVal(b);
    if(pa > pb) return 1;
    if(pa == pb) return 0;
    return -1;
}