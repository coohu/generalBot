from .. import *

def post(parent, it):
    try:
        poster = it.Name.split(':\n')
        wxid = None
        eis = []
        for btn in utils.FindAll(it):
            if btn.Name == "图片" and False:
                utils.safeClick(parent, btn, position='tc', offset_x=5, offset_y=13,delay=(2,4))
                eis.append(utils.imageView())
            if btn.Name == poster[0] and not wxid:
                utils.safeClick(parent, btn, position='tc', offset_x=5, offset_y=13,delay=(1,2))
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
                    utils.profile(parent)
                utils.safeClick(parent, parent, position='tc')
        
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

        utils.safeClick(parent, cmt, position='tl', offset_x=2, offset_y=2)
        toast = parent.PaneControl(searchDepth=1, ClassName='SnsLikeToastWnd')
        like = toast.ButtonControl(searchDepth=3, Name='赞')
        if not like.Exists():
            return
        # like.Click()
        # time.sleep(random.uniform(2.5, 4.5))
        utils.safeClick(parent, like, position='tl', offset_x=5, offset_y=5)
        utils.safeClick(parent, cmt, position='tl', offset_x=2, offset_y=2)

        toast = parent.PaneControl(searchDepth=1, ClassName='SnsLikeToastWnd')
        toast.ButtonControl(searchDepth=3, Name='评论').Click()
        time.sleep(random.uniform(2.5, 4.5))
        parent.EditControl(Name="评论").SendKeys('元宵节快乐！{Enter}')
        exit()

    except Exception as e:
        print(e)


def posts():
    ps = auto.WindowControl(searchDepth=1, Name='朋友圈', ClassName='SnsWnd')
    if not ps.Exists():
        print("未找到窗口")
        return
    ps.SetFocus()
    psList = ps.ListControl(searchDepth=4, Name='朋友圈')
    utils.scroll(ps, psList, post, "wheel", 6)
