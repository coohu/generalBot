from .. import *

def saveMsg(parent, it):
    spk = it.ButtonControl(foundIndex=1, searchDepth=2)
    if spk.Exists(2):
        utils.safeClick(parent, spk, position='cc')
        print(f"{spk.Name} : {it.Name}")

        if utils.invite(parent):
            return
        cpf = utils.profile(parent)
        if not cpf:
            return
        # spk.SendKeys('{Esc}')
        # utils.safeClick(parent, parent, position='tl', offset_x=10, offset_y=10)
        xo = spk.BoundingRectangle.width()//2+6
        utils.clickOffset(xo*-1, 0)
        pst = db.Post.insert(session=session,
            user_id=glc['id'], 
            customer_id=cpf[1], 
            post_type = 'msg',
            headline=it.Name )
        if pst:
            print(f"成功保存消息: {pst.id}")
        else:
            print("保存消息失败")

def chat(parent):
    ctList = parent.ListControl(Name='会话')
    if not ctList.Exists(2):
        print("未找到会话: ListControl")
        return

    scroll_pattern = ctList.GetScrollPattern()
    if scroll_pattern:
        scroll_pattern.SetScrollPercent(-1, 0)
        time.sleep(random.uniform(1, 1.5))  

    for it in  ctList.GetChildren():
        mc = re.search(r"(\d+)条新消息$", it.Name)
        if not mc:
            continue 
        n = int(mc.group(1))*-1
        utils.scrollToIt(ctList, it)
        utils.safeClick(ctList, it, position='cc')
        msgs = parent.ListControl(Name='消息')
        if msgs.Exists(2): 
            for it in msgs.GetChildren()[n:]:
                utils.scrollToIt(msgs, it)
                saveMsg(parent, it)
