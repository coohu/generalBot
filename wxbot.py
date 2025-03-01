import subprocess, json, time, random
import win32api, win32gui, win32con
from typing import List, Dict, Set
from datetime import datetime
import uiautomation as auto
import hashlib, re
import db.db as db
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=db.engine)
session = Session()

glc={
    'id':None,
    'wxid':None,
    'nick_name':None,
    'contact':None,
    'postDuplicate':False
}

def profile(parent):
    permission = None
    nick_name = None
    source = None
    status = None
    wxid=None
    addr=None
    ps = None

    def get_control_text(parent, label_name, found_index=2):
        try:
            sbn = parent.TextControl(Name=label_name)
            if sbn.Exists(1):
                sbv = sbn.GetParentControl().TextControl(foundIndex=found_index)
                if sbv.Exists(1):
                    return sbv.Name
            return None

        except Exception as e:
            # print(f"无法获取 '{label_name}' 的值: {e}")
            return None

    nick_name = get_control_text(parent, label_name='昵称：')
    wxid = get_control_text(parent, label_name='微信号：')
    addr = get_control_text(parent, label_name='地区：')

    ps = get_control_text(parent, label_name='备注')
    permission = get_control_text(parent, label_name='朋友权限') 
    source = get_control_text(parent, label_name='来源')  
    status = get_control_text(parent, label_name='个性签名')  
    permission = get_control_text(parent, label_name='朋友权限')  

    if not wxid : 
        return False
    if wxid in glc['contact']:
        return (wxid, glc['contact'].get(wxid))
    nc = db.Customer.insert(
        session = session, 
        user_id = glc['id'],
        wxid = wxid, 
        nick_name=nick_name if nick_name else ps,
        addr = addr,
        permission = permission,
        ps = ps,
        source = source,
        status = status
    )
    if nc:
        print(f"成功创建客户: {nc.id}   {nc.nick_name}")
        glc['contact'][wxid] = nc.id
        return (wxid, nc.id)
    else:
        print("创建客户失败")
        return False

def FindAll(ctl, ctlType=auto.ControlType.ButtonControl):
    rts = []
    if ctl.ControlType == ctlType:
        rts.append(ctl)
    for child in ctl.GetChildren():
        child_rts = FindAll(child, ctlType)
        rts.extend(child_rts)
    return rts

def closeWindow(win):
    for btn in FindAll(win):
        if btn.Name=="关闭" or btn.Name=="Close":
            safeClick(win, btn, position='cc', offset_x=1, offset_y=0)
            return True

    hwnd = win.NativeWindowHandle
    if not win32gui.IsWindow(hwnd):
        print(f"无效的窗口句柄: {hwnd}")
        return False
    
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception as e:
        print(f"关闭窗口失败: {e}")
        return False

def safeClick(parent, btn, position='tl', offset_x=2, offset_y=2, delay=(0.5, 2)):
    rect = btn.BoundingRectangle
    x = rect.left + offset_x
    y = rect.top + offset_y
    
    if position == 'tc':
        x = (rect.left + rect.right) // 2 + offset_x
        y = rect.top + offset_y
    elif position == 'tr':
        x = rect.right + offset_x
        y = rect.top + offset_y
    elif position == 'bl':
        x = rect.left + offset_x
        y = rect.bottom + offset_y
    elif position == 'bc':
        x = (rect.left + rect.right) // 2 + offset_x
        y = rect.bottom + offset_y
    elif position == 'br':
        x = rect.right + offset_x
        y = rect.bottom + offset_y
    elif position == 'cc':
        x = (rect.left + rect.right) // 2 + offset_x
        y = (rect.top + rect.bottom) // 2 + offset_y
    elif position == 'lc':
        x = rect.left + offset_x
        y = (rect.top + rect.bottom) // 2 + offset_y
    elif position == 'rc':
        x = rect.right + offset_x
        y = (rect.top + rect.bottom) // 2 + offset_y

    prect = parent.BoundingRectangle
    if (prect.left < x < prect.right and prect.top < y < prect.bottom):
        auto.Click(x, y)
        time.sleep(random.uniform(delay[0], delay[1]))
    else:
        print(f"坐标({x}, {y})超出父组件边界，禁止点击")

def clickOffset(x_offset, y_offset):
    """Click at a position relative to current cursor position"""
    current_x, current_y = win32api.GetCursorPos()
    target_x = current_x + x_offset
    target_y = current_y + y_offset
    
    # Move to target position
    auto.SetCursorPos(target_x, target_y)
    # Perform click
    auto.Click(target_x, target_y)
    time.sleep(random.uniform(0.5, 1.5))

