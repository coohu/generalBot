from .. import *

def contact(parent, it):
    if it.Name in ['','企业微信通知','公众号','新的朋友'] :
        return
    elif it.Name == '新的朋友':
        newBtn = it.ButtonControl(searchDepth=2)
        if newBtn.Exists(2):
            utils.safeClick(parent, newBtn, 'cc', 0, 1)
            parent.ListControl(Name='新的朋友')
    try:
        btn = it.ButtonControl(searchDepth=2)
        utils.safeClick(parent, btn, 'tl', 2, 2,(0,0))
        utils.profile(parent)

    except Exception as e:
        print(e)

def contacts(wc):
    ccList = wc.ListControl(searchDepth=6, Name='联系人')
    if not ccList.Exists():
        print("未找到联系人: ListControl")
        return
    utils.scroll(wc,ccList,contact)

