import requests
import json
import base64


GROCY_API_BASE_URL = f'{pyscript.app_config["url"]}/api'
GROCY_API_KEY = pyscript.app_config['api_key']
HEADERS = {
        'Content-Type': 'application/json',
        'GROCY-API-KEY': GROCY_API_KEY
        }

def fetch_data(endpoint):
    url = f'{GROCY_API_BASE_URL}/{endpoint}'
    log.info(f'fetching data from {url}')
    req = task.executor(
            requests.get,
            url,
            headers=HEADERS
            )
    if req.status_code != 200:
        log.error(f'Failure to retrieve {url} - Status code: {req.status_code}')
        return None

    return req.json()

def post_data(endpoint, req_body):
    url = f'{GROCY_API_BASE_URL}/{endpoint}'
    log.info(f'posting data to {url}')
    req = task.executor(
            requests.post,
            url,
            headers=HEADERS,
            data=json.dumps(req_body)
            )
    if req.status_code != 200:
        log.error(f'Failure to post {url} - Status code: {req.status_code}')
        log.error(req.text)
        return None

    return req.json()

def get_all_products_id():
    products = fetch_data('objects/products')
    if not products:
        return None
    
    return [product['id'] for product in products]

def get_product_info(product_id):
    product = fetch_data(f'stock/products/{product_id}')
    if not product:
        return None


    product_data = {
            'value': product['stock_amount'],
            'attributes': {
                'id': product['product']['id'],
                'icon': "mdi:basket",
                'group_id': product['product']['product_group_id'],
                'friendly_name': product['product']['name'],
                'min_stock_amount': product['product']['min_stock_amount'],
                'amount_opened': product['stock_amount_opened'],
                'location_id': product['location']['id'],
                'location_name': product['location']['name']
                }
            }
    
    picture_file = product['product']['picture_file_name']
    
    if picture_file:
        file_b64 = base64.b64encode(picture_file.encode()).decode()
        picture_url = f'{GROCY_API_BASE_URL}/files/productpictures/{file_b64}'
        product_data['attributes']['picture'] = picture_url

    return product_data

@service("grocy.update_product_sensor")
def grocy_update_product_sensor(product_id):
    product = get_product_info(product_id) 
    sensor_name = f'sensor.grocy_product_{product_id}'
    state.set(sensor_name, product['value'], product['attributes'])

@service("grocy.update_product")
def grocy_update_product(product_id, amount=1, operation="consume"):
    valid_operations = [
            "consume",
            "add",
            "open"
            ]
    if operation not in valid_operations:
        log.error(f'Operation {operation} is invalid')
        return None

    payload = {
            "amount": amount
            }
    post_data(f'stock/products/{product_id}/{operation}', payload)
    grocy_update_product_sensor(product_id)


@service("grocy.update_all_products")
@time_trigger("startup")
@time_trigger("period(now + 1m, 1m)")
def grocy_update_all_products():
    for p in get_all_products_id():
        grocy_update_product_sensor(p)