def scrollToIt(list_ctl, it_ctl):
    list_rect = list_ctl.BoundingRectangle
    list_height = list_rect.height()
    list_top = list_rect.top
    list_bottom = list_rect.bottom
    
    item_rect = it_ctl.BoundingRectangle
    item_top = item_rect.top
    item_bottom = item_rect.bottom
    item_height = item_rect.height()
    
    scroll_pattern = list_ctl.GetScrollPattern()
    if not scroll_pattern:
        raise ValueError("ListControl没有Scroll模式")
    
    vertical_scroll_percent = scroll_pattern.VerticalScrollPercent
    vertical_view_size = scroll_pattern.VerticalViewSize
    vsr = 100 - vertical_view_size
    
    if (item_bottom < list_top) or (item_top > list_bottom):
        if item_bottom < list_top:
            relative_pos = (list_top - item_bottom) / list_height * vsr
            target_percent = max(0, vertical_scroll_percent - relative_pos)
        else:
            relative_pos = (item_top - list_bottom) / list_height * vsr
            target_percent = min(100, vertical_scroll_percent + relative_pos)

        scroll_pattern.SetScrollPercent(-1, target_percent)
        time.sleep(random.uniform(0.2, 1))

def imageView():
    rts = [None, None]
    imgWin = auto.WindowControl(searchDepth=1, Name='图片查看', ClassName='ImagePreviewWnd')
    if not imgWin.Exists(1):
        print("无法找到图片查看")
        return rts
    try:
        ext = imgWin.ButtonControl(Name='提取文字')
        safeClick(imgWin, ext, position='cc', offset_x=3, offset_y=2)
        ext = imgWin.TextControl(foundIndex=2)
        if ext.Exists(1):
            print(ext.Name)
            rts[1] = ext.Name

        ext = imgWin.ButtonControl(Name='识别图中二维码')
        if ext.Exists(1):
            safeClick(imgWin, ext, position='cc', offset_x=3, offset_y=2)
            qradd = imgWin.ButtonControl(Name='添加到通讯录')
            if qradd.Exists(1):
                safeClick(imgWin, qradd, position='cc')
                cfn = auto.WindowControl(ClassName='WeUIDialog', Name='添加朋友请求')
                if cfn.Exists(1):
                    cfnBtn = cfn.ButtonControl(searchDepth=3,  Name='确定')
                    if cfnBtn.Exists(1):
                        safeClick(cfn, cfnBtn, position='cc')
        return rts
        ext = imgWin.ButtonControl(Name='另存为...')
        safeClick(imgWin, ext, position='cc', offset_x=3, offset_y=2)

        saveBox = imgWin.WindowControl(ClassName="#32770", Name="另存为...")
        if not saveBox.Exists(2):
            print("无法找到另存为")
            closeWindow(imgWin)
            return rts

        editBox = saveBox.EditControl(ClassName="Edit", Name='文件名:')
        if not editBox.Exists(2):
            print("无法找到文件名编辑框")
            cancel = saveBox.ButtonControl(Name="取消")
            if not cancel.Exists(1):
                closeBox = saveBox.ButtonControl(Name="关闭")
                if closeBox.Exists(1):
                    safeClick(saveBox, closeBox, position='cc', offset_x=3, offset_y=2)
                closeWindow(imgWin)
                return rts
            safeClick(imgWin, cancel, position='cc', offset_x=3, offset_y=2)
            closeWindow(imgWin)
            return rts

        cfn = editBox.GetValuePattern().Value
        nfn = f"D:\\proj\\ai\\rpa\\{cfn}"
        editBox.SendKeys(nfn)
        time.sleep(random.uniform(1, 3.5))
        auto.SendKeys("{Alt}s")
        closeWindow(imgWin)
        rts[0] = nfn 
        return rts

    except Exception as e:
        print(e)
        return rts

