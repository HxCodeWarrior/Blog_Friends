# generator/requests.py
# author:  ByteWyrm
# date: 2025.5.25 1:20
import requests
from config.settings import load

requests.packages.urllib3.disable_warnings()


def get_data(link):
    cfg = load()
    result = ''
    user_agent = 'Mozilla/5.0 (Macintosh;Intel Mac OS X 10_12_6) ' \
                'AppleWebKit/537.36(KHTML, like Gecko) ' \
                'Chrome/67.0.3396.99Safari/537.36'
    header = {'User_Agent': user_agent}
    try:
        r = requests.get(link,
                        headers=header,
                        timeout=cfg['request']['timeout'],
                        verify=cfg['request']['ssl'])
        r.encoding = 'utf-8'
        result = r.text.encode("gbk", 'ignore').decode('gbk', 'ignore')
        if str(r) == '<Response [404]>':
            result = 'error'
    except Exception as e:
        print(e)
        print(e.__traceback__.tb_frame.f_globals["__file__"])
        print(e.__traceback__.tb_lineno)
    return result

def get_json(link, params=None):
    cfg = load()
    header = {
        'Accept': 'application/vnd.github.v3+json'
    }
    try:
        r = requests.get(link,
                        headers=header,
                        params=params,
                        timeout=cfg['request']['timeout'],
                        verify=cfg['request']['ssl'])
        return r.json()
    except Exception as e:
        print(e)
        return None