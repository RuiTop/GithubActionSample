# 安装依赖 pip3 install requests html5lib bs4 schedule
import os
import requests
import json
import time
from random import randint
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 从环境变量获取配置信息
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")
openId = os.environ.get("OPEN_ID")
weather_template_id = os.environ.get("TEMPLATE_ID")

# 设置请求头，模拟浏览器行为
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.8,en;q=0.6",
    "Connection": "keep-alive"
}


# 创建带重试机制的requests会话
def create_session_with_retry():
    session = requests.Session()
    retry = Retry(
        total=3,  # 总重试次数
        backoff_factor=1,  # 重试间隔时间因子
        status_forcelist=[429, 500, 502, 503, 504]  # 需要重试的状态码
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(headers)
    return session


def get_weather(my_city):
    urls = [
        "http://www.weather.com.cn/textFC/hb.shtml",
        "http://www.weather.com.cn/textFC/db.shtml",
        "http://www.weather.com.cn/textFC/hd.shtml",
        "http://www.weather.com.cn/textFC/hz.shtml",
        "http://www.weather.com.cn/textFC/hn.shtml",
        "http://www.weather.com.cn/textFC/xb.shtml",
        "http://www.weather.com.cn/textFC/xn.shtml"
    ]

    session = create_session_with_retry()

    for url in urls:
        try:
            # 随机延迟，避免请求过于频繁
            time.sleep(randint(1, 3))

            resp = session.get(url, timeout=10)
            resp.raise_for_status()  # 检查HTTP错误状态码

            text = resp.content.decode("utf-8")
            soup = BeautifulSoup(text, 'html5lib')
            div_conMidtab = soup.find("div", class_="conMidtab")

            if not div_conMidtab:
                continue

            tables = div_conMidtab.find_all("table")
            for table in tables:
                trs = table.find_all("tr")[2:]
                for tr in trs:
                    tds = tr.find_all("td")
                    if len(tds) < 8:  # 确保有足够的td元素
                        continue

                    # 提取城市信息
                    city_td = tds[-8]
                    city_strings = list(city_td.stripped_strings)
                    if not city_strings:
                        continue

                    this_city = city_strings[0]
                    if this_city == my_city:
                        # 提取天气信息
                        high_temp_td = tds[-5]
                        low_temp_td = tds[-2]
                        weather_type_day_td = tds[-7]
                        weather_type_night_td = tds[-4]
                        wind_td_day = tds[-6]
                        wind_td_night = tds[-3]

                        high_temp = list(high_temp_td.stripped_strings)[0] if high_temp_td.stripped_strings else "-"
                        low_temp = list(low_temp_td.stripped_strings)[0] if low_temp_td.stripped_strings else "-"
                        weather_typ_day = list(weather_type_day_td.stripped_strings)[
                            0] if weather_type_day_td.stripped_strings else "-"
                        weather_type_night = list(weather_type_night_td.stripped_strings)[
                            0] if weather_type_night_td.stripped_strings else "-"

                        wind_day_parts = list(wind_td_day.stripped_strings)
                        wind_day = "".join(wind_day_parts[:2]) if len(wind_day_parts) >= 2 else "--"

                        wind_night_parts = list(wind_td_night.stripped_strings)
                        wind_night = "".join(wind_night_parts[:2]) if len(wind_night_parts) >= 2 else "--"

                        # 处理缺失数据
                        temp = f"{low_temp}——{high_temp}摄氏度" if high_temp != "-" else f"{low_temp}摄氏度"
                        weather_typ = weather_typ_day if weather_typ_day != "-" else weather_type_night
                        wind = wind_day if wind_day != "--" else wind_night

                        return (this_city, temp, weather_typ, wind)

        except requests.exceptions.RequestException as e:
            print(f"访问 {url} 时出错: {e}")
            continue

    # 如果未找到城市信息
    raise ValueError(f"未找到 {my_city} 的天气信息")


def get_access_token():
    if not appID or not appSecret:
        raise ValueError("APP_ID 和 APP_SECRET 必须设置")

    url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appID.strip()}&secret={appSecret.strip()}'

    try:
        session = create_session_with_retry()
        response = session.get(url, timeout=10)
        response.raise_for_status()
        result = response.json()

        if 'errcode' in result and result['errcode'] != 0:
            raise ValueError(f"获取access_token失败: {result}")

        access_token = result.get('access_token')
        if not access_token:
            raise ValueError("未在响应中找到access_token")

        return access_token

    except requests.exceptions.RequestException as e:
        print(f"获取access_token时网络错误: {e}")
        raise
    except Exception as e:
        print(f"获取access_token失败: {e}")
        raise


def get_daily_love():
    url = "https://api.vvhan.com/api/text/love?type=json"
    max_retries = 3
    retry_delay = 2

    session = create_session_with_retry()

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()

            if not response.text.strip():
                raise ValueError("API返回空响应")

            data = response.json()

            # 检查必要字段（成功时必须包含code和content）

            if data.get("success") :  # 若code为字符串类型则改为"1"
                return data["data"].get("content")  # 成功时仅返回content，无默认文本
            else:
                # 失败状态，msg为可选字段
                error_msg = data.get("msg", "未知错误")
                raise ValueError(f"API返回失败状态 (code: {data.get('code')}): {error_msg}")

        except Exception as e:
            print(f"请求情话失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

    return "今日情话获取失败，愿你拥有美好的一天！"


def send_weather(access_token, weather):
    if not access_token or not weather:
        raise ValueError("access_token 和 weather 不能为空")

    import datetime
    today = datetime.date.today()
    today_str = today.strftime("%Y年%m月%d日")

    body = {
        "touser": openId.strip() if openId else "",
        "template_id": weather_template_id.strip() if weather_template_id else "",
        "url": "https://weixin.qq.com",
        "data": {
            "date": {"value": today_str},
            "region": {"value": weather[0]},
            "weather": {"value": weather[2]},
            "temp": {"value": weather[1]},
            "wind_dir": {"value": weather[3]},
            "today_note": {"value": get_daily_love()}
        }
    }

    url = f'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}'

    try:
        session = create_session_with_retry()
        response = session.post(url, json=body, timeout=10)
        response.raise_for_status()
        print(f"发送结果: {response.text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"发送天气信息时出错: {e}")
        raise


def weather_report(this_city):
    try:
        # 1. 获取access_token
        access_token = get_access_token()
        if not access_token:
            print("无法获取access_token，程序终止")
            return

        # 2. 获取天气
        weather = get_weather(this_city)
        print(f"天气信息： {weather}")

        if not weather:
            print(f"无法获取 {this_city} 的天气信息")
            return

        # 3. 发送消息
        send_weather(access_token, weather)

    except Exception as e:
        print(f"程序执行出错: {e}")
        # 可以在这里添加错误通知逻辑


if __name__ == '__main__':
    weather_report("泰安")