def post(parent, it):
    try:
        poster = it.Name.split(':\n')
        wxid = None
        eis = []
        for btn in FindAll(it):
            if btn.Name == "图片" and False:
                safeClick(parent, btn, position='tc', offset_x=5, offset_y=13,delay=(2,4))
                eis.append(imageView())
            if btn.Name == poster[0] and not wxid:
                safeClick(parent, btn, position='tc', offset_x=5, offset_y=13,delay=(1,2))
                idlb = parent.TextControl(Name='微信号：')
                if not idlb.Exists(1):
                    return
                idlb = idlb.GetParentControl().TextControl(searchDepth=1, foundIndex=2)
                if not idlb.Exists(1):
                    return 
                wxid = idlb.Name
                if wxid == glc['wxid']:   # myself
                    return 
                if wxid not in glc['contact']:
                    profile(parent)
                safeClick(parent, parent, position='tc')
        
        if len(poster) < 2:
            return
        try:
            md5 = hashlib.md5(it.Name.encode('utf-8')).hexdigest()
            cid = glc['contact'].get(wxid)
            # print(cid, wxid, poster)
            pst = db.Post(user_id=glc['id'], customer_id=cid, post_type='post', md5=md5 , headline=poster[1])
            session.add(pst)
            session.commit()
            if pst:
                print(f"成功保存朋友圈: {pst.id}")
                for img in eis:
                    if img[0]:
                        db.Image.insert(session =session, post_id=pst.id, img=img[0], ocr_text=img[1])
            else:
                print("保存朋友圈失败")

        except IntegrityError as e:
            session.rollback()
            if "md5" in str(e) and "Duplicate" in str(e):
                glc['postDuplicate'] = True 

        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error inserting post: {str(e)}")
            return None

        return
        cmt = it.ButtonControl(searchDepth=5, Name='评论')
        if not cmt.Exists():
            return

        safeClick(parent, cmt, position='tl', offset_x=2, offset_y=2)
        toast = parent.PaneControl(searchDepth=1, ClassName='SnsLikeToastWnd')
        like = toast.ButtonControl(searchDepth=3, Name='赞')
        if not like.Exists():
            return
        # like.Click()
        # time.sleep(random.uniform(2.5, 4.5))
        safeClick(parent, like, position='tl', offset_x=5, offset_y=5)
        safeClick(parent, cmt, position='tl', offset_x=2, offset_y=2)

        toast = parent.PaneControl(searchDepth=1, ClassName='SnsLikeToastWnd')
        toast.ButtonControl(searchDepth=3, Name='评论').Click()
        time.sleep(random.uniform(2.5, 4.5))
        parent.EditControl(Name="评论").SendKeys('元宵节快乐！{Enter}')
        exit()

    except Exception as e:
        print(e)

def contact(parent, it):
    if it.Name in ['','企业微信通知','公众号','新的朋友'] :
        return
    elif it.Name == '新的朋友':
        newBtn = it.ButtonControl(searchDepth=2)
        if newBtn.Exists(2):
            safeClick(parent, newBtn, 'cc', 0, 1)
            parent.ListControl(Name='新的朋友')
    try:
        btn = it.ButtonControl(searchDepth=2)
        safeClick(parent, btn, 'tl', 2, 2,(0,0))
        profile(parent)

    except Exception as e:
        print(e)

def invite(parent):
    pfc = parent.ButtonControl(Name='添加到通讯录')
    if pfc.Exists(2):
        safeClick(parent, pfc, position='cc')
        cfn = parent.WindowControl(ClassName='WeUIDialog', Name='添加朋友请求')
        if cfn.Exists(2):
            cfnBtn = cfn.ButtonControl(searchDepth=3,  Name='确定')
            if cfnBtn.Exists(1):
                safeClick(cfn, cfnBtn, position='cc')
                return True 
    return False

