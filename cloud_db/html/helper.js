/* 
    To build this, use ./build_helper.py
*/

var Address4 = require('ip-address').Address4;
var Address6 = require('ip-address').Address6;

ipToString = function(ip, v6) {
    if (v6) {
        ip = ip.address;
        ip = ip.split(':').map(x => x.replace(/^0+(.+?)$/,'$1')).join(':');
        ip = ip.replace(/\b:?(?:0+:?){2,}/, '::');
        return ip;
    } else {
        return ip.address;
    }
}

cidrToIPs = function(cidr) {
    if (cidr.includes(":")) {
        temp = new Address6(cidr);
        return [ipToString(temp.startAddress(), true), ipToString(temp.endAddress(), true)];
    } else {
        temp = new Address4(cidr);
        return [ipToString(temp.startAddress(), false), ipToString(temp.endAddress(), false)];
    }
}

ipToBits = function(ip) {
    if (ip.includes(":")) {
        return new Address6(ip).getBitsBase2();
    } else {
        return new Address4(ip).getBitsBase2();
    }
}
