import requests
from bs4 import BeautifulSoup

from flask import Flask, render_template,request, make_response, jsonify
from datetime import datetime

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

if os.path.exists('serviceAccountKey.json'):
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)

app = Flask(__name__)

@app.route("/")
def index():
    link = "<h1>歡迎進入呂芳妤的網站</h1>"
    link += "<a href=/mis>課程</a><hr>"
    link += "<a href=/today>現在日期時間</a><hr>"
    link += "<a href=/me>關於我</a><hr>"
    link += "<a href=/welcome?u=芳妤&d=靜宜資管&c=資訊管理導論>Get傳值</a><hr>"
    link += "<a href=/account>POST傳值</a><hr>"
    link += "<a href=/calculate>次方與根號計算</a><hr>"
    link += "<br><a href=/read>讀取Firestore資料</a><br>"
    link += "<br><a href=/read_c>讀取Firestore資料(根據資料關鍵字:楊)</a><br>"
    link += "<br><a href=/search>老師姓名查詢</a><br>"
    link += "<br><a href=/spider>爬取子青老師本學期課程</a><br>"
    link += "<br><a href=/movie1>爬取即將上映電影</a><br>"
    link += "<br><a href=/spiderMovie>爬取將上映電影</a><br>"
    link += "<br><a href=/searchQ>查詢即將上映電影</a><br>"
    link += "<br><a href=/road>十大肇事路口</a><br>"
    link += "<br><a href=/weather>查詢目前天氣</a><br>"
    link += "<br><a href=/rate>本週新片進DB</a><br>"
    return link


@app.route("/webhook", methods=["POST"])
def webhook():
    # build a request object
    req = request.get_json(force=True)
    # fetch queryResult from json
    action =  req["queryResult"]["action"]
    #msg =  req["queryResult"]["queryText"]
    #info = "我是呂芳妤設計的機器人，動作：" + action + "； 查詢內容：" + msg

    if (action == "rateChoice"):
        rate =  req["queryResult"]["parameters"]["rate"]
        info = "我是呂芳妤設計的機器人，您選擇的電影分級是：" + rate +"，相關電影：\n"


    return make_response(jsonify({"fulfillmentText": info}))


@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate


@app.route("/weather", methods=["GET", "POST"])
def weather_query():
    result_text = ""
    if request.method == "POST":
        city = request.form.get("city", "")
        if city:
            city = city.replace("台", "臺")
            url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=rdec-key-123-45678-011121314&format=JSON&locationName={city}"
            
            try:
                response = requests.get(url)
                data = json.loads(response.text)
                
                if data["records"]["location"]:
                    weather_element = data["records"]["location"][0]["weatherElement"]
                    weather = weather_element[0]["time"][0]["parameter"]["parameterName"]
                    rain = weather_element[1]["time"][0]["parameter"]["parameterName"]
                    result_text = f"{city} 目前天氣預報：<br>{weather}，降雨機率：{rain}%"
                else:
                    result_text = "找不到該縣市，請輸入正確名稱（如：臺中市）。"
            except Exception as e:
                result_text = f"連線錯誤：{e}"
                
    return render_template("weather.html", result=result_text)



@app.route("/road")
def road():
    R = "台中市十大肇事路口(113年10月)作者:呂芳妤</h1><br>"
    url = "https://datacenter.taichung.gov.tw/swagger/OpenData/a1b899c0-511f-4e3d-b22b-814982a97e41"
    headers = {"User-Agent": "Mozilla/5.0"}

    Data = requests.get(url, headers=headers)
    #print(Data.text)

    JsonData = json.loads(Data.text)
    for item in JsonData:
        R += (item["路口名稱"] + ",原因:" + item["主要肇因"] + ",件數:" + item["總件數"]) + "<br>"
       
    return R