def scroll(parent, list_ctl, func=None, method="key", amount=2):
    scroll_pattern = list_ctl.GetScrollPattern()
    if scroll_pattern:
        scroll_pattern.SetScrollPercent(-1, 0)
    # safeClick(parent, list_ctl, position='lc', offset_x=20, offset_y=0)
    rect = list_ctl.BoundingRectangle
    while True:
        current_items = list_ctl.GetChildren()
        if current_items:
            for item in current_items:
                if func is not None:
                    if func.__name__ =="post" and glc['postDuplicate']:
                        return 
                    func(parent, item)
                time.sleep(random.uniform(0.2, 1))

        print('//////////////////////////Page Down////////////////////////////')

        win32api.SetCursorPos(((rect.right+rect.left)//2, (rect.bottom+rect.top)//2))
        if method == "wheel":
            list_ctl.WheelDown(waitTime=0.5, wheelTimes=amount)
        
        elif method == "key":
            list_ctl.SetFocus()
            list_ctl.SendKeys('{PageDown}')
        
        elif method == "pattern":
            if scroll_pattern:
                cp = scroll_pattern.VerticalScrollPercent
                scroll_pattern.SetScrollPercent(-1, min(100, cp + 1))
        time.sleep(random.uniform(1, 1.5))                          # 等待滚动完成

        if scroll_pattern.VerticalScrollPercent >= 99.0 :
            print('scroll_pattern.VerticalScrollPercent', scroll_pattern.VerticalScrollPercent)
            break


def posts():
    ps = auto.WindowControl(searchDepth=1, Name='朋友圈', ClassName='SnsWnd')
    if not ps.Exists():
        print("未找到窗口")
        return
    ps.SetFocus()
    psList = ps.ListControl(searchDepth=4, Name='朋友圈')
    scroll(ps, psList, post, "wheel", 6)

def contacts(wc):
    ccList = wc.ListControl(searchDepth=6, Name='联系人')
    if not ccList.Exists():
        print("未找到联系人: ListControl")
        return
    scroll(wc,ccList,contact)

def userInfo(wc):
    profile = wc.PaneControl(searchDepth=1, ClassName='ContactProfileWnd')
    try:
        nick_name = profile.TextControl(foundIndex=1).Name
        wxid = profile.TextControl(foundIndex=3).Name
        addr = profile.TextControl(foundIndex=5).Name
        glc['wxid'] = wxid
        glc['nick_name'] = nick_name

        me = session.query(db.User).filter(db.User.wxid == wxid).first()
        if me:
            glc['id'] = me.id
            glc['contact'] ={cst.wxid:cst.id for cst in me.customers}
            print(glc,'-----------')
            return

        new_user = db.User.insert(session=session, wxid=wxid, last_run=datetime.now())
        if new_user:
            print(f"成功创建用户: {new_user.nick_name}")
            new_customer = db.Customer.insert(
                user_id=new_user.id,
                nick_name=nick_name,
                session=session, 
                wxid=wxid, 
                addr=addr
            )
            if new_customer:
                print(f"成功创建客户: {new_customer.nick_name}")
            else:
                print("创建客户失败")
        else:
            print("创建用户失败")

    except Exception as e:
        exit()
        print(e)

def resQR():
    rq = auto.WindowControl(searchDepth=1, Name='微信', ClassName='CefWebViewWnd')
    if not rq.Exists(2):
        print("微信加入群链接未找到！")
        return
    rq.HyperlinkControl(Name='加入群聊').Click()
    time.sleep(random.uniform(0.5, 1.5))

def search():
    ws = auto.PaneControl(searchDepth=1, Name='微信', ClassName='Chrome_WidgetWin_0')
    if not ws.Exists(2):
        print("微信搜一搜窗口未找到！")
        return
    try:
        ws.EditControl(AutomationId='weixin-search-input')
        ws.ButtonControl(Name='文章').Click()
        time.sleep(random.uniform(0.5, 1.5))
        ws.SetFocus()
        ws.SendKeys("上海妇科评论")
        time.sleep(random.uniform(0.5, 1.5))
        ws.ButtonControl(Name='搜索').Click()
        time.sleep(random.uniform(2.5, 3.5))
        ws.ButtonControl(Name='最新').Click()
        time.sleep(random.uniform(2.5, 3.5))
        itSet = set()
        for _ in range(random.randint(3,7)):
            res = ws.GroupControl(AutomationId='search_result').GroupControl(searchDepth=1)
            if res.Exists(2):
                for arBtn in res.GetChildren():
                    if arBtn.Name in itSet or arBtn.ControlType != auto.ControlType.ButtonControl :
                        continue
                    itSet.add(arBtn.Name)
                    print(arBtn.Name)
                    safeClick(ws, arBtn, position='cc')
                    for _ in range(random.randint(2, 4)):
                        ws.WheelDown(waitTime=0.5, wheelTimes=3)
                        time.sleep(random.uniform(2, 4))
                    tnBtn = ws.TabItemControl(foundIndex=2).ButtonControl(searchDepth=1, Name='关闭')
                    if tnBtn.Exists(2):
                        safeClick(ws, tnBtn, position='cc')
 
            if len(itSet) > 5:
                break

            ws.WheelDown(waitTime=0.5, wheelTimes=2)
            time.sleep(random.uniform(5, 10))

    except Exception as e:
        print(e)

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
        scrollToIt(listCtl, it)
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

def main():
    # wc = auto.WindowControl(ProcessName="WeChat") 
    wc = auto.WindowControl(searchDepth=1, ClassName='WeChatMainWndForPC')
    if not wc.Exists(2): # 2秒超时
        print("未找到微信窗口。")
        return
    try:
        wc.Restore()
        wc.SetActive()
        wc.SetFocus()

    except Exception as e:
        print(f"激活窗口失败: {str(e)}")
    
    nv = wc.ToolBarControl(searchDepth=4, Name= "导航")

    nv.ButtonControl(searchDepth=1).Click()             #hello, it's me
    time.sleep(random.uniform(0.5, 1.5))
    userInfo(wc)

    nv.ButtonControl(searchDepth=1, Name="通讯录").Click()
    time.sleep(random.uniform(0.5, 1.5))
    contacts(wc)

    nv.ButtonControl(searchDepth=1,Name="朋友圈").Click()
    time.sleep(random.uniform(0.5, 1.5))
    posts()

    nv.ButtonControl(searchDepth=3,Name="搜一搜").Click()
    time.sleep(random.uniform(0.5, 1.5))
    search()

    nv.ButtonControl(searchDepth=1,Name="聊天").Click()
    time.sleep(random.uniform(0.5, 1.5))
    ctList = wc.ListControl(Name='会话')
    if not ctList.Exists():
        print("未找到会话: ListControl")
        return
    msgScroll(wc, ctList, func=chat)

main()