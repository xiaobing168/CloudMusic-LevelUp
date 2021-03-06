#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@FILE    :   action.py
@DSEC    :   网易云音乐签到刷歌脚本
@AUTHOR  :   Secriy
@DATE    :   2020/08/25
@VERSION :   2.0
'''

import os
import sys
import requests
import base64
import json
import hashlib
import binascii
import codecs
from Crypto.Cipher import AES


class Encrypt:
    def __init__(self):
        self.modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
        self.nonce = '0CoJUm6Qyw8W8jud'
        self.pubKey = '010001'

    # Random String Generator
    def createSecretKey(self, size):
        return str(binascii.hexlify(os.urandom(size))[:16], encoding='utf-8')

    # AES Encrypt
    def aesEncrypt(self, text, secKey):
        pad = 16 - len(text) % 16
        text = text + pad * chr(pad)
        encryptor = AES.new(secKey.encode('utf8'), 2, b'0102030405060708')
        ciphertext = encryptor.encrypt(text.encode('utf8'))
        ciphertext = str(base64.b64encode(ciphertext), encoding='utf-8')
        return ciphertext

    # RSA Encrypt
    def rsaEncrypt(self, text, pubKey, modulus):
        text = text[::-1]
        rs = int(text.encode('utf-8').hex(), 16)**int(pubKey, 16) % int(
            modulus, 16)
        return format(rs, 'x').zfill(256)

    def encrypt(self, text):
        secKey = self.createSecretKey(16)
        encText = self.aesEncrypt(self.aesEncrypt(text, self.nonce), secKey)
        encSecKey = self.rsaEncrypt(secKey, self.pubKey, self.modulus)
        return {'params': encText, 'encSecKey': encSecKey}


class CloudMusic:
    def __init__(self):
        self.session = requests.Session()
        self.enc = Encrypt()
        self.headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
            "Referer": "http://music.163.com/",
            "Accept-Encoding": "gzip, deflate",
        }

    def login(self, phone, password):
        loginUrl = "https://music.163.com/weapi/login/cellphone"
        self.loginData = self.enc.encrypt(
            json.dumps({
                'phone': phone,
                'countrycode': '86',
                'password': password,
                'rememberLogin': 'true'
            }))
        headers = {
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36",
            "Referer":
            "http://music.163.com/",
            "Accept-Encoding":
            "gzip, deflate",
            "Cookie":
            "os=pc; osver=Microsoft-Windows-10-Professional-build-10586-64bit; appver=2.0.3.131777; channel=netease; __remember_me=true;"
        }
        res = self.session.post(url=loginUrl,
                                data=self.loginData,
                                headers=headers)
        ret = json.loads(res.text)
        if ret['code'] == 200:
            self.cookie = res.cookies
            self.csrf = requests.utils.dict_from_cookiejar(
                self.cookie)['__csrf']
            self.nickname = ret["profile"]["nickname"]
            print("\"{nickname}\" 登录成功，当前等级：{level}".format(
                nickname=self.nickname, level=self.getLevel()["level"]))
            self.beforeCount = self.getLevel()["nowPlayCount"]
            print("距离升级还需听{beforeCount}首歌".format(
                beforeCount=self.getLevel()["nextPlayCount"] -
                self.getLevel()["nowPlayCount"]))
        else:
            print("登录失败 " + str(ret['code']) + "：" + ret['message'])
            exit()

    def getLevel(self):
        url = "https://music.163.com/weapi/user/level?csrf_token=" + self.csrf
        res = self.session.post(url=url,
                                data=self.loginData,
                                headers=self.headers)
        ret = json.loads(res.text)
        return ret["data"]

    def sign(self):
        signUrl = "https://music.163.com/weapi/point/dailyTask"
        res = self.session.post(url=signUrl,
                                data=self.enc.encrypt('{"type":0}'),
                                headers=self.headers)
        ret = json.loads(res.text)
        if ret['code'] == 200:
            print("签到成功，经验+" + str(ret['point']))
        elif ret['code'] == -2:
            print("今天已经签到过了")
        else:
            print("签到失败 " + str(ret['code']) + "：" + ret['message'])

    def task(self, custom):
        url = "https://music.163.com/weapi/v6/playlist/detail?csrf_token=" + self.csrf
        recommendUrl = "https://music.163.com/weapi/v1/discovery/recommend/resource"
        if len(custom) == 0:
            res = self.session.post(url=recommendUrl,
                                    data=self.enc.encrypt('{"csrf_token":"' +
                                                          self.csrf + '"}'),
                                    headers=self.headers)
            ret = json.loads(res.text)
            if ret['code'] != 200:
                print("获取推荐歌曲失败 " + str(ret['code']) + "：" + ret['message'])
            else:
                lists = ret['recommend']
                musicLists = [(d['id']) for d in lists]
        else:
            musicLists = custom
        musicId = []
        for m in musicLists:
            res = self.session.post(url=url,
                                    data=self.enc.encrypt(
                                        json.dumps({
                                            'id': m,
                                            'n': 1000,
                                            'csrf_token': self.csrf
                                        })),
                                    headers=self.headers)
            ret = json.loads(res.text)
            for i in ret['playlist']['trackIds']:
                musicId.append(i['id'])
        postData = json.dumps({
            'logs':
            json.dumps(
                list(
                    map(
                        lambda x: {
                            'action': 'play',
                            'json': {
                                'download': 0,
                                'end': 'playend',
                                'id': x,
                                'sourceId': '',
                                'time': 300,
                                'type': 'song',
                                'wifi': 0
                            }
                        }, musicId[:340])))
        })
        res = self.session.post(
            url="http://music.163.com/weapi/feedback/weblog",
            data=self.enc.encrypt(postData))
        ret = json.loads(res.text)
        if ret['code'] == 200:
            afterCount = self.getLevel()["nowPlayCount"]
            print("刷听歌量成功，共{count}首".format(count=afterCount -
                                            self.beforeCount))
        else:
            print("刷听歌量失败 " + str(ret['code']) + "：" + ret['message'])
            exit(ret['code'])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("python3 action.py 手机号 密码MD5值32位 歌单1 歌单2 歌单3")
        exit()
    # Custom Music List
    customMusicList = []
    # Start
    app = CloudMusic()
    # pylint: disable=unbalanced-tuple-unpacking
    phone, passowrd = sys.argv[1:3]
    customMusicList += sys.argv[3:]
    print("=============================")
    try:
        # Login
        app.login(phone, passowrd)
        # Sign In
        app.sign()
        # Music Task
        app.task(customMusicList)
    except KeyboardInterrupt:
        print("=============================")
        exit()
    print("=============================")