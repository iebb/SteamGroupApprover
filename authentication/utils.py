import base64
import re
import xml.etree.ElementTree
import pickle
import requests
import steam, steam.webauth, steam.guard

from verifier.settings import STEAM_GROUP_ID, ACTOR_USERNAME, ACTOR_PASSWORD, ACTOR_SHARED_SECRET


def list_group_uids():
    result = []
    try:
        url = f"https://steamcommunity.com/gid/{STEAM_GROUP_ID}/memberslistxml/"
        tree = xml.etree.ElementTree.fromstring(
            requests.get(url).text
        )
        members = tree.find("members")
        for member in members:
            result.append(int(member.text))
    except:
        pass
    return result


def get_session():
    try:
        sess_cookies = pickle.load(open("sessionFile", "rb"))
        sess = requests.Session()
        sess.cookies.update(sess_cookies)

        return sess
    except:
        user = steam.webauth.WebAuth(ACTOR_USERNAME, ACTOR_PASSWORD)
        try:
            user.login()
        except steam.webauth.TwoFactorCodeRequired:
            user.login(twofactor_code=steam.guard.generate_twofactor_code(
                base64.b64decode(ACTOR_SHARED_SECRET.encode("u8"))
            ))
        except:
            return False
        pickle.dump(user.session.cookies, open("sessionFile", "wb+"))
        return user.session


def approve_to_group(steamid32):
    sess = get_session()
    if not sess:
        return False
    ret = sess.get(
        f"https://steamcommunity.com/gid/{STEAM_GROUP_ID}/joinRequestsManage")
    session_ids = re.findall('name="sessionID" value="([a-f0-9]+)"', ret.text)
    if not len(session_ids):
        raise Exception("Steam 故障，暂时无法登录")

    session_id = session_ids[0]

    approve_ids = list(
        map(int, re.findall('JoinRequests_ApproveDenyUser\( \'(\d+)\', 1 \)"', ret.text)))

    if steamid32 not in approve_ids:
        raise Exception(
            f"未查找到 Steam 加入申请。"
            f"请 <a href='https://steamcommunity.com/gid/{STEAM_GROUP_ID}/'>点击此处</a> 发送进组请求"
        )

    ret = sess.post(
        f"https://steamcommunity.com/gid/{STEAM_GROUP_ID}/joinRequestsManage",
        data={
            "rgAccounts[]": str(steamid32),
            "bapprove": "1",
            "sessionID": session_id
        })
    if int(ret.text) != 1:
        raise Exception("Steam 内部错误 [%d]" % int(ret.text))
    return True
