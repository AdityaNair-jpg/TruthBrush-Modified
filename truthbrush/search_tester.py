import requests
import json
# --- Configuration ---
SEARCH_QUERY = "ukraine"
# IMPORTANT: This token needs to be fresh.
AUTH_TOKEN = "-2RP-I3TKLBBdYDmYC3y0PcrJQJqxvPVvJ3gTXnHUCk" 

cookies = {
    '__gads': 'ID=a92e36e4eafee714:T=1753547796:RT=1753547796:S=ALNI_MZEgaR1XcpJFT9ZHvRa-vIlIkAoOw',
    '__eoi': 'ID=152eb5af7fe53c68:T=1753547796:RT=1755361170:S=AA-Afjb1cogJTHQbVBEwVQrow22l',
    '__cflb': '0H28vTPqhjwKvpvovPffsJ3cyNVudUuwykqKN2oiieb',
    'cf_clearance': 'FD924W1vZtqWN9s9ztk.oe0FD1NYbgE36gPBmsvL5nQ-1755415832-1.2.1.1-pTFtQctAUgQoZtBO7ecwDigNU9R_YuRyPy13W5LltKrdl2bQ8WA1xaOt06onr4HK9eXVBt3BJkRP8toyMBBVeFiOUDnKGdu46hQsfrMXVO21.1p2RUvqp9tz06Tp6NliXjTplZD4Hc3QNlSa5fY8UmLKgBGdktaI6t.fxcIoY4wL5QMQjsA8TwUOShszH_VSLCo.Rutg4GRbOIWBK4e03hA.QBHgzTdxAPG4rcqe824',
    '_cfuvid': 'IdEtuABWH4jjkuH_cUPWRNT2ErTjhDkGglesFMac35s-1755415833954-0.0.1.1-604800000',
    '__cf_bm': '1KoV60KLE1mgxtNUlR4r0FN20tngR2LSmM1ofoSS4pk-1755415834-1.0.1.1-oNSmtCO_mhnh4YanVz2iWwWnPFSZaPtsCm7eBlBmTUDRYsc1xMzJYSD61GanIeHWbfn5o0kB1xKZhHBUmRfd.DTUmgrrRLWwiZIkrGIwcMe9ToileI7Zw02SdoUTG.1y',
    '_mastodon_session': '%2FDLVniX8nQQCwd%2FmYrCHzYgwlbYY8eB19DMFL93%2FQvWegTBXzWlBEf1r6jDQ7UmzkW2zqp%2FIi1XX5VpoVJQxBC%2BlzDuphvmZ1nf%2BgkqFzy%2BuFKhG1XmEUn%2B6ZCyVMR8wVSUTG9u84cCMOP0RzBtU9mdqRAK3UM15x1k7GngE3j54nqNfjtfw38iVIWzXGoQPb1Er6S8ieVQwJozZTsp2Q7M6AE4i39rC9L0Pqx%2Fd4XLC%2FI1DwQqgrC4Yx%2FJm--1eqNoK4JSW13wES7--VXo%2Bh3YVY8cRmoKB9emLCg%3D%3D',
    '_tq_id.TV-5427368145-1.4081': 'e000a14548635d03.1753547554.0.1755416509..',
    'mp_15c0cd079bcfa80cd935f3a1b8606b48_mixpanel': '%7B%22distinct_id%22%3A%20%22trash_bin_01%22%2C%22%24device_id%22%3A%20%22198479413c6b28-07553f53fb7a8e-26011151-144000-198479413c7118c%22%2C%22%24search_engine%22%3A%20%22google%22%2C%22%24initial_referrer%22%3A%20%22https%3A%2F%2Fwww.google.com%2F%22%2C%22%24initial_referring_domain%22%3A%20%22www.google.com%22%2C%22%24user_id%22%3A%20%22trash_bin_01%22%7D',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'authorization': 'Bearer G3sJKcUWJVRZtXX603p6g-H8vB7_1NqQ4T28k-uW3EE',
    'baggage': 'sentry-environment=production,sentry-release=b16190b9477cd253d8476683f5c02fd3b61e9d53,sentry-public_key=341951a6e21a4c929c321aa2720401f5,sentry-trace_id=dc31347bb73e4aa997aca42c677c35a6',
    'priority': 'u=1, i',
    'referer': 'https://truthsocial.com/search?q=ukraine',
    'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"139.0.7258.128"',
    'sec-ch-ua-full-version-list': '"Not;A=Brand";v="99.0.0.0", "Google Chrome";v="139.0.7258.128", "Chromium";v="139.0.7258.128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"19.0.0"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'sentry-trace': 'dc31347bb73e4aa997aca42c677c35a6-8348810ed9523f9f',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    # 'cookie': '__gads=ID=a92e36e4eafee714:T=1753547796:RT=1753547796:S=ALNI_MZEgaR1XcpJFT9ZHvRa-vIlIkAoOw; __eoi=ID=152eb5af7fe53c68:T=1753547796:RT=1755361170:S=AA-Afjb1cogJTHQbVBEwVQrow22l; __cflb=0H28vTPqhjwKvpvovPffsJ3cyNVudUuwykqKN2oiieb; cf_clearance=FD924W1vZtqWN9s9ztk.oe0FD1NYbgE36gPBmsvL5nQ-1755415832-1.2.1.1-pTFtQctAUgQoZtBO7ecwDigNU9R_YuRyPy13W5LltKrdl2bQ8WA1xaOt06onr4HK9eXVBt3BJkRP8toyMBBVeFiOUDnKGdu46hQsfrMXVO21.1p2RUvqp9tz06Tp6NliXjTplZD4Hc3QNlSa5fY8UmLKgBGdktaI6t.fxcIoY4wL5QMQjsA8TwUOShszH_VSLCo.Rutg4GRbOIWBK4e03hA.QBHgzTdxAPG4rcqe824; _cfuvid=IdEtuABWH4jjkuH_cUPWRNT2ErTjhDkGglesFMac35s-1755415833954-0.0.1.1-604800000; __cf_bm=1KoV60KLE1mgxtNUlR4r0FN20tngR2LSmM1ofoSS4pk-1755415834-1.0.1.1-oNSmtCO_mhnh4YanVz2iWwWnPFSZaPtsCm7eBlBmTUDRYsc1xMzJYSD61GanIeHWbfn5o0kB1xKZhHBUmRfd.DTUmgrrRLWwiZIkrGIwcMe9ToileI7Zw02SdoUTG.1y; _mastodon_session=%2FDLVniX8nQQCwd%2FmYrCHzYgwlbYY8eB19DMFL93%2FQvWegTBXzWlBEf1r6jDQ7UmzkW2zqp%2FIi1XX5VpoVJQxBC%2BlzDuphvmZ1nf%2BgkqFzy%2BuFKhG1XmEUn%2B6ZCyVMR8wVSUTG9u84cCMOP0RzBtU9mdqRAK3UM15x1k7GngE3j54nqNfjtfw38iVIWzXGoQPb1Er6S8ieVQwJozZTsp2Q7M6AE4i39rC9L0Pqx%2Fd4XLC%2FI1DwQqgrC4Yx%2FJm--1eqNoK4JSW13wES7--VXo%2Bh3YVY8cRmoKB9emLCg%3D%3D; _tq_id.TV-5427368145-1.4081=e000a14548635d03.1753547554.0.1755416509..; mp_15c0cd079bcfa80cd935f3a1b8606b48_mixpanel=%7B%22distinct_id%22%3A%20%22trash_bin_01%22%2C%22%24device_id%22%3A%20%22198479413c6b28-07553f53fb7a8e-26011151-144000-198479413c7118c%22%2C%22%24search_engine%22%3A%20%22google%22%2C%22%24initial_referrer%22%3A%20%22https%3A%2F%2Fwww.google.com%2F%22%2C%22%24initial_referring_domain%22%3A%20%22www.google.com%22%2C%22%24user_id%22%3A%20%22trash_bin_01%22%7D',
}

params = {
    'q': 'ukraine',
    'limit': '20',
    'resolve': 'true',
    'type': 'statuses',
}

response = requests.get('https://truthsocial.com/api/v2/search', params=params, cookies=cookies, headers=headers)
if response.status_code == 200:
    print("✅ Success! The request worked.")
    # Pretty-print the JSON data
    print(json.dumps(response.json(), indent=2))
else:
    print(f"❌ Failed. The server responded with Status Code: {response.status_code}")
    # Print any error message the server sent back
    print("Error message:", response.text)