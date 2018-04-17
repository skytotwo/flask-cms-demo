# -*- coding:utf-8 -*-
__author__ = 'jolly'
__date__ = '2018/4/14 下午2:34'

import os
import uuid
from flask import Flask, render_template, redirect, flash, session, Response, url_for, request
from werkzeug.security import generate_password_hash
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename

from forms import LoginForm, RegisterForm, ArticleAddForm, ArticleEditForm
from models import User, db, Article
from models import app

# app = Flask(__name__)
app.config['SECRET_KEY'] = "12345678"
# 设置上传封面图路径
app.config["uploads"] = os.path.join(os.path.dirname(__file__), "static/uploads")


# 登录装饰器
def user_login_req(f):
    @wraps(f)
    def login_req(*args,**kwargs):
        if "user" not in session:
            return redirect(url_for('login', next=request.url )) #request.url拼接在返回的url里，用作登陆后跳转至原来输入的地址
        return f(*args,**kwargs)
    return login_req


# 登录
@app.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit(): #如果验证成功
        data = form.data
        session["user"] = data["account"]
        flash("登录成功！", "ok")
        return redirect("/art/list/1/")
    return render_template("login.html", title="登录", form=form)  # 渲染模板


# 注册
@app.route("/register/", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit(): #如果验证成功
        data = form.data
        # 保存数据
        user = User(
            account=data["account"],
            # 对于pwd进行加密
            pwd=generate_password_hash(data["pwd"]),
            add_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.session.add(user)
        db.session.commit()
        # 定义一个会话的闪现
        flash("注册成功, 请登录!", "ok")
        return redirect("/login/")
    else:
        flash("输入正确信息注册！", "err")
    return render_template("register.html", title="注册", form=form)


# 退出(302跳转到登陆页面)
@app.route("/logout/", methods=["GET"])
@user_login_req
def logout():
    session.pop("user")
    return redirect("/login/")


# 修改文件名称
def change_name(name):
    info = os.path.splitext(name)
    # 文件名: 时间格式字符串+唯一字符串+后缀名
    name = datetime.now().strftime("%Y%m%d%H%M%S")+str(uuid.uuid4().hex)+info[-1]
    return name


# 发布文章
@app.route("/art/add/", methods=["GET", "POST"])
@user_login_req
def art_add():
    form = ArticleAddForm()
    if form.validate_on_submit():
        data = form.data

        # 上传logo
        file = secure_filename(form.logo.data.filename) #编译安全文件名称
        logo = change_name(file)
        if not os.path.exists(app.config["uploads"]):
            os.makedirs(app.config["uploads"])
        # 保存文件
        form.logo.data.save(app.config["uploads"] + "/" + logo)
        # 获取用户ID
        user = User.query.filter_by(account=session["user"]).first()
        user_id = user.id
        # 保存数据，Article
        article = Article(
            title=data["title"],
            category=data["category"],
            user_id=user_id,
            logo=logo,
            content=data["content"],
            add_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        db.session.add(article)
        db.session.commit()
        flash(u"发布文章成功", "ok")
    return render_template("art_add.html", title="发布文章", form=form)


# 编辑文章
@app.route("/art/edit/<int:id>", methods=["GET", "POST"])
@user_login_req
def art_edit(id):
    form = ArticleEditForm()
    article = Article.query.get_or_404(int(id))
    if request.method == "GET":
        form.content.data = article.content
        form.category.data = article.category
        # 莫名其妙赋初值:不赋初值表单提交时会提示封面为空
        # 放在这里修复显示请选择封面的错误
    form.logo.data = article.logo
    if form.validate_on_submit():
        data = form.data
        # 上传logo
        file = secure_filename(form.logo.data.filename)
        logo = change_name(file)
        if not os.path.exists(app.config["uploads"]):
            os.makedirs(app.config["uploads"])
        # 保存文件
        form.logo.data.save(app.config["uploads"] + "/" + logo)
        article.logo = logo
        article.title = data['title']
        article.content = data['content']
        article.category = data['category']
        db.session.add(article)
        db.session.commit()
        flash(u"编辑文章成功", "ok")
    return render_template("art_edit.html", form=form, title="编辑文章", article=article)
    #  其中注意的几个点。get请求时才赋初值，无论get post 都为logo赋初值。


# art_del 删除文章
@app.route("/art/del/<int:id>/", methods=["GET"])  # 删除文章
@user_login_req
def art_del(id):
    article = Article.query.get_or_404(int(id))
    db.session.delete(article)
    db.session.commit()
    flash("删除《%s》成功!" % article.title, "ok")
    return redirect("/art/list/1")


# 文章列表
@app.route("/art/list/<int:page>/", methods=["GET"])
@user_login_req
def art_list(page):
    if page is None:
        page = 1
        # 只展示当前用户才能看到的内容
    user = User.query.filter_by(account=session["user"]).first()
    user_id = user.id
    page_data = Article.query.filter_by(
        user_id=user_id
    ).order_by(
        Article.add_time.desc()
    ).paginate(page=page, per_page=1)
    #使用数据库中保存的category数字在categorylist中取到对应的索引位置的元组
    category = [(1, u"科技"), (2, u"搞笑"), (3, u"军事")]
    return render_template("art_list.html", title="文章列表", page_data=page_data, category=category)


# 验证码
@app.route("/captcha/", methods=["GET"])
def captcha():
    from captcha import Captcha
    c = Captcha()
    info = c.create_captcha()
    image = os.path.join(os.path.dirname(__file__), "static/captcha") + "/" + info["image_name"]
    with open(image, 'rb') as f:
        image = f.read()
    session['captcha'] = info["captcha"]
    # print(session['captcha'])
    return Response(image, mimetype="jpeg")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
