from .. import *

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
        ws.SendKeys("加群")
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
                    utils.safeClick(ws, arBtn, position='cc')
                    for _ in range(random.randint(2, 4)):
                        ws.WheelDown(waitTime=0.5, wheelTimes=3)
                        time.sleep(random.uniform(2, 4))
                    tnBtn = ws.TabItemControl(foundIndex=2).ButtonControl(searchDepth=1, Name='关闭')
                    if tnBtn.Exists(2):
                        utils.safeClick(ws, tnBtn, position='cc')
 
            if len(itSet) > 5:
                break

            ws.WheelDown(waitTime=0.5, wheelTimes=2)
            time.sleep(random.uniform(5, 10))

    except Exception as e:
        print(e)


