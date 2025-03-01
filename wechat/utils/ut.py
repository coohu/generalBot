from .. import *

def resQR():
    rq = auto.WindowControl(searchDepth=1, Name='微信', ClassName='CefWebViewWnd')
    if not rq.Exists(2):
        print("微信加入群链接未找到！")
        return
    rq.HyperlinkControl(Name='加入群聊').Click()
    time.sleep(random.uniform(0.5, 1.5))

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