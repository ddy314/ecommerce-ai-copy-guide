from backend.app import create_app

app = create_app()
client = app.test_client()

r = client.post('/api/auth/login', json={'username':'merchant','password':'merchant123','role':'merchant'})
print('login', r.status_code, r.json.get('message'))
token = r.json['token']

h = {'Authorization': f'Bearer {token}'}

r2 = client.get('/api/merchant/dashboard/revenue', headers=h)
print('dashboard', r2.status_code, list(r2.json.keys()) if r2.status_code==200 else r2.json)

r3 = client.get('/api/merchant/orders?page=1&page_size=5', headers=h)
print('orders', r3.status_code, list(r3.json.keys()) if r3.status_code==200 else r3.json)

r4 = client.get('/api/merchant/products?page=1&page_size=5', headers=h)
print('products', r4.status_code, list(r4.json.keys()) if r4.status_code==200 else r4.json)
