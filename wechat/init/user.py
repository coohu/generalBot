from .. import *

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
        print(e)