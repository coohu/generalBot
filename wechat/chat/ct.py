from .. import *

def saveMsg(parent, it):
    spk = it.ButtonControl(foundIndex=1, searchDepth=2)
    if spk.Exists(2):
        safeClick(parent, spk, position='cc')
        print(f"{spk.Name} : {it.Name}")

        if invite(parent):
            return
        cpf = profile(parent)
        if not cpf:
            return
        # safeClick(parent, parent, position='tl', offset_x=10, offset_y=10)
        pst = db.Post.insert(session=session,
            user_id=glc['id'], 
            customer_id=cpf[1], 
            post_type = 'msg',
            headline=it.Name )
        if pst:
            print(f"成功保存消息: {pst.id}")
        else:
            print("保存消息失败")

def msgScroll(parent, listCtl, func=None, lastN=None):
    scroll_pattern = listCtl.GetScrollPattern()
    if scroll_pattern:
        scroll_pattern.SetScrollPercent(-1, 0)

    items = listCtl.GetChildren()[lastN:] if lastN is not None else listCtl.GetChildren()
    if not items or func==None:
        return 
    for it in items:
        utils.scrollToIt(listCtl, it)
        func(parent, it)

def chat(parent, it):
    mc = re.search(r"(\d+)条新消息$", it.Name)
    if not mc:
        return 

    safeClick(parent, it, position='cc')
    n = int(mc.group(1))*-1
    msgs = parent.ListControl(Name='消息')
    if msgs.Exists(2): 
        msgScroll(parent, msgs, func=saveMsg, lastN=n)