import uiautomation as auto
import argparse
from wechat import *

def main(opt):
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
    init.userInfo(wc)

    if opt == 'contact':
        nv.ButtonControl(searchDepth=1, Name="通讯录").Click()
        time.sleep(random.uniform(0.5, 1.5))
        contact.contacts(wc)

    elif opt == 'post':
        nv.ButtonControl(searchDepth=1,Name="朋友圈").Click()
        time.sleep(random.uniform(0.5, 1.5))
        post.posts()

    elif opt == 'search':
        nv.ButtonControl(searchDepth=3,Name="搜一搜").Click()
        time.sleep(random.uniform(0.5, 1.5))
        search.search()

    elif opt == 'chat':
        nv.ButtonControl(searchDepth=1,Name="聊天").Click()
        time.sleep(random.uniform(0.5, 1.5))
        ctList = wc.ListControl(Name='会话')
        if not ctList.Exists():
            print("未找到会话: ListControl")
            return
        chat.msgScroll(wc, ctList, func=chat.chat)
    else:
        print(f"请选择要执行的操作：['contact', 'post', 'search', 'chat']")

parser = argparse.ArgumentParser()
parser.add_argument("option", type=str, help="给出要执行的操作")
args = parser.parse_args()
if args.option not in ['contact', 'post', 'search', 'chat']:
    print(f"请选择要执行的操作：['contact', 'post', 'search', 'chat']")
    exit()
main(args.option)