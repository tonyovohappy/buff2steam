import re

from requests.cookies import cookiejar_from_dict

from buff2steam import *


class Buff(BaseProvider):
    web_withdraw = 'https://buff.163.com/api/market/backpack/withdraw'
    web_backpack = 'https://buff.163.com/api/market/backpack'
    web_sell_order = 'https://buff.163.com/api/market/goods/sell_order'
    web_buy = 'https://buff.163.com/api/market/goods/buy'
    web_cancel = 'https://buff.163.com/api/market/bill_order/deliver/cancel'
    web_history = 'https://buff.163.com/api/market/buy_order/history'

    csrf_pattern = re.compile(r'name="csrf_token"\s*content="(.+?)"')

    def __init__(self, game='dota2', game_appid=570, opener=None):
        super().__init__(opener)
        self.game = game
        self.game_appid = game_appid

    def post(self, url, **kwargs):
        csrf_token = self.csrf_pattern.findall(
            self.opener.get('https://buff.163.com').text
        )

        if not csrf_token:
            raise RuntimeError

        self.opener.headers['X-CSRFToken'] = csrf_token[0]
        self.opener.headers['Referer'] = 'https://buff.163.com'

        return self.opener.post(url, **kwargs)

    def withdraw(self, backpack_ids: typing.List[str] = None) -> bool:
        if not backpack_ids:
            backpack_ids = []

            res = self.opener.get(self.web_backpack, params={
                'game': self.game
            }).json()

            if res['data']['backpack_count'] == 0:
                return False

            for each_item in res['data']['items']:
                backpack_ids.append(each_item['id'])

        self.post(self.web_withdraw, json={
            'game': self.game,
            'backpack_ids': backpack_ids
        })

        return True

    def buy(self, max_price: float, goods_id: str, auto_buy_qty: int = 1, pay_method: int = 3) -> bool:
        res = self.opener.get(self.web_sell_order, params={
            'game': self.game,
            'goods_id': goods_id,
            'sort_by': 'price.asc',
            'max_price': max_price,
            'exclude_current_user': '1',
            'allow_tradable_cooldown': '0',
        }).json()

        if res['data']['total_count'] == 0:
            return False

        if 0 == auto_buy_qty:
            auto_buy_qty = res['data']['total_count']

        for each_item in res['data']['items'][:auto_buy_qty]:
            self.post(self.web_buy, json={
                'game': self.game,
                'goods_id': goods_id,
                'sell_order_id': each_item['id'],
                'price': max_price,
                'pay_method': pay_method,
                'allow_tradable_cooldown': 0
            })

        return True

    def cancel(self, timeout=0):
        res = self.opener.get(self.web_history, params={
            'page_num': 1,
            'page_size': 60,
            'game': self.game,
            'appid': self.game_appid,
            'state': 'trading',
        }).json()

        for each_item in res['data']['items']:
            # check cancel is available or not
            if each_item['buyer_cancel_timeout'] > 0:
                continue

            # check if timeout or not
            if each_item['buyer_cancel_timeout'] + timeout > 0:
                continue

            self.post(self.web_cancel, json={
                'game': self.game,
                'bill_order_id': each_item['id']
            })

if __name__ == '__main__':
    s = requests.session()
    s.cookies = cookiejar_from_dict({
        'session': ''
    })
    Buff(opener=s).cancel()