@app.route("/spiderMovie")
def spiderMovie():
    R = ""
    
    db = firestore.client()
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"

    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text.replace("更新時間：", "")


    result=sp.select(".filmListAllX li")
    info = ""
    total = 0
    for item in result:
      total += 1
      movie_id = item.find("a").get("href").replace("/movie/", "").replace("/", "")
      title = item.find(class_="filmtitle").text
      picture = "https://www.atmovies.com.tw/" + item.find("img").get("src")
      hyperlink = "https://www.atmovies.com.tw/" + item.find("a").get("href")
      showDate = item.find(class_="runtime").text[5:15]
      info += movie_id + "\n" + title + "\n"
      info += picture + "\n" + hyperlink + "\n" + showDate + "\n\n"


      doc = {
          "title": title,
          "picture": picture,
          "hyperlink": hyperlink,
          "showDate": showDate,
          "lastUpdate": lastUpdate
      }
      
      doc_ref = db.collection("電影2B").document(movie_id)
      doc_ref.set(doc)

    R += "網站最近更新日期:" + lastUpdate + "<br>"
    R += "總共爬取" + str(total) + "部電影到資料庫"


    return R

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>返回首頁"

@app.route("/today")
def today():
    now = datetime.now()
    return render_template("today.html", datetime = str(now))

@app.route("/me")
def me():
    return render_template("about.html")

@app.route("/welcome", methods=["GET"])
def welcome():
    user = request.values.get("u")
    d = request.values.get("d")
    c = request.values.get("c")
    return render_template("welcome.html", name=user, dep = d, course = c)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/calculate")
def calculate():
    return render_template("calculate.html")

@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")    
    docs = collection_ref.get()
    docs = collection_ref.order_by("lab", direction=firestore.Query.DESCENDING).get()
    for doc in docs:         
        Result += str(doc.to_dict()) + "<br>"    
    return Result

@app.route("/read_c")
def read_c():
    Result = ""
    keyword = "楊"
    db = firestore.client()
    collection_ref = db.collection("靜宜資管")
    docs = collection_ref.get()
    for doc in docs:
        teacher = doc.to_dict()
        if keyword in teacher["name"]:         
            Result += str(teacher) + "<br>"

    if Result == "":
        Result = "抱歉，查無此關鍵字姓名之老師資料"
    return Result

@app.route("/search", methods=["GET", "POST"])
def search():
    db = firestore.client()
    results = []
    keyword = ""
    if request.method == "POST":
        keyword = request.form.get("keyword")
        collection_ref = db.collection("靜宜資管")
        docs = collection_ref.get()
        for doc in docs:
            user = doc.to_dict()
            if keyword in user["name"]:
                results.append({
                    "name": user["name"],
                    "lab": user["lab"]
                })
    return render_template("search.html", results=results, keyword=keyword)

@app.route("/spider")
def spider():
    R = ""
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".team-box a")
    for i in result:
        R += i.text + i.get("href") + "<br>" 
    return R

@app.route("/movie1")
def movie1():
    R = ""
    url = "https://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    #print(Data.text)
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".filmListAllX li")
    for item in result:
        introduce = "https://www.atmovies.com.tw/" + item.find("a").get("href")
        R += "<a href=" + introduce + ">" + item.find("img").get("alt") + "</a><br>"
        post = "https://www.atmovies.com.tw/" + item.find("img").get("src")
        R += "<img src=" + post + "> </img><br><br>"
    return R

@app.route("/searchQ", methods=["POST","GET"])
def searchQ():
    db = firestore.client()
    results = []
    keyword = ""
    
    if request.method == "POST":
        keyword = request.form.get("keyword")
        collection_ref = db.collection("電影")
        docs = collection_ref.get()

        for doc in docs:
            movie = doc.to_dict()
            if keyword in movie["title"]:
                results.append({
                    "title":  movie["title"],
                    "picture": movie["picture"],
                    "hyperlink": movie["hyperlink"],
                    "showDate": movie["showDate"],
                    "lastUpdate": movie["lastUpdate"]
                })

    return render_template("input.html", results=results, keyword=keyword)


if __name__ == "__main__":
    app.run(debug=True)
    
