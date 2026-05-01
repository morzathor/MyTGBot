
# A Telegram Bot
Which it can be used as :  
1.Watching weather status in your city/region  
2.Password Manager  
3.Getting recent currency / gold prices (IR)  
4.Tracking your devices price as portfolio  


## Weather Watcher
It's using [OpenMeteo](https://api.open-meteo.com) API.
You should first provide and select your city, and then you can get the weather status hourly and daily.



## Password Manager
It has a built-in generator. It generates password based on your input character that follows the common security standard (Using symbols and numbers) and you can save the generated password as well.



## Currency / Gold price Watcher

Using [TabDeal](web.tabdeal.org) API, it shows you prices of Gold,Currency and other things as well.
You can even set a time interval to get prices and your own desired time interval.
Example output:



💵 ارزها:
💵 دلار 999,999 تومان
💵 یورو 999,999 تومان
💵 درهم 999,999 تومان
💵 پوند 999,999 تومان

🥇 طلا:
🥇 طلای آبشده 999,999 تومان
🥇 طلای ۱۸ عیار 999,999 تومان
🥇 طلای ۲۴ عیار 999,999 تومان

🪙 سکه:  
🪙 سکه امامی 999,999 تومان  
🪙 سکه بهار آزادی 999,999 تومان  
🪙 نیم سکه 999,999 تومان  
🪙 ربع سکه 999,999 تومان  
🪙 سکه گرمی 999,999 تومان





##  Usage
In order to run this bot you need to:  
1.Install [MongoDB](https://www.mongodb.com/docs/manual/administration/install-community/)    
2.Install Python 3.>    
3.Clone or download this repository  
```
Git clone https://github.com/morzathor/MyTGBot.git
```  
4.Install requirements using  
```
pip -r requirements.txt
```  
5.Create a bot in [BotFather](https://telegram.me/BotFather)     
6.Copy the token and place it in  
```
Main.py and Price_Fetcher.py
```  
7.Run the script  
```
Python3 main.py
```  

### Privacy Concerns
All your information and details are saved locally in your own MongoDB which is installed on your system and nobody else has access to it. 

## Platform Conversion
For converting this bot to work in compatible platforms like "Bale" messenger, you need to:  
1.Uncomment line **421** on ```main.py``` and **713** in ```Price_fetcher.py```  
2.Get your token bot from (@botfather) in Bale messenger  
3.Change the next line of each corresponding file from  
```
application = ApplicationBuilder().token('YOUR_TOKEN').build()
to    
application = ApplicationBuilder().base_url(base_url=Base_Url).token('YOUR_TOKEN').build()
```
