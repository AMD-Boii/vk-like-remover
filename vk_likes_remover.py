from __future__ import annotations
from typing import Optional

import json
import requests

from vk_api import VkApi, VkUserPermissions
from vk_api.exceptions import *
from base64 import b64encode
from time import sleep

from twocaptcha_manager import TwoCaptchaSolver


class VKLikesRemover:
    """
    Класс для управления лайками в VK.
    """

    def __init__(self,
                 vk_token: str,
                 twocaptcha_token: str, 
                 comments: bool, 
                 photos: bool, 
                 videos: bool, 
                 posts: bool,
                 goods: bool) -> Optional[str]:
        """
        Инициализация VKLikesManager.
        """

        self.vk_session = VkApi(token=vk_token, scope=VkUserPermissions.WALL)
        try:
            self.vk_session.auth(token_only=True)
        except AuthError or AccessDenied as e:
            return str(e)
        
        self.twocaptcha_token = twocaptcha_token

        self.comments = comments
        self.photos = photos
        self.videos = videos
        self.posts = posts
        self.goods = goods 

        try:
            with open('input.json', 'r') as f:
                filedata = f.read()
        except Exception as e:
            print(e)
            exit()

        if not filedata:
            exit('Файл пустой')

        if filedata[0] == "'":
            filedata = filedata[1:-1]
        try:
            self.data = list(set(json.loads(filedata)))
        except Exception as e:
            print(e)
            exit()

        self.len_data = len(self.data)
        print(f'Всего {self.len_data} шт')

    def check_captcha(self, response: dict) -> tuple:
        """
        Проверка на наличие капчи в ответе.

        :param response: Ответ от VK API.
        :return: URL изображения капчи и идентификатор капчи.
        """
        if 'error' in response:
            if response['error']['error_code'] == 14:
                captcha_sid = response['error']['captcha_sid']
                captcha_img = response['error']['captcha_img']
                return captcha_img, captcha_sid
        return None, None

    @staticmethod
    def get_base64_image(captcha_img: str) -> Optional[str]:
        """
        Получение изображения капчи в формате base64.

        :param captcha_img: URL изображения капчи.
        :return: Изображение капчи в формате base64.
        """
        response =  requests.get(captcha_img)
        if response.status_code == 200:
            return b64encode(response.content).decode('ascii')
        else:
            return     

    def request_vk(
        self,
        owner_id: str,
        post_id: str,
        type_remove: str,
        captcha_sid: str = '',
        captcha_key: str = '',
    ) -> dict:
        """
        Отправка запроса на удаление лайка в VK.

        :param owner_id: ID владельца.
        :param post_id: ID элемента.
        :param captcha_sid: Идентификатор капчи.
        :param captcha_key: Ключ капчи.
        :return: Ответ от VK API.
        """
        data = {
            'access_token': VK_TOKEN,
            'type': type_remove,
            'owner_id': owner_id,
            'item_id': post_id,
            'v': 5.199,
        }
        if captcha_key:
            data['captcha_key'] = captcha_key
        if captcha_sid:
            data['captcha_sid'] = captcha_sid

        response = requests.post('https://api.vk.com/method/likes.delete', data=data)
        return response.json()

    def remove(self, owner_id: str, post_id: str, type_remove: str) -> bool:
        """
        Удаление лайка с элемента.

        :param owner_id: ID владельца.
        :param post_id: ID элемента.
        :return: Успешность операции.
        """
        try:
            response = self.request_vk(owner_id, post_id, type_remove)
        except Exception as e:
            print(e)
            return False

        captcha_img, captcha_sid = self.check_captcha(response)
        if captcha_img and captcha_sid:
            print('Капча')
            c = TwoCaptchaSolver(self.get_base64_image(captcha_img))
            c.create_tasks()
            captcha_key = c.wait_for_captcha()
            response = self.request_vk(
                owner_id, post_id, type_remove, captcha_sid, captcha_key
            )

        return True

    def process_likes(self) -> None:
        """
        Обработка всех лайков из списка данных. Ограничение 3 запроса в секунду.
        Не рекомендую использовать паралелльные запросы.
        """
        item: str
        for index, item in enumerate(self.data):
            print(f'Обработка материала №{index+1} из {self.len_data} ')

            if '/wall' in item:
                if '?reply' in item and self.comments:
                    item = item.replace('https://vk.com/wall', '')
                    owner_id, item_id = item.split('_')
                    item_id = item_id.split('?reply=')[1].split('&thread=')[0]
                    type_remove = 'comment'
                elif self.posts:
                    owner_id, item_id = item.replace('/wall', '').split('_')
                    type_remove = 'post'
            elif '/photo' in item and self.photos:
                owner_id, item_id = item.replace('/photo', '').split('_')
                type_remove = 'photo'
            elif '/video' in item and self.videos:
                owner_id, item_id = item.replace('/video', '').split('_')
                type_remove = 'video'
            elif '/market' in item and self.goods:
                owner_id, item_id = item.split('product')[1].split('_')
                type_remove = 'market'
            else:
                continue

            self.remove(owner_id, item_id, type_remove)
            sleep(.3)
