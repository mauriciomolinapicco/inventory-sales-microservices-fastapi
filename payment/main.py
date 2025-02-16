from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from redis_om import get_redis_connection, HashModel
from starlette.requests import Request
from dotenv import load_dotenv
import os
import requests
from fastapi.background import BackgroundTasks

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)

redis = get_redis_connection(
    host="redis-17898.crce181.sa-east-1-2.ec2.redns.redis-cloud.com",
    port=17898,
    password=os.getenv('REDIS_PASSWORD'),
    decode_responses=True
)

class Order(HashModel):
    product_id: str
    price: float
    fee: float
    total: float
    quantity: int 
    status: str #pending or completed or refunded

    class Meta:
        database = redis


@app.get('/orders/{pk}')
def get(pk: str):
    return Order.get(pk)


@app.post('/orders')
async def create(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()

    try:
        req = requests.get('http://127.0.0.1:8000/products/%s' % body['id'])
        req.raise_for_status()  # Lanza una excepción si la solicitud no fue exitosa (por ej., código de estado 4xx o 5xx)
    except requests.exceptions.RequestException as e:
        # Captura cualquier excepción durante la solicitud o decodificación JSON
        return {"error": str(e)}  # Puedes devolver un mensaje de error genérico o personalizado
    
    product = req.json()  # Intenta decodificar la respuesta como JSON
    order = Order(
        product_id=body['id'],
        price=product['price'],
        fee=0.2 * product['price'],
        total=1.2 * product['price'] ,
        quantity=body['quantity'],
        status='pending'
    )
    order.save()

    # esto es para que la tarea de marcar como completado sea asincrona y no haga falta esperar a que se ejecute
    background_tasks.add_task(order_completed, order)
    return order
    

def order_completed(order: Order):
    order.status = 'completed'
    order.save()