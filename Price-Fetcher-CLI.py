import requests as rq
import json
from persiantools.jdatetime import JalaliDate
import datetime
from rtl import rtl

gold = rq.get("https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=gold")
gold.encoding = "UTF-8"
coin = rq.get("https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=coin")
coin.encoding = "UTF-8"
currency = rq.get('https://api-web.tabdeal.org/r/festival/get-asset-prices/?asset_type=currency')
currency.encoding = "UTF-8"

gold_data = gold.json()
coin_data = coin.json()
currency = currency.json()

the_list= []
the_dict = {}
for i in gold_data:

    the_dict[i['price_title']] = int(i['last_price'][:-1])

for i in coin_data:
    the_dict[i['price_title']] = int(i['last_price'][:-1])

for i in currency:
    the_dict[i['price_title']] = int(i['last_price'][:-1])


the_dict.pop('یورو')
the_dict.pop('پوند')
the_dict.pop('طلای ۲۴ عیار')
print(rtl(json.dumps(the_dict,ensure_ascii=False, indent=2)))


def time():
    months_fa = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر",
    5: "مرداد", 6: "شهریور", 7: "مهر", 8: "آبان",
    9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند",
    }

    weekdays_fa = {
    0: "شنبه", 1: "یکشنبه", 2: "دوشنبه",
    3: "سه‌شنبه", 4: "چهارشنبه",
    5: "پنجشنبه", 6: "جمعه",
    }

    jd = JalaliDate.today()

    result = f"{weekdays_fa[jd.weekday()]}، {jd.day} {months_fa[jd.month]} {jd.year}"
    now = datetime.datetime.now().strftime("%H:%M")
    return rtl(result + '' + '\n' + now)
print(time())

