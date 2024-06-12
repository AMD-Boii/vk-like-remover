from __future__ import annotations
from typing import Optional

from twocaptcha import (
    TwoCaptcha, 

    ValidationException, NetworkException, 
    ApiException, TimeoutException
)

from time import sleep

class TwoCaptchaSolver:
    def  __init__(self, api_key: str) -> Optional[str]:
        config = {
            'apiKey': api_key,
            'server': 'rucaptcha.com',
        }
        self.solver = TwoCaptcha(config)
        # try:
        #     self.last_balance = self.solver.balance()
        # except Exception as e:
        #     print('Не удалось получить баланс', e)
        #     return e
    
    def solve_captcha(self, image_base64: str) -> Optional[tuple[str, str]]:
        try:
            print('Отправляем капчу на решение...')
            self.id = self.solver.send(image_base64, lang='ru')
            print('Распознаем капчу...')
            result = None
            for i in range(5):
                sleep(5)
                try:
                    result = self.solver.get_result(self.id)
                    break
                except NetworkException:
                    print(f'Решение еще не готово. Ждем еще {5-i} раз...')
                    continue
                except ApiException:
                    print('Сервису не удалось распознать капчу :с')

        except ValidationException as e:
            # invalid parameters passed
            print('Что-то с данными :/', e)
        except NetworkException as e:
            # network error occurred
            print('Что-то с сетью :c', e)
        except ApiException as e:
            # api respond with error
            print('Что-то с API :O', e)
        except TimeoutException as e:
            # captcha is not solved so far
            print('Что-то долго они...', e)
        finally:
            return result, f'Баланс: {self.solver.balance()}'

    def send_report(self, is_correct: bool) -> None:
        self.solver.report(self.id, is_correct)