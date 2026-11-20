import random
import datetime
from locust import FastHttpUser, task, constant
from faker import Faker

random.seed(42)

fake = Faker()
fake.seed_instance(42)

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z'
]

class MicroservicesUser(FastHttpUser):
    wait_time = constant(0)

    @task
    def user_session(self) -> None:
        """
        Sekwencyjna ścieżka sesji użytkownika (w stylu projektu Clue),
        dostosowana do Google Microservices Demo.
        """
        
        res = self.client.get("/")
        
        currencies = ['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY']
        self.client.post("/setCurrency", {'currency_code': random.choice(currencies)})

        for _ in range(random.randint(2, 4)):
            product = random.choice(products)
            self.client.get(f"/product/{product}")

        target_product = random.choice(products)
        self.client.get(f"/product/{target_product}")
        self.client.post("/cart", {
            'product_id': target_product,
            'quantity': random.randint(1, 3)
        })
        self.client.get("/cart")

        choice_buy = random.choice([True, False])
        if choice_buy:
            current_year = datetime.datetime.now().year + 1
            self.client.post("/cart/checkout", {
                'email': fake.email(),
                'street_address': fake.street_address(),
                'zip_code': fake.zipcode(),
                'city': fake.city(),
                'state': fake.state_abbr(),
                'country': fake.country(),
                'credit_card_number': fake.credit_card_number(card_type="visa"),
                'credit_card_expiration_month': random.randint(1, 12),
                'credit_card_expiration_year': random.randint(current_year, current_year + 70),
                'credit_card_cvv': f"{random.randint(100, 999)}",
            }, name="/cart/checkout")
        else:
            self.client.post('/cart/empty')

        self.client.get("/")